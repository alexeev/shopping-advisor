"""Command line for saved studies.

    uv run --offline --locked python -m shopping_advisor.study check  BRIEF
    uv run --offline --locked python -m shopping_advisor.study run    BRIEF
    uv run --offline --locked python -m shopping_advisor.study verify BUNDLE

``check`` validates a brief and prints what it will be read as, including
every default it fell back to. It reads no feeds beyond confirming they
exist, so it is the cheap step to run while writing one.

``run`` analyses the feeds the brief names and writes a study bundle under
``data/studies/<study id>``. It collects nothing: every byte it reads was on
disk before the command started.

``verify`` re-derives the decisions from the bundle's own brief and inputs and
reports what moved. It is the command that distinguishes a study that still
holds from one whose inputs, brief or analysis code have changed underneath
it -- and it is how another environment picks up a study without collecting
again.

Exit status is 0 when there is nothing to report, 1 when a check failed, and
2 when the brief or the bundle could not be read at all.
"""

import argparse
import json
from pathlib import Path
from . import audit, gates, intake
from .controls import catalogue
from ..provenance import write_json_atomically
from .bundle import artifact_digests
import datetime as _dt
import sys
import os
from dataclasses import replace

from ..analysis import categories  # noqa: F401  (registers the built-ins)
from .analysis import StudyError
from .brief import BriefError, load
from .bundle import (DEFAULT_STUDY_ROOT, BundleError, REPORT, run as run_study,
                     verify as verify_bundle)


def _now():
    return _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat()


def check_command(args):
    """``check BRIEF`` -- is this brief usable, and what will it be read as."""
    brief = load(args.brief)
    intake.check_transition(intake.load(args.plan) if args.plan else None, brief)
    print(f'{args.brief}: valid brief v{brief.brief_version} '
          f'`{brief.id}` · {brief.category} on {brief.marketplace}')
    print(f'  question      {brief.question}')
    for declared, resolved in zip(brief.inputs, brief.resolved_inputs):
        print(f'  input         {declared} -> {resolved}')
    print(f'  axis          {brief.axis or "(the category default)"}')
    print(f'  unit          {brief.unit or "(whatever the evidence measures)"}')
    print(f'  requires      {", ".join(brief.require_claims) or "(nothing)"}')
    print('  limit         '
          + (f'{brief.max_axis_value:g} on the axis'
             if brief.max_axis_value is not None else '(none)'))
    print(f'  enough to     at least {brief.minimum_candidates} candidate(s)'
          + (f', {brief.decisive_margin:.1%} apart'
             if brief.decisive_margin is not None else ''))
    print('  as of         '
          + (brief.as_of or '(not stated: freshness is not assessed)'))
    if not brief.as_of:
        print('  NOTE          without freshness.as_of nothing in the report '
              'can say how old these observations are.')
    return 0


def run_command(args):
    """``run BRIEF`` -- analyse the feeds it names and persist the study."""
    started = _now()
    directory, manifest = run_study(args.brief, directory=args.output,
                                    root=args.root, force=args.force,
                                    started_at=started, finished_at=_now(), evidence=args.evidence,
                                    plan=args.plan)
    counts = manifest['counts']
    label = manifest['outcome']
    if manifest.get('stop'):
        label = (f'{manifest["outcome"]} on the available axis; recommendation '
                 f'withheld: {manifest["stop"]}')
    print(f'{manifest["study_id"]}  [{label}]')
    print(f'  brief         {manifest["brief_id"]} '
          f'({manifest["brief_source"]["path"]})')
    print(f'  inputs        ' + ', '.join(
        f'{item["declared"]} ({item["records"]} records)'
        for item in manifest['inputs']))
    print(f'  classified    '
          f'{manifest["classification"]["matched"]} of '
          f'{manifest["classification"]["records"]} as {manifest["category"]}')
    print(f'  ranking       {counts["offers"]} offer(s), '
          f'{counts["excluded"]} excluded, '
          f'{counts["filtered_out"]} short of a required claim')
    print(f'  shortlisted   {counts["shortlisted"]}')
    print(f'  bundle        {directory}')
    print(f'  report        {directory / REPORT}')
    return 0


