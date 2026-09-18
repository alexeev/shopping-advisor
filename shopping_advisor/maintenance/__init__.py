"""The repository's one automated maintenance gate.

    uv run --offline --locked python -m shopping_advisor maintenance check

Everything this repository already uses to decide that a change is safe --
the offline unittest suite, the published contract and schema versions, the
category registry, the committed study examples with their audited reports,
and the local documentation links -- runs from here, in one command, from a
clean checkout. It is local and version-controlled on purpose: there is no
hosted runner to configure, nothing to authenticate against, and no second
copy of the check list that can drift away from the code it protects.

The gate is deliberately *not* a Git hook. A hook is per-clone local state
that is invisible in review and trivially skipped with ``--no-verify``, which
is the opposite of what the maintenance workflow needs. Run this command; a
hook that calls it is a personal convenience, never the authority.

The second thing this module does is refuse to be quietly weakened.
``baseline.json`` is tracked, and it records what the gate is *entitled to
find*: which checks must run, which test modules must still exist and how
many tests they must still contain, which contract versions are published,
which categories are registered and what lifecycle state each has earned,
and which decisions each committed example must still reproduce. A
task-local change that deletes a test module, drops a check, bumps a contract
version, promotes a capability or moves an example's decision fails the gate
with the baseline field that would have to change. Changing it is
``maintenance baseline --update``: one tracked file, one reviewable diff, and
it refuses to run while the gate is failing, so a red baseline cannot be
recorded as the new normal.

Exit status follows the study CLI: 0 when there is nothing to report, 1 when
a check failed, and 2 when the gate could not be read or run at all.
"""

import contextlib
import dataclasses
import datetime as _dt
import io
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
BASELINE_PATH = Path(__file__).resolve().parent / 'baseline.json'

#: The baseline file's own shape. It changes when the gate starts recording
#: something new, which is a change to what "unweakened" means and therefore
#: not something an old baseline may be silently reinterpreted against.
#: Version 2 added ``capabilities``: the lifecycle state, decision and method
#: version of every registered capability (R16).
BASELINE_VERSION = 2


class GateError(Exception):
    """The gate could not be read or run -- distinct from a failed check."""


@dataclasses.dataclass(frozen=True)
class Finding:
    """One reason the gate did not pass, with the field that would move it."""

    code: str
    message: str

    def as_dict(self):
        return {'code': self.code, 'message': self.message}


@dataclasses.dataclass
class Result:
    """What one check found, and the one line it prints when it passed."""

    name: str
    summary: str = ''
    findings: tuple = ()
    observed: dict = dataclasses.field(default_factory=dict)

    @property
    def passed(self):
        return not self.findings


# ---------------------------------------------------------------- baseline


def load_baseline(path=BASELINE_PATH):
    """Read the tracked baseline, or say precisely why it cannot be read."""
    try:
        data = json.loads(Path(path).read_text(encoding='utf-8'))
    except OSError as exc:
        raise GateError(f'{path}: the gate baseline is missing. A clean '
                        f'checkout carries it; restore it from Git rather '
                        f'than regenerating it against an unknown tree.'
                        ) from exc
    except ValueError as exc:
        raise GateError(f'{path}: unreadable gate baseline ({exc}).') from exc
    if not isinstance(data, dict):
        raise GateError(f'{path}: the gate baseline must be a JSON object.')
    version = data.get('baseline_version')
    if version != BASELINE_VERSION:
        raise GateError(f'{path}: baseline_version {version!r}; this build '
                        f'reads version {BASELINE_VERSION}. The recorded '
                        f'floors may mean something else -- re-record them '
                        f'deliberately instead of running against them.')
    for field in ('checks', 'runtime', 'contracts', 'categories',
                  'capabilities', 'tests', 'examples', 'documentation'):
        if field not in data:
            raise GateError(f'{path}: the baseline has no {field!r} section. '
                            f'A section removed is a check removed.')
    return data


