"""The study on disk: what is written, what it is named, and how it is checked.

A study bundle is the portable half of T2. It holds the brief, the inputs it
was computed from with their digests, every candidate and the reason for its
fate, the evidence cards behind the ones that matter, the decisions, and the
report -- enough that another checkout on another machine can re-derive the
same answer from the same bytes, and enough that a reader can tell when it
cannot::

    data/studies/<study_id>/
        manifest.json     brief digest, input digests, code identity,
                          outcome, artifact digests, declared variation
        brief.json        the brief as validated, with its defaults filled in
        candidates.jsonl  one line per record considered, with its decision
        cards.jsonl       the complete evidence card of every classified
                          candidate, as JSON
        ranking.json      the structured ranking, exclusions and claims
        report.md         the written report

**The identity is derived, not random.** A crawl's id has to carry random
bytes because two identical crawls are two different observations of a
changing shelf (T1). A study is the opposite: it is a pure function of a
brief and some pinned bytes, so its id is a digest of exactly that -- the
brief, the input digests, and the published schema/contract versions. The
same study computed in two places lands in the same directory name, and an
input that changed produces a different one. What the id deliberately does
*not* cover is the analysis code: a category rule can change a decision
without changing the id, and :func:`verify` is what catches that.

**Everything except the manifest is byte-identical between two runs.** The
report carries no timestamp and no hostname. The manifest is where the
variation lives, and it declares its own: ``volatile`` lists the fields that
may differ between two runs of the same brief over the same inputs -- when it
ran, and which interpreter and revision produced it. A reader comparing two
bundles compares everything else.
"""

import json
import pathlib
import shutil

from ..provenance import (code_identity, sha256_file, sha256_text,
                          write_json_atomically)
from ..analysis import report as report_module
from ..analysis.category import is_match
from ..run import read_jsonl
from . import writeup, audit, intake, intake_review, gates, delivery, session
from .analysis import StudyError, analyse, brief_fault
from .brief import BRIEF_VERSION, BriefError, load

#: The bundle shape this build writes and reads.
STUDY_MANIFEST_VERSION = 2

DEFAULT_STUDY_ROOT = 'data/studies'

MANIFEST = 'manifest.json'
BRIEF = 'brief.json'
CANDIDATES = 'candidates.jsonl'
CARDS = 'cards.jsonl'
RANKING = 'ranking.json'
REPORT = 'report.md'

LEDGER = 'ledger.json'
CLAIM_INDEX = 'claim-index.json'
VALIDATION = 'validation.json'
REVIEW = 'semantic-review.json'
ARTIFACTS = (BRIEF, CANDIDATES, CARDS, RANKING, REPORT, LEDGER, CLAIM_INDEX, VALIDATION, REVIEW)

#: What two runs of the same brief over the same inputs may legitimately
#: disagree about. Everything not on this list is a finding.
VOLATILE = ('started_at', 'finished_at', 'code', 'directory',
            'brief_source')


class BundleError(ValueError):
    """The bundle cannot be written, read or checked as it stands."""


def input_digests(brief):
    """Each declared feed with the digest of the bytes actually read."""
    digests = []
    for declared, resolved in zip(brief.inputs, brief.resolved_inputs):
        path = pathlib.Path(resolved)
        digests.append({'declared': declared,
                        'sha256': sha256_file(path),
                        'bytes': path.stat().st_size,
                        'records': sum(1 for _ in read_jsonl(path))})
    return digests


def study_id(brief, inputs, ledger=None):
    """``<brief id>-<digest>`` over everything the answer is pinned to."""
    code = code_identity()
    material = {
        'ledger': ledger or audit.empty(),
        'manifest_version': STUDY_MANIFEST_VERSION,
        'brief_version': brief.brief_version,
        'brief_sha256': brief.source_sha256,
        'inputs': sorted(item['sha256'] for item in inputs),
        'schema_version': code['extraction_schema_version'],
        'contract_version': code['validated_contract_version'],
    }
    digest = sha256_text(json.dumps(material, sort_keys=True))
    return f'{brief.id}-{digest[:12]}'


def _write_lines(path, rows):
    path.write_text(''.join(json.dumps(row, ensure_ascii=False,
                                       sort_keys=True) + '\n' for row in rows),
                    encoding='utf-8')


