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
import datetime as _dt
import sys

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
                                    started_at=started, finished_at=_now())
    counts = manifest['counts']
    print(f'{manifest["study_id"]}  [{manifest["outcome"]}]')
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
    print(f'{manifest.get("study_id") or args.bundle}  '
          f'[{manifest.get("outcome")}]')
    if not findings:
        print('  verified      every artefact matches its digest, and every '
              'decision and numeric claim re-derives from the declared inputs')
        return 0
    for finding in findings:
        print(f'  {finding["code"]:<28} {finding["message"]}')
    print(f'  {len(findings)} finding(s). This bundle does not verify as it '
          f'stands.')
    return 1


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog='shopping_advisor.study',
        description='Persist and replay a research study, offline.')
    commands = parser.add_subparsers(dest='command', required=True)

    checking = commands.add_parser(
        'check', help='validate a brief and show how it will be read')
    checking.add_argument('brief', help='a .toml or .json brief')
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
    running.set_defaults(handler=run_command)

    verifying = commands.add_parser(
        'verify', help='re-derive a bundle from its own inputs and report '
                       'what moved')
    verifying.add_argument('bundle', help='data/studies/<study_id>')
    verifying.add_argument('--input-root', default='',
                           help='where the feeds the brief names are now, if '
                                'the bundle has been moved away from them')
    verifying.set_defaults(handler=verify_command)

    args = parser.parse_args(argv)
    try:
        return args.handler(args)
    except (BriefError, BundleError, StudyError) as exc:
        print(f'{exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