def _guard(baseline, checks):
    """Would this run establish less than the tracked baseline promises?

    Two directions matter and only one of them is obvious. A baseline that
    names a check nobody implements is a gate with a hole in it. A check that
    *is* implemented but no longer required is the quieter failure: the code
    still works, the command still passes, and the run simply stopped proving
    something. Both are findings, and both name the file to edit.
    """
    findings = []
    required = baseline['checks']
    if not isinstance(required, list) or not required:
        return [Finding('no_required_checks',
                        'baseline.checks is empty: this gate would establish '
                        'nothing. Restore the check list.')]
    for name in required:
        if name not in checks:
            findings.append(Finding(
                'unknown_check',
                f'baseline.checks requires {name!r}, which this build does '
                f'not implement. Either the check was deleted from the code '
                f'or the baseline names it wrongly.'))
    for name in checks:
        if name not in required:
            findings.append(Finding(
                'check_not_required',
                f'{name!r} is implemented but baseline.checks no longer '
                f'requires it. Dropping a check is a decision; record it in '
                f'baseline.json with the reason, or restore the entry.'))
    return findings


# ------------------------------------------------------------------ checks


def check_runtime(baseline, root=ROOT):
    """Is this the locked environment the rest of the baseline was taken in?

    A floor recorded under one interpreter and one Scrapy minor says nothing
    about another. The lock digest is here for the same reason: a dependency
    change is allowed, but not as a side effect of unrelated work.
    """
    from .. import provenance

    declared = baseline['runtime']
    identity = provenance.code_identity()
    findings = []
    for key in ('python', 'scrapy'):
        expected, actual = declared.get(key), identity.get(key)
        if actual is None:
            findings.append(Finding(
                f'{key}_unavailable',
                f'could not determine the {key} version in this environment'))
        elif not str(actual).startswith(str(expected)):
            findings.append(Finding(
                f'{key}_version',
                f'{key} {actual}; baseline.runtime.{key} declares '
                f'{expected}. Keep a runtime upgrade separate from product '
                f'work, and re-record the baseline with its own evidence.'))
    expected_lock = declared.get('lock_sha256')
    actual_lock = identity.get('lock_sha256')
    if actual_lock is None:
        findings.append(Finding(
            'lock_missing',
            'uv.lock is not present: this checkout cannot claim a locked '
            'environment.'))
    elif expected_lock and actual_lock != expected_lock:
        findings.append(Finding(
            'lock_changed',
            f'uv.lock digest {actual_lock[:12]}; baseline declares '
            f'{str(expected_lock)[:12]}. A dependency change needs its own '
            f'regression run and its own baseline update.'))
    summary = (f'python {identity.get("python")}, '
               f'scrapy {identity.get("scrapy")}, lock '
               f'{str(actual_lock)[:12] if actual_lock else "absent"}')
    return Result('runtime', summary, tuple(findings),
                  {'python': identity.get('python'),
                   'scrapy': identity.get('scrapy'),
                   'lock_sha256': actual_lock})


def _contract_versions():
    """The published versions, read from the modules that define them."""
    from ..extraction.pdp import SCHEMA_VERSION
    from ..provenance import RUN_MANIFEST_VERSION
    from ..study import audit
    from ..study.brief import BRIEF_VERSION
    from ..study.bundle import STUDY_MANIFEST_VERSION
    from ..study.intake import PLAN_VERSION
    from ..study.intake_review import INTAKE_REVIEW_VERSION
    from ..study.gates import STAGE_GATES_VERSION
    from ..study.delivery import DELIVERY_VERSION
    from ..study.delivery_review import DELIVERY_REVIEW_VERSION
    from ..study.session import SESSION_VERSION
    from ..study.adaptation import ADAPTATION_VERSION
    from ..validation.contract import CONTRACT_VERSION

    return {'extraction_schema': SCHEMA_VERSION,
            'validation_contract': CONTRACT_VERSION,
            'run_manifest': RUN_MANIFEST_VERSION,
            'brief': BRIEF_VERSION,
            'intake_plan': PLAN_VERSION,
            'intake_review': INTAKE_REVIEW_VERSION,
            'stage_gates': STAGE_GATES_VERSION,
            'delivery_record': DELIVERY_VERSION,
            'delivery_review': DELIVERY_REVIEW_VERSION,
            'session_ledger': SESSION_VERSION,
            'adaptation_record': ADAPTATION_VERSION,
            'study_manifest': STUDY_MANIFEST_VERSION,
            'evidence_ledger': audit.LEDGER_VERSION,
            'study_audit': audit.AUDIT_VERSION,
            'semantic_review': audit.REVIEW_VERSION}