def verify_command(args):
    """``verify BUNDLE`` -- does this study still derive from its own inputs."""
    manifest, findings = verify_bundle(args.bundle, args.input_root)
    label = manifest.get('outcome')
    if manifest.get('stop'):
        label = f'{label} on the available axis; recommendation withheld: {manifest["stop"]}'
    print(f'{manifest.get("study_id") or args.bundle}  [{label}]')
    if not findings:
        print('  verified      every artefact matches its digest, and every '
              'decision and numeric claim re-derives from the declared inputs')
        return 0
    for finding in findings:
        print(f'  {finding["code"]:<28} {finding["message"]}')
    print(f'  {len(findings)} finding(s). This bundle does not verify as it '
          f'stands.')
    return 1


def validate_command(args):
    try:
        manifest, findings = verify_bundle(args.bundle, args.input_root)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(json.dumps({'valid': False, 'findings': [{'code': 'unreadable_bundle', 'message': str(exc)}]}))
        return 2
    if not findings:
        try:
            review = json.loads((Path(args.bundle) / 'semantic-review.json').read_text())
            audit.check_review(review, args.bundle, required=args.require_review)
            if audit.review_status(review) == 'fail':
                raise audit.AuditError('semantic review recorded failed checks')
        except (ValueError, OSError) as exc:
            findings.append({'code': 'semantic_review', 'message': str(exc)})
    print(json.dumps({'valid': not findings, 'semantic': audit.review_status(review) if not findings else 'not_approved', 'findings': findings}, indent=2))
    return 1 if findings else 0


def review_command(args):
    directory = Path(args.bundle)
    manifest, findings = verify_bundle(directory)
    if findings:
        raise audit.AuditError('Repair bundle before attaching review: ' + str(findings))
    review = json.loads(Path(args.review).read_text())
    audit.check_review(review, directory)
    write_json_atomically(directory / 'semantic-review.json', review)
    validation = audit.validation_result(review)
    write_json_atomically(directory / 'validation.json', validation)
    manifest['artifacts'] = artifact_digests(directory)
    write_json_atomically(directory / 'manifest.json', manifest)
    print('Semantic review attached to the checked report bytes.')
    return 0


def controls_command(args):
    print(json.dumps(catalogue(args.category), indent=2, ensure_ascii=False))
    return 0


def plan_check_command(args):
    plan = intake.load(args.plan)
    if args.brief:
        intake.check_transition(plan, load(args.brief))
    print(f'{plan["id"]}: valid intake plan v{plan["plan_version"]}, '
          f'revision {plan["revision"]}; {len(plan["requirements"])} requirements.')
    readiness = gates.intake_gate(plan)
    for row in readiness['requirements']:
        print(f'  {row["id"]:<14}{row["disposition"]:<18}{row["role"]}, '
              f'{row["settlement"]}, by {row["author"]}'
              + ('; restricts the conclusion' if row['restricts_conclusion'] else ''))
    print(f'  readiness     {readiness["readiness"]}')
    print(f'  next action   {readiness["next_action"]}')
    print('Structural preservation only; not semantic approval or execution authority.')
    return 0


def plan_readback_command(args):
    plan = intake.load(args.plan)
    text = intake.render_readback(plan)
    if args.record:
        if plan['readback']['response']['status'] != 'not_presented':
            raise intake.PlanError('read-back already recorded; revise explicitly instead of overwriting a response')
        plan['readback']['text'] = text
        plan['readback']['response']['status'] = 'no_response'
        intake.check(plan)
        write_json_atomically(args.plan, plan)
    print(text, end='')
    return 0