def write(brief, result, cards, directory):
    """Write one bundle into ``directory``, which must not already exist."""
    directory = pathlib.Path(directory)
    directory.mkdir(parents=True, exist_ok=False)

    write_json_atomically(directory / BRIEF, result['brief'])
    _write_lines(directory / CANDIDATES, result['candidates'])
    _write_lines(directory / CARDS,
                 [report_module.card_json(card)
                  for card in sorted((card for card in cards if is_match(card)),
                                     key=lambda card: card['asin'])])
    ranking = {'ranking': result['ranking'],
               'constraints': result['constraints'],
               'classification': result['classification'],
               'freshness': result['freshness'],
               'outcome': result['outcome'],
               'claims': result['claims'],
               'shortlist': result['shortlist']}
    if result.get('gates') is not None:
        # Plan-backed only, so a legacy bundle's bytes do not move.
        ranking['stop'] = result['stop']
        ranking['gates'] = result['gates']
    write_json_atomically(directory / RANKING, ranking)
    return directory


def artifact_digests(directory):
    directory = pathlib.Path(directory)
    return {name: {'sha256': sha256_file(directory / name),
                   'bytes': (directory / name).stat().st_size}
            for name in (*ARTIFACTS, intake.SNAPSHOT, intake_review.SNAPSHOT,
                         delivery.RECORD, session.SNAPSHOT)
            if (directory / name).is_file()}


def manifest(brief, result, identity, inputs, started_at, finished_at,
             directory):
    written = {
        'manifest_version': STUDY_MANIFEST_VERSION,
        'study_id': identity,
        'brief_id': brief.id,
        'brief_version': brief.brief_version,
        'brief_source': {'path': brief.source_path,
                         'format': brief.source_format,
                         'sha256': brief.source_sha256},
        'category': result['category'],
        'marketplace': result['marketplace'],
        'outcome': result['outcome']['code'],
        # Declared, or the historical default. Current advice is a condition
        # checked at each delivery event against delivery.json, never here.
        'scope': brief.scope or delivery.HISTORICAL,
        'scope_source': 'brief' if brief.scope else 'undeclared',
        'started_at': started_at,
        'finished_at': finished_at,
        'directory': str(directory),
        'code': code_identity(),
        'inputs': inputs,
        'merge': result['merge'],
        'classification': result['classification'],
        'counts': dict(result['ranking']['counts'],
                       shortlisted=len(result['shortlist'])),
        'artifacts': artifact_digests(directory),
        # Declared rather than discovered: a reader comparing two bundles has
        # to know which differences are expected before the first one shows
        # up. Everything not named here is a finding.
        'volatile': list(VOLATILE),
    }
    if result.get('gates') is not None:
        # The analytical outcome above is a fact about the evidence; the stop
        # is a fact about the request. A manifest reading `recommendation`
        # with no stop beside it would be the label INTAKE §1 warns about.
        written['stop'] = result['stop']
        written['permits'] = result['gates']['conclusion']['permits']
    return written


def load_manifest(directory):
    path = pathlib.Path(directory) / MANIFEST
    if not path.is_file():
        raise BundleError(f'{directory}: no {MANIFEST}. Either this is not a '
                          f'study bundle, or the study never finished writing '
                          f'one.')
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(data, dict):
            raise ValueError('manifest must be an object')
        return data
    except ValueError as exc:
        raise BundleError(f'{path}: unreadable manifest ({exc})') from exc