def check_contracts(baseline, root=ROOT):
    """Do the published versions still say what the baseline recorded?

    CONTRACT.md's version rules are the review process; this is only the
    tripwire that keeps a bump from arriving as a diff nobody read.
    """
    declared = baseline['contracts']
    actual = _contract_versions()
    findings = []
    for name, expected in sorted(declared.items()):
        if name not in actual:
            findings.append(Finding(
                'contract_missing',
                f'baseline.contracts declares {name!r}, which this build no '
                f'longer publishes.'))
        elif actual[name] != expected:
            findings.append(Finding(
                'contract_version',
                f'{name} is at version {actual[name]}; the baseline records '
                f'{expected}. Apply CONTRACT.md version rules, state the '
                f'semantic change, then record it in baseline.contracts.'))
    for name in sorted(set(actual) - set(declared)):
        findings.append(Finding(
            'contract_untracked',
            f'{name} version {actual[name]} is published but absent from '
            f'baseline.contracts, so nothing would notice it moving.'))
    summary = ', '.join(f'{name} {value}' for name, value in sorted(
        actual.items()))
    return Result('contracts', summary, tuple(findings), actual)


def check_categories(baseline, root=ROOT):
    """Is every category the baseline recorded still registered?

    Additions are fine and unremarked: a new category is the point of the
    product. A disappearance is a capability the repository silently lost.
    """
    from ..analysis import categories

    declared = list(baseline['categories'])
    present = categories.known()
    missing = [key for key in declared if key not in present]
    findings = [Finding(
        'category_missing',
        f'{key!r} is in baseline.categories but no longer registered. A '
        f'retired category is an R16 decision with a recorded reason.')
        for key in missing]
    added = [key for key in present if key not in declared]
    summary = f'{len(present)} registered, {len(declared)} required'
    if added:
        summary += f' (new: {", ".join(added)})'
    return Result('categories', summary, tuple(findings),
                  {'registered': list(present)})


def check_capabilities(baseline, root=ROOT):
    """Has every capability declared what it earned, and is that still it?

    R16's promotion gate, made executable. Each registered category declares
    a lifecycle beside its code: state, last decision, applicability with
    case records behind it, evidence paths and roadmap anchors. This check
    reads only that declaration -- it is what the capability index publishes
    -- and asks three things of it. That it is complete and points at things
    that exist, so the index cannot describe evidence the tree does not
    hold. That every roadmap entry it cites is a heading, so a lifecycle
    decision is recorded before it is declared. And that its state, decision
    and method version are the ones the baseline pinned, so an experiment
    becoming a maintained capability is a reviewed diff with its evidence in
    ROADMAP rather than an adjective that changed in a commit.
    """
    from ..analysis import categories
    from ..analysis.category import Lifecycle
    from ..study import capabilities

    declared = baseline['capabilities']
    anchors = _anchors_of(Path(root) / 'ROADMAP.md')
    findings, observed = [], {}
    for key in categories.known():
        category = categories.get(key)
        for field, message in capabilities.problems(category, root):
            findings.append(Finding(
                'capability_invalid',
                f'{key}: lifecycle.{field}: {message}. The index and this '
                f'check read only the declaration beside the category.'))
        lifecycle = category.lifecycle
        if not isinstance(lifecycle, Lifecycle):
            continue
        for anchor in (*lifecycle.milestones, lifecycle.review):
            if anchor not in anchors:
                findings.append(Finding(
                    'capability_record_missing',
                    f'{key}: lifecycle cites ROADMAP.md#{anchor}, which is no '
                    f'heading there. A lifecycle decision is recorded in the '
                    f'roadmap before a declaration cites it.'))
        observed[key] = {'state': lifecycle.state,
                         'decision': lifecycle.decision,
                         'method_version': lifecycle.method_version}
        if key not in declared:
            findings.append(Finding(
                'capability_untracked',
                f'{key} is registered as {lifecycle.state!r} but absent from '
                f'baseline.capabilities. Retention is a decision: record the '
                f'declared state, decision and method version there, in a '
                f'reviewable diff.'))
            continue
        for field, actual in observed[key].items():
            expected = declared[key].get(field)
            if actual != expected:
                findings.append(Finding(
                    'capability_lifecycle_changed',
                    f'{key}: {field} is {actual!r}; the baseline records '
                    f'{expected!r}. Promotion, rejection and retirement are '
                    f'R16 decisions: record the decision and its evidence in '
                    f'ROADMAP, then re-record baseline.capabilities.'))
    counts = {}
    for row in observed.values():
        counts[row['state']] = counts.get(row['state'], 0) + 1
    summary = (f'{len(observed)} capabilities'
               + (' (' + ', '.join(f'{n} {state}' for state, n in sorted(
                   counts.items())) + ')' if counts else '')
               + f', {sum(key in declared for key in observed)} pinned')
    return Result('capabilities', summary, tuple(findings),
                  {'capabilities': observed})