def plan_bind_command(args):
    plan, brief = intake.load(args.plan), load(args.brief)
    bound = replace(brief, intake=intake.binding(plan))
    intake.check_transition(plan, bound)
    output = Path(args.output)
    if output.suffix != '.json' or output.exists():
        raise intake.PlanError('choose a new .json output for the bound brief')
    data = bound.as_dict()
    data.pop('source')
    data['inputs'] = [os.path.relpath(Path(path).resolve(), output.parent.resolve())
                      for path in brief.resolved_inputs]
    write_json_atomically(output, data)
    print(f'{output}: requirements bound; existing brief controls were checked, not changed.')
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog='shopping_advisor.study',
        description='Persist and replay a research study, offline.')
    commands = parser.add_subparsers(dest='command', required=True)

    controls = commands.add_parser(
        'controls', help='inspect live category controls and their limits as JSON')
    controls.add_argument('--category', required=True,
                          help='registered category key (no default)')
    controls.set_defaults(handler=controls_command)

    planning = commands.add_parser('plan-check', help='validate an intake plan without feeds')
    planning.add_argument('plan', help=f'JSON plan, conventionally under {intake.DEFAULT_PLAN_ROOT}/')
    planning.add_argument('--brief', help='also check the plan-to-brief transition')
    planning.set_defaults(handler=plan_check_command)
    readback = commands.add_parser('plan-readback', help='render this plan revision for read-back')
    readback.add_argument('plan')
    readback.add_argument('--record', action='store_true',
                          help='save presented bytes with no-response status; never confirms')
    readback.set_defaults(handler=plan_readback_command)
    binding = commands.add_parser('plan-bind', help='bind requirements after checking existing brief controls')
    binding.add_argument('brief')
    binding.add_argument('--plan', required=True)
    binding.add_argument('-o', '--output', required=True, help='new JSON brief path')
    binding.set_defaults(handler=plan_bind_command)

    checking = commands.add_parser(
        'check', help='validate a brief and show how it will be read')
    checking.add_argument('brief', help='a .toml or .json brief')
    checking.add_argument('--plan', help='intake plan required by a bound brief')
    checking.set_defaults(handler=check_command)

    running = commands.add_parser(
        'run', help='analyse the feeds a brief names and write the bundle')
    running.add_argument('brief', help='a .toml or .json brief')
    running.add_argument('-o', '--output', default='',
                         help='write the bundle here instead of under --root')
    running.add_argument('--root', default=DEFAULT_STUDY_ROOT,
                         help=f'where bundles live (default {DEFAULT_STUDY_ROOT})')
    running.add_argument('--force', action='store_true',
                         help='replace an existing bundle of the same study id')
    running.add_argument('--evidence', help='versioned external ledger with indexed claims (JSON)')
    running.add_argument('--plan', help='intake plan to check and snapshot inside the bundle')
    running.set_defaults(handler=run_command)

    verifying = commands.add_parser(
        'verify', help='re-derive a bundle from its own inputs and report '
                       'what moved')
    verifying.add_argument('bundle', help='data/studies/<study_id>')
    verifying.add_argument('--input-root', default='',
                           help='where the feeds the brief names are now, if '
                                'the bundle has been moved away from them')
    verifying.set_defaults(handler=verify_command)

    validating = commands.add_parser('validate-report', help='JSON deterministic report validation')
    validating.add_argument('bundle')
    validating.add_argument('--input-root', default='')
    validating.add_argument('--require-review', action='store_true')
    validating.set_defaults(handler=validate_command)
    reviewing = commands.add_parser('review', help='attach a separate completed semantic checklist')
    reviewing.add_argument('bundle')
    reviewing.add_argument('review', help='completed review JSON, bound to report digest')
    reviewing.set_defaults(handler=review_command)
    args = parser.parse_args(argv)
    try:
        return args.handler(args)
    except (BriefError, BundleError, StudyError, audit.AuditError, OSError, ValueError) as exc:
        print(f'{exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