def run(brief_path, directory=None, root=DEFAULT_STUDY_ROOT, force=False,
        started_at='', finished_at='', evidence=None, plan=None, session_ledger=None,
        plan_review=None):
    """Validate a brief, analyse its inputs, and write the bundle.

    ``(directory, manifest)``. Nothing here collects: every byte it reads was
    already on disk when the command started.
    """
    brief = load(brief_path)
    plan = intake.load(plan) if isinstance(plan, (str, pathlib.Path)) else plan
    intake.check_transition(plan, brief)
    review = (intake_review.read(plan_review)
              if isinstance(plan_review, (str, pathlib.Path)) else plan_review)
    if review is not None:
        if plan is None:
            raise BundleError('an intake review reviews a plan; run this study with '
                              '--plan so the bundle can hold the revision it binds')
        intake_review.check_review(review, plan)
        if intake_review.status(review) == intake_review.FAIL:
            # A recorded blocker at intake is a planning outcome, not
            # authorisation to proceed through it (INTAKE §5). The study
            # is not run on a reading its own review says is wrong.
            failed = '; '.join(f'{name}: {findings}'
                               for name, findings in intake_review.failures(review))
            raise BundleError(f'the intake review records that plan {plan["id"]} '
                              f'revision {plan["revision"]} fails review — {failed}. '
                              f'Revise the plan and review the revision rather than '
                              f'running a study on a reading its review says misreads '
                              f'the request. Nothing was written.')
    ledger_snapshot = (session.load(session_ledger)
                       if isinstance(session_ledger, (str, pathlib.Path)) else session_ledger)
    if ledger_snapshot is not None:
        session.check(ledger_snapshot)
        # The snapshot travels with the study so it resumes without the working
        # ledger. A ledger that names another plan revision is not this study's.
        if ledger_snapshot['plan'] is not None:
            if plan is None:
                raise BundleError('the session ledger names a plan; run this study with '
                                  '--plan so the bundle can hold the same revision')
            expected = {'id': plan['id'], 'revision': plan['revision'],
                        'sha256': intake.digest(plan)}
            if ledger_snapshot['plan'] != expected:
                raise BundleError(f'the session ledger names plan '
                                  f'{ledger_snapshot["plan"]["id"]} revision '
                                  f'{ledger_snapshot["plan"]["revision"]}; this study runs '
                                  f'{plan["id"]} revision {plan["revision"]}. Revise the '
                                  f'ledger explicitly rather than snapshotting a stale one')
    inputs = input_digests(brief)
    ledger = audit.read(evidence) if evidence else audit.empty()
    if brief.category == 'basmati_rice':
        from ..evidence import legacy_basmati
        existing = {o['id']: o for o in ledger['observations']}
        for observation in legacy_basmati()['observations']:
            if observation['id'] not in existing:
                ledger['observations'].append(observation)
            elif existing[observation['id']] != observation:
                raise audit.AuditError('reserved legacy observation differs from the reviewed ledger')
    identity = study_id(brief, inputs, ledger)
    target = pathlib.Path(directory) if directory else \
        pathlib.Path(root) / identity
    if target.exists():
        if not force:
            raise BundleError(
                f'{target} already exists. The study id is derived from the '
                f'brief, the input digests and the contract versions, so this '
                f'is the same study over the same bytes — read it, or pass '
                f'--force to compute it again over the current code.')
        shutil.rmtree(target)

    result, cards = analyse(brief, plan=plan)
    fault = brief_fault(result)
    if fault:
        raise StudyError(f'{brief_path}: {fault} Nothing was written.')
    records = {f'{c["marketplace"]}:{c["asin"]}': c['validated'].record
               for c in cards}
    audit.check_claims(ledger, records, brief.as_of)
    write(brief, result, cards, target)
    if plan is not None:
        write_json_atomically(target / intake.SNAPSHOT, plan)
    if review is not None:
        write_json_atomically(target / intake_review.SNAPSHOT, review)
    if ledger_snapshot is not None:
        write_json_atomically(target / session.SNAPSHOT, ledger_snapshot)
    write_json_atomically(target / LEDGER, ledger)
    serialized = list(read_jsonl(target / CARDS))
    write_json_atomically(target / CLAIM_INDEX, audit.index(result, serialized, ledger))
    (target / REPORT).write_text(
        writeup.render(result, identity, inputs) + audit.render(ledger), encoding='utf-8')
    write_json_atomically(target / REVIEW, audit.review_template(target))
    write_json_atomically(target / VALIDATION, audit.validation_result(audit.review_template(target)))
    written = manifest(brief, result, identity, inputs, started_at,
                       finished_at, target)
    if ledger_snapshot is not None:
        # Integrity-bound, not identity-bearing (INTAKE §8): the same analysis
        # is the same study whatever the session spent reaching it.
        written['session'] = {'id': ledger_snapshot['id'],
                              'revision': ledger_snapshot['revision'],
                              'sha256': session.digest(ledger_snapshot)}
    if review is not None:
        # Approval travels in review artifacts and is checked before
        # delivery; it is never rendered into the report it approves
        # (INTAKE §11), and it does not enter study_id.
        written['intake_review'] = {'status': intake_review.status(review),
                                    'sha256': intake_review.digest(review)}
    write_json_atomically(target / MANIFEST, written)
    return target, written