def check_tests(baseline, root=ROOT):
    """Run the offline suite, and check that it is still the same suite.

    A green run proves nothing on its own: deleting a test file makes the
    command pass faster. The baseline records the module inventory and the
    test count so that removal has to be argued for rather than noticed
    later, if at all.
    """
    declared = baseline['tests']
    start = Path(root) / 'tests'
    loader = unittest.TestLoader()
    suite = loader.discover(start_dir=str(start), top_level_dir=str(start))
    if loader.errors:
        return Result('tests', 'discovery failed', tuple(
            Finding('test_discovery', str(error)) for error in loader.errors))

    modules, total = set(), 0
    for case in _flatten(suite):
        total += 1
        modules.add(type(case).__module__)

    findings = []
    for name in sorted(set(declared.get('modules', [])) - modules):
        findings.append(Finding(
            'test_module_missing',
            f'{name} is in baseline.tests.modules but was not discovered. '
            f'Removing regression coverage is a reviewable decision.'))
    minimum = declared.get('minimum', 0)
    if total < minimum:
        findings.append(Finding(
            'test_count',
            f'{total} tests discovered; baseline.tests.minimum records '
            f'{minimum}. {minimum - total} test(s) disappeared -- say which '
            f'and why, then lower the floor deliberately.'))

    # ``buffer`` keeps the suite's own diagnostics -- challenge notices,
    # extraction warnings -- out of the gate report unless a test fails, in
    # which case they are attached to it.
    stream = io.StringIO()
    outcome = unittest.TextTestRunner(stream=stream, verbosity=0,
                                      buffer=True).run(suite)
    for case, traceback in list(outcome.failures) + list(outcome.errors):
        findings.append(Finding('test_failed', f'{case}\n{traceback.strip()}'))

    summary = (f'{total} tests in {len(modules)} modules, '
               f'{len(outcome.failures)} failed, {len(outcome.errors)} '
               f'errored (floor {minimum})')
    return Result('tests', summary, tuple(findings),
                  {'minimum': total, 'modules': sorted(modules)})


