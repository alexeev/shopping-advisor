"""Command line for the local maintenance gate.

    uv run --offline --locked python -m shopping_advisor maintenance check
    uv run --offline --locked python -m shopping_advisor maintenance baseline

``check`` is the authoritative verification entry point. Developers and
coding agents run the same command, and the maintenance workflow's "run the
full offline suite" step is this one command rather than a list somebody has
to keep in their head. ``--only`` narrows a run while iterating; it never
counts as the gate, and the output says so.

``baseline`` prints what the gate is entitled to find. ``baseline --update``
re-records the measured floors after a change that legitimately moved them,
and refuses while the gate is failing: a baseline is a claim about a tree
that passes.

Exit status is 0 when there is nothing to report, 1 when a check failed,
and 2 when the gate could not be read or run at all.
"""

import argparse
import json
import sys

from . import (BASELINE_PATH, CHECKS, GateError, load_baseline, measure,
               run_gate)
from ..provenance import write_json_atomically


def _emit(results, guard, partial=False):
    findings = list(guard)
    for result in results:
        findings.extend(result.findings)
    status = 'pass' if not findings else 'FAIL'
    scope = ' (partial run: not the gate)' if partial else ''
    print(f'maintenance gate  [{status}]{scope}')
    for finding in guard:
        print(f'  {"baseline":<14}{finding.code}: {finding.message}')
    for result in results:
        mark = ' ' if result.passed else '!'
        print(f' {mark}{result.name:<14}{result.summary}')
        for finding in result.findings:
            for index, line in enumerate(finding.message.splitlines()):
                label = f'{finding.code}: ' if index == 0 else ''
                print(f'    {label}{line}')
    if findings:
        print(f'  {len(findings)} finding(s). This tree does not pass the '
              f'gate as it stands.')
    return findings


def check_command(args):
    baseline = load_baseline(args.baseline)
    only = set(args.only) if args.only else None
    if only:
        unknown = only - set(CHECKS)
        if unknown:
            raise GateError(f'unknown check(s): {", ".join(sorted(unknown))}. '
                            f'Known: {", ".join(sorted(CHECKS))}')
    results, guard = run_gate(baseline, root=args.root, only=only)
    if args.json:
        findings = list(guard) + [finding for result in results
                                  for finding in result.findings]
        print(json.dumps({
            'gate': 'partial' if only else 'complete',
            'passed': not findings,
            'checks': [{'name': result.name, 'summary': result.summary,
                        'passed': result.passed,
                        'findings': [finding.as_dict()
                                     for finding in result.findings]}
                       for result in results],
            'baseline_findings': [finding.as_dict() for finding in guard],
        }, indent=2))
        return 1 if findings else 0
    return 1 if _emit(results, guard, partial=bool(only)) else 0


def baseline_command(args):
    baseline = load_baseline(args.baseline)
    if not args.update:
        print(json.dumps(baseline, indent=2))
        return 0
    updated, results = measure(baseline, root=args.root)
    findings = _emit(results, [])
    if findings:
        print('\nThe baseline is unchanged: it records a tree that passes, '
              'and this one does not.')
        return 1
    write_json_atomically(args.baseline, updated)
    print(f'\nRecorded {args.baseline}. Review the diff: it is the statement '
          f'that this is the new floor.')
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog='shopping_advisor.maintenance',
        description='The local, version-controlled maintenance gate.')
    parser.add_argument('--baseline', default=BASELINE_PATH,
                        help='the tracked gate baseline (default: the '
                             'committed one)')
    parser.add_argument('--root', default=None,
                        help='the repository root to check (default: this '
                             'checkout)')
    commands = parser.add_subparsers(dest='command', required=True)

    checking = commands.add_parser(
        'check', help='run every required check against the baseline')
    checking.add_argument('--only', action='append', metavar='CHECK',
                          help=f'run one check while iterating; a partial '
                               f'run is not the gate. One of: '
                               f'{", ".join(sorted(CHECKS))}')
    checking.add_argument('--json', action='store_true',
                          help='machine-readable findings')
    checking.set_defaults(handler=check_command)

    recording = commands.add_parser(
        'baseline', help='show, or deliberately re-record, the floors')
    recording.add_argument('--update', action='store_true',
                           help='re-record the measured floors from a tree '
                                'that passes')
    recording.set_defaults(handler=baseline_command)

    args = parser.parse_args(argv)
    if args.root is None:
        from . import ROOT
        args.root = ROOT
    try:
        return args.handler(args)
    except (GateError, OSError, ValueError) as exc:
        print(f'{exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