# ---------------------------------------------------------------------------
# Reading a bundle back, and checking it still holds
# ---------------------------------------------------------------------------

def resolve_input(declared, manifest_data, directory, input_root=''):
    """Where this bundle's feed is now, and everywhere that was tried.

    A bundle outlives the working directory it was produced in, so the path
    written in the brief is a starting point rather than an address. Every
    place looked in is returned with the answer, because "input missing" is
    only actionable if it says where it looked.
    """
    tried = []
    if input_root:
        # Authoritative when given. Falling through to somewhere else after
        # an operator has said where the feeds are would verify a study
        # against files they did not mean, and report that it holds.
        roots = [pathlib.Path(input_root)]
    else:
        roots = []
        source = (manifest_data.get('brief_source') or {}).get('path') or ''
        if source:
            roots.append(pathlib.Path(source).parent)
        roots += [pathlib.Path(directory), pathlib.Path('.')]
    for root in roots:
        candidate = pathlib.Path(declared)
        candidate = candidate if candidate.is_absolute() else root / candidate
        if candidate not in tried:
            tried.append(candidate)
        if candidate.is_file():
            return candidate, tried
    return None, tried


def _compare(persisted, recomputed, label, findings, key=None):
    """Field-by-field, with the first differences named rather than counted."""
    if persisted == recomputed:
        return
    moved = []
    if isinstance(persisted, list) and isinstance(recomputed, list):
        if len(persisted) != len(recomputed):
            moved.append(f'{len(persisted)} entries persisted, '
                         f'{len(recomputed)} recomputed')
        for old, new in zip(persisted, recomputed):
            if old == new:
                continue
            if not isinstance(old, dict) or not isinstance(new, dict):
                moved.append(f'{old!r} → {new!r}')
                continue
            name = old.get(key) if key else None
            fields = ', '.join(sorted(
                f'{field} {old.get(field)!r} → {new.get(field)!r}'
                for field in set(old) | set(new)
                if old.get(field) != new.get(field)))
            moved.append(f'{name or "entry"}: {fields}')
    else:
        moved.append(f'{persisted!r} → {recomputed!r}')
    findings.append({
        'code': 'decision_moved',
        'message': f'{label} does not reproduce from these inputs: '
                   + '; '.join(moved[:5])
                   + (f' (and {len(moved) - 5} more)' if len(moved) > 5
                      else '')})