def _flatten(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from _flatten(item)
        else:
            yield item


def check_examples(baseline, root=ROOT):
    """Replay every committed example through its documented commands.

    The unittest suite exercises the study library; this exercises the
    commands the documentation actually tells an agent to type, end to end,
    and compares the decisions with the ones the baseline recorded. A report
    whose shortlist, outcome or study identity moved is a semantic
    regression, whatever the library tests say.
    """
    import tempfile

    findings, observed, clean = [], [], 0
    with tempfile.TemporaryDirectory(prefix='sa-gate-') as scratch:
        for index, example in enumerate(baseline['examples']):
            directory = Path(scratch) / f'{index:02d}-{example["name"]}'
            reported, decisions = _replay_example(example, directory, root)
            findings.extend(reported)
            observed.append(decisions)
            clean += not reported
    summary = (f'{clean} of {len(baseline["examples"])} replayed with the '
               f'recorded decisions')
    return Result('examples', summary, tuple(findings),
                  {'examples': observed})


def _replay_example(example, directory, root):
    """One example: check the brief, run it, verify it, audit the report."""
    from ..study import __main__ as study_cli

    name = example['name']
    findings = []

    def invoke(*argv):
        buffer = io.StringIO()
        try:
            with contextlib.redirect_stdout(buffer), \
                    contextlib.redirect_stderr(buffer):
                status = study_cli.main([str(item) for item in argv])
        except Exception as exc:                      # noqa: BLE001
            findings.append(Finding(
                'example_command_raised',
                f'{name}: `study {" ".join(str(a) for a in argv)}` raised '
                f'{type(exc).__name__}: {exc}'))
            return None
        if status != 0:
            findings.append(Finding(
                'example_command_failed',
                f'{name}: `study {" ".join(str(a) for a in argv)}` exited '
                f'{status}\n{buffer.getvalue().strip()}'))
        return status

    brief = Path(root) / example['brief']
    plan_argv = ['--plan', Path(root) / example['plan']] if example.get('plan') else []
    if invoke('check', brief, *plan_argv) != 0:
        return findings, {'name': name}

    run_argv = ['run', brief, '-o', directory, *plan_argv]
    if example.get('intake_review'):
        run_argv += ['--intake-review', Path(root) / example['intake_review']]
    if example.get('session'):
        run_argv += ['--session', Path(root) / example['session']]
    if example.get('evidence'):
        run_argv += ['--evidence', Path(root) / example['evidence']]
    if example.get('adaptation'):
        # R15: a study resting on an adopted adaptation record; its method
        # descriptor is in the study id the baseline pins.
        run_argv += ['--adaptation', Path(root) / example['adaptation']]
    if invoke(*run_argv) != 0:
        return findings, {'name': name}
    invoke('verify', directory)
    if example.get('deliver_at'):
        # A fixed reference, so the gate fails with a change and never with
        # the passage of time. The record says the reference was declared.
        invoke('deliver', directory, '--reference', example['deliver_at'])
        invoke('verify', directory)
    resumable = ''
    if example.get('session'):
        # The complete resumption example: from the bundle's own snapshot, at
        # the same fixed reference, with the working ledger deliberately unused.
        status = invoke('resume', directory, '--reference',
                        example.get('deliver_at') or '2026-09-17T00:00:00+00:00')
        resumable = 'yes' if status == 0 else 'no'
    invoke('validate-report', directory)
    if example.get('review'):
        invoke('review', directory, Path(root) / example['review'])
        invoke('validate-report', directory, '--require-review')

    try:
        manifest = json.loads(
            (directory / 'manifest.json').read_text(encoding='utf-8'))
    except (OSError, ValueError) as exc:
        findings.append(Finding(
            'example_unreadable', f'{name}: no readable manifest ({exc})'))
        return findings, {'name': name}

    current_advice = ''
    if (directory / 'delivery.json').is_file():
        from ..study import delivery
        current_advice = delivery.latest(delivery.read(directory / 'delivery.json'))['current_advice']
    decisions = {'study_id': manifest.get('study_id'),
                 'outcome': manifest.get('outcome'),
                 'stop': manifest.get('stop', ''),
                 'current_advice': current_advice,
                 'resumable': resumable,
                 'intake_review': (manifest.get('intake_review') or {}).get('status', ''),
                 'shortlisted': manifest.get('counts', {}).get('shortlisted'),
                 'offers': manifest.get('counts', {}).get('offers'),
                 'excluded': manifest.get('counts', {}).get('excluded')}
    for field, expected in sorted(example.get('expect', {}).items()):
        if decisions.get(field) != expected:
            findings.append(Finding(
                'example_decision_changed',
                f'{name}: {field} is {decisions.get(field)!r}; the baseline '
                f'recorded {expected!r}. Explain what changed the decision '
                f'before re-recording it.'))
    return findings, {'name': name, 'expect': decisions}


_FENCE = re.compile(r'^\s*(```|~~~)')
_HEADING = re.compile(r'^(#{1,6})\s+(.*?)\s*#*\s*$')
_LINK = re.compile(r'(?<!\!)\[[^\]]*\]\(([^)\s]+)(?:\s+"[^"]*")?\)')


def _strip_fences(text):
    """Markdown outside fenced code. Commands are documentation, not links."""
    lines, inside = [], False
    for line in text.splitlines():
        if _FENCE.match(line):
            inside = not inside
            continue
        lines.append('' if inside else line)
    return lines


def slug(heading):
    """GitHub's anchor for a heading, near enough for local navigation."""
    text = re.sub(r'`([^`]*)`', r'\1', heading)
    text = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', text)
    text = text.replace('*', '').replace('_', '').lower()
    text = re.sub(r'[^\w\- ]', '', text, flags=re.UNICODE)
    return text.strip().replace(' ', '-')


def _anchors_of(path):
    """The heading anchors one Markdown document publishes."""
    lines = _strip_fences(Path(path).read_text(encoding='utf-8'))
    return {slug(match.group(2)) for match in
            (_HEADING.match(line) for line in lines) if match}


def check_docs(baseline, root=ROOT):
    """Do the documents still point at each other and at the code?

    The documentation is this repository's agent interface, so a dead link
    is a broken entry point rather than a cosmetic defect -- and the
    maintenance workflow already asks for links to be verified on a
    documentation-only change. This is that step, automated.
    """
    # Resolved, because a link is checked through its resolved destination
    # and a checkout reached through a symlink would otherwise compare two
    # different spellings of the same file.
    root = Path(root).resolve()
    declared = list(baseline['documentation'])
    documents = [path for path in
                 (root / name for name in declared) if path.is_file()]
    findings = [Finding(
        'document_missing',
        f'{name} is in baseline.documentation but absent from the tree.')
        for name in declared if not (root / name).is_file()]

    anchors = {path.resolve(): _anchors_of(path) for path in documents}

    links = 0
    for path in documents:
        for line in _strip_fences(path.read_text(encoding='utf-8')):
            for match in _LINK.finditer(line):
                target = match.group(1)
                if re.match(r'^[a-z][a-z0-9+.-]*:', target) or \
                        target.startswith('//'):
                    continue
                links += 1
                findings.extend(_check_link(path, target, root, anchors))
    summary = (f'{links} local links across {len(documents)} documents, '
               f'{sum(len(value) for value in anchors.values())} anchors')
    return Result('docs', summary, tuple(findings),
                  {'documentation': declared, 'links': links})


def _relative(path, root):
    try:
        return path.relative_to(root)
    except ValueError:
        return path


def _check_link(path, target, root, anchors):
    relative = _relative(path, root)
    location, _, fragment = target.partition('#')
    destination = path.resolve()
    if location:
        destination = (path.parent / location).resolve()
        if not destination.exists():
            return [Finding('dead_link',
                            f'{relative}: {target} does not exist')]
    if not fragment:
        return []
    if destination.suffix.lower() != '.md':
        return []
    known = anchors.get(destination)
    if known is None:
        known = anchors[destination] = _anchors_of(destination)
    if fragment not in known:
        return [Finding('dead_anchor',
                        f'{relative}: {target} names no heading in '
                        f'{_relative(destination, root)}')]
    return []


#: Order matters only for reading: cheap identity checks first, then the
#: suite, then the examples that take the longest to replay.
CHECKS = {'runtime': check_runtime, 'contracts': check_contracts,
          'categories': check_categories, 'capabilities': check_capabilities,
          'tests': check_tests, 'examples': check_examples, 'docs': check_docs}


# ------------------------------------------------------------------ runner


def run_gate(baseline, root=ROOT, checks=None, only=None):
    """Run the required checks and return ``(results, guard findings)``."""
    checks = CHECKS if checks is None else checks
    guard = _guard(baseline, checks)
    results = []
    for name in baseline['checks']:
        if name not in checks or (only and name not in only):
            continue
        try:
            results.append(checks[name](baseline, root))
        except Exception as exc:                      # noqa: BLE001
            results.append(Result(name, 'could not run', (Finding(
                'check_raised',
                f'{name} raised {type(exc).__name__}: {exc}'),)))
    return results, guard


def measure(baseline, root=ROOT):
    """A baseline describing the tree as it is now, for ``--update``.

    The curated parts -- which checks are required, which examples exist,
    which documents are indexed -- are carried over, not rediscovered: what
    the repository decided to verify is a decision, and only the measured
    floors underneath it are re-read from the tree.
    """
    results, _guard_findings = run_gate(baseline, root)
    observed = {result.name: result.observed for result in results}
    updated = dict(baseline)
    updated['baseline_version'] = BASELINE_VERSION
    updated['recorded_at'] = _dt.datetime.now(
        _dt.timezone.utc).replace(microsecond=0).isoformat()
    updated['checks'] = sorted(CHECKS)
    if 'runtime' in observed:
        runtime = dict(baseline['runtime'])
        python, scrapy = observed['runtime'].get('python'), \
            observed['runtime'].get('scrapy')
        runtime['python'] = '.'.join(str(python).split('.')[:2])
        runtime['scrapy'] = '.'.join(str(scrapy).split('.')[:2])
        runtime['lock_sha256'] = observed['runtime'].get('lock_sha256')
        updated['runtime'] = runtime
    if observed.get('contracts'):
        updated['contracts'] = observed['contracts']
    if observed.get('categories'):
        updated['categories'] = observed['categories']['registered']
    if observed.get('capabilities'):
        updated['capabilities'] = observed['capabilities']['capabilities']
    if observed.get('tests'):
        updated['tests'] = {'minimum': observed['tests']['minimum'],
                            'modules': observed['tests']['modules']}
    if observed.get('examples'):
        recorded = {item['name']: item.get('expect')
                    for item in observed['examples']['examples']}
        updated['examples'] = [
            dict(example, expect=recorded[example['name']])
            if recorded.get(example['name']) else example
            for example in baseline['examples']]
    return updated, results