def verify(directory, input_root=''):
    """Re-derive this bundle from its own inputs and report what moved.

    Nothing is collected and nothing is written. The findings are ordered so
    that the ones that invalidate everything below them come first: an
    unreadable manifest, then an unsupported version, then a missing or
    altered artefact or input, and only then a decision that moved.
    """
    directory = pathlib.Path(directory)
    findings = []
    data = load_manifest(directory)

    version = data.get('manifest_version')
    if version != STUDY_MANIFEST_VERSION:
        findings.append({
            'code': 'unsupported_manifest_version',
            'message': f'{directory}: study manifest version {version!r}; '
                       f'this build reads version {STUDY_MANIFEST_VERSION}. '
                       f'Nothing below was checked.'})
        return data, findings

    unusable = set()
    # A snapshot must agree with both the manifest and the brief binding. Its
    # presence is optional only for legacy studies, not for a bound brief.
    optional = tuple(name for name in (intake.SNAPSHOT, intake_review.SNAPSHOT,
                                       delivery.RECORD, session.SNAPSHOT)
                     if name in (data.get('artifacts') or {})
                     or (directory / name).exists())
    for name in (*ARTIFACTS, *optional):
        path = directory / name
        recorded = (data.get('artifacts') or {}).get(name)
        if recorded is None:
            findings.append({
                'code': 'artifact_not_recorded',
                'message': f'{name} is not in the manifest\'s artifact list, '
                           f'so nothing can be said about it'})
            unusable.add(name)
            continue
        if not path.is_file():
            unusable.add(name)
            findings.append({
                'code': 'artifact_missing',
                'message': f'{name} is missing: the manifest records it at '
                           f'{recorded["bytes"]} bytes, digest '
                           f'{recorded["sha256"][:12]}. This bundle is '
                           f'incomplete.'})
            continue
        digest = sha256_file(path)
        if digest != recorded['sha256']:
            unusable.add(name)
            findings.append({
                'code': 'artifact_altered',
                'message': f'{name} has changed since the study wrote it: '
                           f'recorded {recorded["sha256"][:12]}, found '
                           f'{digest[:12]}. Its contents are not the study\'s '
                           f'own record any more.'})
    # Everything below re-derives the study from its own brief and compares
    # it with its own ranking and candidates. If either of those is missing or
    # altered there is nothing left to compare against, and a "decision moved"
    # finding on top of an "artefact altered" one would only obscure it.
    if unusable:
        return data, findings

    source = data.get('brief_source') or {}
    if source.get('path') and pathlib.Path(source['path']).is_file():
        digest = sha256_text(
            pathlib.Path(source['path']).read_text(encoding='utf-8'))
        if digest != source.get('sha256'):
            findings.append({
                'code': 'brief_source_changed',
                'message': f'{source["path"]} has changed since this study '
                           f'ran: recorded {str(source.get("sha256"))[:12]}, '
                           f'found {digest[:12]}. The bundle was checked '
                           f'against its own copy of the brief, not that '
                           f'file.'})

    persisted_brief = json.loads((directory / BRIEF).read_text(encoding='utf-8'))
    if ('intake' in persisted_brief) != (intake.SNAPSHOT in optional):
        findings.append({'code': 'intake_snapshot_missing',
                         'message': 'brief binding and bundle-internal intake snapshot must accompany each other'})
        return data, findings
    if persisted_brief.get('brief_version') != BRIEF_VERSION:
        findings.append({
            'code': 'unsupported_brief_version',
            'message': f'{BRIEF} declares brief_version '
                       f'{persisted_brief.get("brief_version")!r}; this build '
                       f'reads version {BRIEF_VERSION}. The decisions were '
                       f'not recomputed.'})
        return data, findings

    resolved, missing = [], False
    for declared in persisted_brief.get('inputs') or []:
        path, tried = resolve_input(declared, data, directory, input_root)
        if path is None:
            missing = True
            findings.append({
                'code': 'input_missing',
                'message': f'input {declared!r} was not found. Looked in: '
                           + ', '.join(str(item) for item in tried)
                           + '. Pass --input-root to say where the feeds are.'})
            continue
        resolved.append((declared, path))

    recorded_inputs = {item['declared']: item for item in data.get('inputs') or []}
    tampered = False
    for declared, path in resolved:
        recorded = recorded_inputs.get(declared)
        if recorded is None:
            findings.append({
                'code': 'input_not_recorded',
                'message': f'input {declared!r} is named by the brief but not '
                           f'by the manifest'})
            continue
        digest = sha256_file(path)
        if digest != recorded['sha256']:
            tampered = True
            findings.append({
                'code': 'input_altered',
                'message': f'{path} is not the file this study read: recorded '
                           f'{recorded["sha256"][:12]}, found {digest[:12]}. '
                           f'Every number below rests on those bytes, so the '
                           f'decisions were not recomputed.'})
    if missing or tampered:
        return data, findings

    code = data.get('code') or {}
    current = code_identity()
    for field in ('git_revision', 'extraction_schema_version',
                  'validated_contract_version'):
        if code.get(field) != current.get(field):
            findings.append({
                'code': 'code_changed',
                'message': f'produced at {field} {code.get(field)!r}, checked '
                           f'at {current.get(field)!r}. A decision that moved '
                           f'below moved because of that, not because of the '
                           f'evidence.'})

    try:
        from .brief import rehydrate
        brief = rehydrate(persisted_brief,
                          tuple(str(path) for _, path in resolved))
        plan = (intake.load(directory / intake.SNAPSHOT)
                if intake.SNAPSHOT in optional else None)
        result, _cards = analyse(brief, plan=plan)
    except (BriefError, StudyError, intake.PlanError) as exc:
        findings.append({'code': 'not_recomputable',
                         'message': f'{directory}: {exc}'})
        return data, findings

    stored = json.loads((directory / RANKING).read_text(encoding='utf-8'))
    if plan is not None and 'gates' not in stored:
        findings.append({
            'code': 'stage_gates_missing',
            'message': f'{RANKING} records no stage gates for a plan-backed '
                       f'study: the bundle predates R13 stage 6. Regenerate it '
                       f'from its brief and snapshot; its conclusion was never '
                       f'gated.'})
        return data, findings
    if 'gates' in stored:
        _compare(stored['stop'], result['stop'], 'the stop', findings)
        _compare(stored['gates'], result['gates'], 'the stage gates', findings)
    _compare(stored['outcome'], result['outcome'], 'the outcome', findings)
    _compare(stored['claims'], result['claims'], 'a numeric claim', findings,
             key='id')
    _compare(stored['shortlist'], result['shortlist'], 'the shortlist',
             findings)
    _compare(list(read_jsonl(directory / CANDIDATES)), result['candidates'],
             'a candidate decision', findings, key='asin')
    for key in ('ranking', 'constraints', 'classification', 'freshness'):
        _compare(stored[key], result[key], key, findings)
    serialized = [report_module.card_json(c) for c in
                  sorted((c for c in _cards if is_match(c)), key=lambda c: c['asin'])]
    _compare(list(read_jsonl(directory / CARDS)), serialized, 'evidence cards and scores', findings)
    try:
        ledger = audit.read(directory / LEDGER)
        records = {f'{c["marketplace"]}:{c["asin"]}': c['validated'].record for c in _cards}
        audit.check_claims(ledger, records, brief.as_of)
        expected_index = audit.index(result, serialized, ledger)
        _compare(json.loads((directory / CLAIM_INDEX).read_text()), expected_index,
                 'claim index', findings)
        expected_report = writeup.render(result, data['study_id'], data['inputs']) + audit.render(ledger)
        _compare((directory / REPORT).read_text(), expected_report, 'report', findings)
        review = json.loads((directory / REVIEW).read_text())
        audit.check_review(review, directory)
        validation = json.loads((directory / VALIDATION).read_text())
        if validation != audit.validation_result(review):
            raise audit.AuditError('saved validation does not match the audit/review')
    except (audit.AuditError, ValueError, TypeError, KeyError) as exc:
        findings.append({'code': 'report_invalid', 'message': str(exc)})
    if delivery.RECORD in optional:
        # Recomputed from each event's own frozen reference. This is the one
        # place a clock could leak into replay, and it does not.
        try:
            delivery.check(delivery.read(directory / delivery.RECORD), directory)
        except delivery.DeliveryError as exc:
            findings.append({'code': 'delivery_invalid', 'message': str(exc)})
    if session.SNAPSHOT in optional:
        # Shape and plan binding only: the ledger is a record of what the
        # session spent, and nothing in this analysis re-derives it.
        try:
            snapshot = session.load(directory / session.SNAPSHOT)
            recorded = data.get('session') or {}
            if recorded.get('sha256') != session.digest(snapshot):
                raise session.SessionError('the manifest names a different session ledger '
                                           'digest than the snapshot holds')
            if snapshot['plan'] is not None and plan is not None and snapshot['plan'] != {
                    'id': plan['id'], 'revision': plan['revision'], 'sha256': intake.digest(plan)}:
                raise session.SessionError('the session snapshot names another plan revision '
                                           'than the bundle holds')
        except session.SessionError as exc:
            findings.append({'code': 'session_invalid', 'message': str(exc)})
    if intake_review.SNAPSHOT in optional:
        # Binding only: the review is a reviewer's record, and nothing in this
        # analysis re-derives a judgement. What is checked is that it reviewed
        # this bundle's plan revision against the live catalogue, and that the
        # manifest names the same bytes and the same status.
        try:
            if plan is None:
                raise intake_review.IntakeReviewError(
                    'an intake review accompanies no intake plan snapshot: nothing '
                    'in this bundle is what it reviewed')
            review = intake_review.load(directory / intake_review.SNAPSHOT, plan)
            recorded = data.get('intake_review') or {}
            if recorded.get('sha256') != intake_review.digest(review) \
                    or recorded.get('status') != intake_review.status(review):
                raise intake_review.IntakeReviewError(
                    'the manifest names another intake review digest or status than '
                    'the snapshot holds')
        except intake_review.IntakeReviewError as exc:
            findings.append({'code': 'intake_review_invalid', 'message': str(exc)})
    return data, findings
