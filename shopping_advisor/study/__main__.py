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
from . import audit, delivery, delivery_review, gates, intake, intake_review, session
from . import adaptation, capabilities, trial
from .controls import catalogue
from ..provenance import write_json_atomically
from .bundle import artifact_digests, code_caveats
from ..provenance import sha256_file
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
    for bound in brief.axis_bounds:
        span = ' '.join(part for part in (
            f'min {bound["min"]:g}' if bound['min'] is not None else '',
            f'max {bound["max"]:g}' if bound['max'] is not None else '') if part)
        print(f'  bound         {bound["axis"]} {span}'
              + (f' {bound["unit"]}' if bound['unit'] else '') + ' (before grouping)')
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
                                    plan=args.plan, session_ledger=args.session,
                                    plan_review=args.intake_review,
                                    adaptation_record=args.adaptation, trial=args.trial)
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
    print(f'  scope         {manifest["scope"]} ({manifest["scope_source"]})'
          + ('; run `study deliver` before issuing current advice'
             if manifest['scope'] == delivery.CURRENT_ADVICE else ''))
    if manifest.get('intake_review'):
        print(f'  intake review {manifest["intake_review"]["status"]}'
              + ('; pending is not approval' if manifest['intake_review']['status']
                 != intake_review.PASS else ''))
    if manifest.get('adaptation'):
        bound = manifest['adaptation']
        print(f'  adaptation    {bound["id"]} ({bound["layer"]}; method '
              f'{bound["descriptor_sha256"][:12]}; adoption {bound["adoption"]}'
              + ('; a trial measures a patch, it delivers nothing' if bound['adoption'] != 'accepted' else '')
              + ')')
    return 0


def deliver_command(args):
    """``deliver BUNDLE`` -- assess current advice at this delivery event."""
    directory = Path(args.bundle)
    manifest, findings = verify_bundle(directory, args.input_root)
    if findings:
        raise delivery.DeliveryError('Repair the bundle before delivering it: '
                                     + '; '.join(f['code'] for f in findings))
    if args.reference:
        reference, source, supplied = delivery.parse_reference(args.reference), delivery.DECLARED, args.reference
    else:
        reference, source, supplied = _now(), delivery.EXECUTION_CLOCK, ''
    path = directory / delivery.RECORD
    record = delivery.read(path) if path.is_file() else delivery.empty()
    event = delivery.assess_bundle(directory, reference, source, supplied)
    record['events'].append(event)
    write_json_atomically(path, record)
    manifest['artifacts'] = artifact_digests(directory)
    write_json_atomically(directory / 'manifest.json', manifest)
    print(f'{manifest["study_id"]}  [{event["current_advice"]}]')
    print(f'  reference     {event["reference"]} ({event["reference_source"]})')
    print(f'  scope         {event["scope"]} ({event["scope_source"]})')
    print(f'  governed      {event["counts"]["governed"]} observation(s), '
          f'{event["counts"]["stale"]} stale, {event["counts"]["undated"]} undated')
    for blocker in event['blockers']:
        print(f'  blocked       {blocker}')
    print(f'  statement     {event["statement"]}')
    print(f'  events        {len(record["events"])} in {path}')
    if event['current_advice'] == delivery.PERMITTED:
        print('  next          a permitted event is delivered as audited only with its own '
              'delivery review: `study delivery-review-template`, then `study review-delivery`')
    return 0


def verify_command(args):
    """``verify BUNDLE`` -- does this study still derive from its own inputs."""
    manifest, findings = verify_bundle(args.bundle, args.input_root)
    label = manifest.get('outcome')
    if manifest.get('stop'):
        label = f'{label} on the available axis; recommendation withheld: {manifest["stop"]}'
    print(f'{manifest.get("study_id") or args.bundle}  [{label}]')
    for caveat in code_caveats(manifest):
        print(f'  {"code":<28} {caveat}')
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
    status = {'scope': manifest.get('scope'), 'current_advice': 'no_record', 'reference': '',
              'review': 'absent'}
    # A bundle that does not verify is not read for its review either way.
    intake_state = 'not_checked' if findings else 'absent'
    if not findings:
        try:
            review = json.loads((Path(args.bundle) / 'semantic-review.json').read_text())
            audit.check_review(review, args.bundle, required=args.require_review)
            if audit.review_status(review) == 'fail':
                raise audit.AuditError('semantic review recorded failed checks')
        except (ValueError, OSError) as exc:
            findings.append({'code': 'semantic_review', 'message': str(exc)})
        # The intake-phase review. verify() has already checked that it binds
        # this bundle's plan revision; what matters here is what it recorded.
        # A failed intake review fails the bundle whatever the final review
        # says, and an audited plan-backed report needs a passing one.
        snapshot = Path(args.bundle) / intake_review.SNAPSHOT
        if snapshot.is_file():
            recorded = intake_review.read(snapshot)
            intake_state = intake_review.status(recorded)
            if intake_state == intake_review.FAIL:
                findings.append({'code': 'intake_review_failed',
                                 'message': 'the intake review records that the plan '
                                            'misreads the request: '
                                            + '; '.join(f'{n}: {f}' for n, f in
                                                        intake_review.failures(recorded))})
            elif args.require_review and intake_state != intake_review.PASS:
                findings.append({'code': 'intake_review_incomplete',
                                 'message': f'the intake review is {intake_state}; an audited '
                                            f'plan-backed report needs a completed passing one, '
                                            f'and pending or limited is not approval'})
        elif args.require_review and (Path(args.bundle) / intake.SNAPSHOT).is_file():
            findings.append({'code': 'intake_review_missing',
                             'message': 'a plan-backed study needs a separate intake review '
                                        'before it is delivered as audited; write one with '
                                        '`study plan-review-template` and attach it with '
                                        '`study review-intake`'})
        # Structural, and outside the review: a completed semantic review does
        # not waive a freshness block, and cannot be edited to.
        path = Path(args.bundle) / delivery.RECORD
        record = delivery.read(path) if path.is_file() else None
        event = delivery.latest(record) if record else None
        if event:
            status.update(current_advice=event['current_advice'], reference=event['reference'])
            # The delivery review of the latest event. verify() has checked that
            # every review binds its event; what matters here is what the one
            # for this event recorded, and whether a permitted current-advice
            # event has one at all when the report is delivered as audited.
            reviews_path = Path(args.bundle) / delivery_review.RECORD
            reviewed = (delivery_review.for_event(delivery_review.read_record(reviews_path),
                                                  len(record['events']) - 1)
                        if reviews_path.is_file() else None)
            status['review'] = delivery_review.status(reviewed) if reviewed else 'absent'
            if reviewed and status['review'] == delivery_review.FAIL:
                findings.append({'code': 'delivery_review_failed',
                                 'message': 'the delivery review of the latest event records a '
                                            'failure: ' + '; '.join(
                                                f'{n}: {i["findings"]}'
                                                for n, i in reviewed['checks'].items()
                                                if i['status'] == delivery_review.FAIL)})
            elif (args.require_review and manifest.get('scope') == delivery.CURRENT_ADVICE
                  and event['current_advice'] == delivery.PERMITTED
                  and status['review'] != delivery_review.PASS):
                findings.append({'code': ('delivery_review_incomplete' if reviewed
                                          else 'delivery_review_missing'),
                                 'message': f'a permitted current-advice event is delivered as '
                                            f'audited only with a passing delivery review of that '
                                            f'event (found: {status["review"]}); write one with '
                                            f'`study delivery-review-template` and attach it with '
                                            f'`study review-delivery`'})
        if manifest.get('scope') == delivery.CURRENT_ADVICE:
            if event is None:
                findings.append({'code': 'delivery_missing',
                                 'message': 'current-advice scope needs a delivery record; '
                                            'run `study deliver` at the delivery event'})
            elif event['current_advice'] != delivery.PERMITTED:
                findings.append({'code': 'current_advice_blocked',
                                 'message': event['statement']})
    structural = ('delivery_missing', 'current_advice_blocked', 'intake_review_failed',
                  'intake_review_incomplete', 'intake_review_missing', 'delivery_review_failed',
                  'delivery_review_missing', 'delivery_review_incomplete')
    semantic = audit.review_status(review) if not findings or all(
        f['code'] in structural for f in findings) else 'not_approved'
    print(json.dumps({'valid': not findings, 'semantic': semantic, 'intake_review': intake_state,
                      'delivery': status, 'code': code_caveats(manifest),
                      'findings': findings}, indent=2))
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


def _reference(args):
    if getattr(args, 'reference', None):
        return delivery.parse_reference(args.reference), delivery.DECLARED
    return _now(), delivery.EXECUTION_CLOCK


def _print_limits(rows):
    for row in rows:
        position = ('unreconciled: ' + ', '.join(row['unknown']) if row['remaining'] is None
                    else f'{row["remaining"]:g} remaining of {row["amount"]:g} '
                         f'({row["consumed"]:g} consumed, {row["reserved"]:g} reserved)')
        print(f'  {row["id"]:<20}{row["kind"]:<12}{row["unit"]:<15}{position}'
              + ('; exhausted' if row['exhausted'] else '')
              + (f'; deadline {row["deadline"]} passed' if row['deadline_passed'] else '')
              + (f'; {row["mode"]}: {row["overshoot"]}' if row['overshoot'] else ''))


def session_check_command(args):
    """``session-check LEDGER`` -- reconcile limits against recorded actions."""
    ledger = session.load(args.ledger)
    reference, _source = _reference(args)
    result = session.reconcile(ledger, reference)
    print(f'{ledger["id"]}: session ledger v{ledger["session_version"]}, revision '
          f'{ledger["revision"]}; {len(ledger["limits"])} limit(s), '
          f'{len(ledger["actions"])} action(s); '
          f'{"reconciled" if result["reconciled"] else "NOT reconciled"} at {reference}')
    _print_limits(result['limits'])
    for action in result['actions']:
        print(f'  {action["id"]:<20}{action["kind"]:<12}{action["state"]:<13}'
              f'{action["authorisation"] or "-":<10}{action["consumption_source"]}'
              + (f'; resumes {action["resumes"]}' if action['resumes'] else '')
              + (f'; replay of {action["replay_of"]}' if action['replay_of'] else ''))
    for name in result['interrupted']:
        print(f'  interrupted   {name}: not complete; resume it as a new action')
    for decision in result['prevented']:
        print(f'  prevented     {decision["action"]}: ' + ' | '.join(decision['reasons']))
    for decision in result['permitted']:
        print(f'  authorisable  {decision["action"]}')
    for name in result['proposals']:
        print(f'  proposal      {name}: engineering, retained; execution is R15')
    print('Records and a check, not a scheduler: nothing here ran or will run anything.')
    return 0 if result['reconciled'] else 1


def session_authorise_command(args):
    """``session-authorise LEDGER ACTION`` -- the check before a research action."""
    ledger = session.load(args.ledger)
    reference, _source = _reference(args)
    decision = session.authorise(ledger, args.action, reference)
    print(f'{args.action}: {"authorised" if decision["authorised"] else "REFUSED"} at {reference}')
    for reason in decision['reasons']:
        print(f'  refused       {reason}')
    for limit_id, remaining in (decision['remaining_after'].items() if decision['authorised'] else ()):
        print(f'  after         {limit_id}: {remaining:g} remaining')
    if decision['authorised'] and args.record:
        action = next(a for a in ledger['actions'] if a['id'] == args.action)
        action.update(state='authorised', authorisation='checked')
        session.check(ledger)
        write_json_atomically(args.ledger, ledger)
        print(f'  recorded      {args.action} is authorised in {args.ledger}; it has not run')
    return 0 if decision['authorised'] else 1


def session_record_command(args):
    """``session-record LEDGER ACTION`` -- what an action did, from its manifest."""
    ledger = session.load(args.ledger)
    consumption = json.loads(args.consumption) if args.consumption else None
    session.record(ledger, args.action, args.run, state=args.state or '',
                   consumption=consumption, assume_allocation=args.assume_allocation,
                   started_at=args.started_at or '', finished_at=args.finished_at or '',
                   result=json.loads(args.result) if args.result else None,
                   promotion=json.loads(args.promotion) if args.promotion else None,
                   adaptation_record=args.adaptation)
    write_json_atomically(args.ledger, ledger)
    action = next(a for a in ledger['actions'] if a['id'] == args.action)
    print(f'{args.action}: {action["state"]}; consumption from {action["consumption_source"]}'
          f'{" (authorisation unchecked)" if action["authorisation"] == "unchecked" else ""}')
    for unit, amount in action['consumption'].items():
        print(f'  {unit:<15}{"unknown" if amount is None else f"{amount:g}"}')
    if action['run_manifest']:
        print(f'  manifest      {action["run_manifest"]["path"]} · {action["run_manifest"]["sha256"][:12]}')
    return 0


def resume_command(args):
    """``resume BUNDLE`` -- verified state and permitted next actions, or the gap."""
    reference, source = _reference(args)
    ledger = session.load(args.session) if args.session else None
    report = session.resume(args.bundle, ledger, reference, source, args.input_root)
    print(f'{report["study_id"] or args.bundle}  '
          f'[{"resumable" if report["resumable"] else "NOT resumable"}]')
    for finding in report['findings']:
        print(f'  {finding["code"]:<28} {finding["message"]}')
    if report['plan']['bundle']:
        print(f'  plan          {report["plan"]["bundle"]["id"]} revision '
              f'{report["plan"]["bundle"]["revision"]}'
              + {True: ' (the ledger agrees)', False: ' (the ledger DISAGREES)',
                 None: ''}[report['plan']['match']])
    if report['resources']:
        _print_limits(report['resources']['limits'])
    for name in report['interrupted']:
        print(f'  interrupted   {name}: never assumed complete')
    print(f'  review        {report["review"] or "none"}')
    print(f'  intake review {report["intake_review"] or "none"}')
    if report['delivery_review'] is not None:
        print(f'  delivery rev. {report["delivery_review"]} (latest event)')
    latest, recheck = report['delivery']['latest'], report['delivery']['recheck']
    if latest:
        print(f'  delivered     {latest["current_advice"]} at {latest["reference"]}')
    if recheck:
        print(f'  recheck       {recheck["current_advice"]} at {recheck["reference"]} '
              f'({recheck["reference_source"]}); {recheck["note"]}')
    for step in report['next_actions']:
        print(f'  {step["status"]:<13} {step["action"]}'
              + (': ' + ' | '.join(step['reasons']) if step['reasons'] else ''))
    return 0 if report['resumable'] else 1


def controls_command(args):
    print(json.dumps(catalogue(args.category), indent=2, ensure_ascii=False))
    return 0


def capabilities_command(args):
    # The gate's committed examples are the replayed studies a row lists; the
    # import is local so that the index itself owes the gate nothing.
    from ..maintenance import load_baseline
    data = capabilities.index(category_key=args.category,
                              marketplace=args.marketplace or '',
                              examples=load_baseline()['examples'])
    print(json.dumps(data, indent=2, ensure_ascii=False))
    return 0


def plan_check_command(args):
    plan = intake.load(args.plan)
    if args.brief:
        intake.check_transition(plan, load(args.brief))
    print(f'{plan["id"]}: valid intake plan v{plan["plan_version"]}, '
          f'revision {plan["revision"]}; {len(plan["requirements"])} requirements.')
    readiness = gates.intake_gate(plan)
    rows = readiness['requirements']
    # The id column grows with the longest id so a long id (``marketplace_scope``)
    # keeps at least one space before the disposition; 14 keeps the fixtures' layout.
    width = max([14] + [len(row['id']) + 1 for row in rows])
    for row in rows:
        print(f'  {row["id"]:<{width}}{row["disposition"]:<18}{row["role"]}, '
              f'{row["settlement"]}, by {row["author"]}'
              + ('; restricts the conclusion' if row['restricts_conclusion'] else ''))
    print(f'  {"readiness":<{width}}{readiness["readiness"]}')
    print(f'  {"next action":<{width}}{readiness["next_action"]}')
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


def plan_review_template_command(args):
    """``plan-review-template PLAN -o OUT`` -- a pending review bound to this revision."""
    plan = intake.load(args.plan)
    review = intake_review.template(plan)
    output = Path(args.output)
    if output.suffix != '.json' or output.exists():
        raise intake_review.IntakeReviewError('choose a new .json output for the review template')
    write_json_atomically(output, review)
    print(f'{output}: pending intake review bound to {plan["id"]} revision '
          f'{plan["revision"]} ({review["plan"]["sha256"][:12]}); catalogue '
          f'{review["basis"]["catalogue_sha256"][:12] or "none (unregistered category)"}.')
    for name in intake_review.CHECKS:
        print(f'  {name:<14}{intake_review.QUESTIONS[name]}')
    for limit in review['review_limits']:
        print(f'  limit         {limit["kind"].replace("_", " ")}'
              + (f' in {limit["message_id"]}' if limit['message_id'] else '')
              + f': {limit["description"]} — '
              + ' and '.join(intake_review.BLOCKED_BY[limit['kind']]) + ' cannot pass')
    print('Pending is not approval. Fill each check with a reviewer and findings in a '
          'separate pass; a failure names the requirements or user messages it concerns.')
    return 0


def plan_review_command(args):
    """``plan-review PLAN REVIEW`` -- does this review bind this revision, and what does it say."""
    plan = intake.load(args.plan)
    review = intake_review.load(args.review, plan)
    word = intake_review.status(review)
    print(f'{plan["id"]} revision {plan["revision"]}: intake review '
          f'v{review["intake_review_version"]} binds this revision '
          f'({review["plan"]["sha256"][:12]}) and the live {plan["category"]} catalogue; '
          f'status {word}.')
    print(f'  reviewer      {review["reviewer"] or "(none yet)"}')
    for name in intake_review.CHECKS:
        item = review['checks'][name]
        refs = ', '.join(item['requirement_ids'] + item['message_ids'])
        print(f'  {name:<14}{item["status"]:<9}{item["findings"]}'
              + (f' [{refs}]' if refs else ''))
    for limit in review['review_limits']:
        print(f'  limit         {limit["kind"].replace("_", " ")}'
              + (f' in {limit["message_id"]}' if limit['message_id'] else '')
              + f': {limit["description"]}')
    for text in review['unresolved_limits']:
        print(f'  unresolved    {text}')
    print('A binding and a record, not execution authority: a passing intake review '
          'says the plan reads the retained request faithfully and its controls '
          'answer it, not that the buyer confirmed it.')
    return 1 if word == intake_review.FAIL else 0


def review_intake_command(args):
    """``review-intake BUNDLE REVIEW`` -- attach an intake review to a plan-backed bundle."""
    directory = Path(args.bundle)
    manifest, findings = verify_bundle(directory, args.input_root)
    if findings:
        raise intake_review.IntakeReviewError('Repair the bundle before attaching an intake '
                                             'review: ' + '; '.join(f['code'] for f in findings))
    if not (directory / intake.SNAPSHOT).is_file():
        raise intake_review.IntakeReviewError(f'{directory}: not a plan-backed study; there is '
                                             f'no plan revision for an intake review to bind')
    review = intake_review.load(args.review, intake.load(directory / intake.SNAPSHOT))
    word = intake_review.status(review)
    final = json.loads((directory / 'semantic-review.json').read_text(encoding='utf-8'))
    if audit.review_status(final) != 'pending':
        raise intake_review.IntakeReviewError(
            f'{directory}: the final semantic review is completed and rests on the intake '
            f'review this bundle holds; attaching another would supersede it. Final approval '
            f'requires valid intake findings (INTAKE §11), so the intake review comes first: '
            f're-run the study with --intake-review and review the new bundle.')
    write_json_atomically(directory / intake_review.SNAPSHOT, review)
    manifest['intake_review'] = {'status': word, 'sha256': intake_review.digest(review)}
    # The pending final-review template names the intake findings it will
    # rest on, so it is refreshed to name the ones now in the bundle.
    template = audit.review_template(directory)
    write_json_atomically(directory / 'semantic-review.json', template)
    write_json_atomically(directory / 'validation.json', audit.validation_result(template))
    manifest['artifacts'] = artifact_digests(directory)
    write_json_atomically(directory / 'manifest.json', manifest)
    print(f'{manifest["study_id"]}  [intake review {word}]')
    for name in intake_review.CHECKS:
        print(f'  {name:<14}{review["checks"][name]["status"]}')
    if word == intake_review.FAIL:
        print('  The review records that this plan revision misreads the request. '
              'validate-report fails until the plan is revised and the study re-run.')
    elif word != intake_review.PASS:
        print('  Pending or limited is not approval; --require-review will not accept it.')
    return 0


def delivery_review_template_command(args):
    """``delivery-review-template BUNDLE -o OUT`` -- a pending review bound to one event."""
    directory = Path(args.bundle)
    manifest, findings = verify_bundle(directory, args.input_root)
    # A stale review of the very event being reviewed is what the new review
    # replaces, not a reason to refuse it; everything else still blocks.
    findings = delivery_review.blocking(
        findings, directory, delivery_review.event_position(directory, args.event))
    if findings:
        raise delivery_review.DeliveryReviewError(
            'Repair the bundle before reviewing a delivery: ' + '; '.join(f['code'] for f in findings))
    review = delivery_review.template(directory, args.event)
    output = Path(args.output)
    if output.suffix != '.json' or output.exists():
        raise delivery_review.DeliveryReviewError('choose a new .json output for the review template')
    write_json_atomically(output, review)
    print(f'{output}: pending delivery review of event {review["event"]} '
          f'({review["current_advice"]} at {review["reference"]}) of {manifest["study_id"]}; '
          f'semantic review {review["semantic_review"]["status"]}.')
    for name in delivery_review.CHECKS:
        print(f'  {name:<24}{delivery_review.QUESTIONS[name]}')
    print('  attestation             who delivered it, whether the reference was read honestly '
          'and whether the declared scope is true -- a statement signed by name, not a proof')
    print('Pending is not approval. A later delivery is a new event and needs its own review.')
    return 0


def review_delivery_command(args):
    """``review-delivery BUNDLE REVIEW`` -- attach a delivery review to the event it binds."""
    directory = Path(args.bundle)
    manifest, findings = verify_bundle(directory, args.input_root)
    findings = delivery_review.blocking(
        findings, directory, delivery_review.read(args.review)['event'])
    if findings:
        raise delivery_review.DeliveryReviewError(
            'Repair the bundle before attaching a delivery review: '
            + '; '.join(f['code'] for f in findings))
    review = delivery_review.load(args.review, directory)
    word = delivery_review.status(review)
    path = directory / delivery_review.RECORD
    record = delivery_review.read_record(path) if path.is_file() else delivery_review.empty()
    write_json_atomically(path, delivery_review.attach(record, review))
    manifest['artifacts'] = artifact_digests(directory)
    write_json_atomically(directory / 'manifest.json', manifest)
    print(f'{manifest["study_id"]}  [delivery review {word}: event {review["event"]}, '
          f'{review["current_advice"]} at {review["reference"]}]')
    for name in delivery_review.CHECKS:
        print(f'  {name:<24}{review["checks"][name]["status"]}')
    attested = review['attestation']
    print(f'  attestation             by {attested["by"] or "(nobody yet)"}; reference read '
          f'honestly: {attested["reference_read_honestly"]}; declaration true: '
          f'{attested["declaration_true"]}')
    if word == delivery_review.FAIL:
        print('  The review records that this delivery does not hold. validate-report fails '
              'until a later event is delivered and reviewed.')
    elif word != delivery_review.PASS:
        print('  Pending is not approval; --require-review will not accept it for current advice.')
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




# ---------------------------------------------------------------------------
# R15: adaptation inside a study
# ---------------------------------------------------------------------------

def _print_record(record):
    patch, checks = record['patch'], record['checks']
    print(f'{record["id"]}  [{record["layer"]}; adoption {record["adoption"]["decision"]}; '
          f'review {record["review"]["verdict"]}]')
    print(f'  origin        {record["origin"]["session_id"]}/{record["origin"]["action_id"]}'
          + (f'; plan {record["origin"]["plan_id"]} r{record["origin"]["plan_revision"]}'
             if record['origin']['plan_id'] else ''))
    print(f'  budget        {record["budget"]["seconds"]} s, {record["budget"]["attempts"]} attempt(s); '
          f'used {record["consumption"]["seconds"] if record["consumption"]["seconds"] is not None else "unknown"} s, '
          f'{record["attempts"]} attempt(s)')
    print(f'  base          {record["base"]["git_revision"][:12] or "(no git revision)"} '
          f'tree {record["base"]["tree_sha256"][:12] or "(not captured)"}')
    print(f'  patch         {len(patch["files"])} file(s) {patch["sha256"][:12] or ""}; '
          f'result tree {record["result_tree_sha256"][:12] or "(not captured)"}; '
          f'method {record["descriptor_sha256"][:12]}')
    print(f'  evaluator     {"frozen" if record["evaluator"]["frozen"] else "NOT proven frozen" if record["evaluator"]["frozen"] is False else "not checked"}'
          f' ({len(record["evaluator"]["files"])} file(s))')
    for move in record['baseline_moves']:
        print(f'  baseline move {move}')
    if record['inspection']:
        flagged = {k: v for k, v in record['inspection']['flags'].items() if v}
        print(f'  inspection    ' + (', '.join(f'{k} ×{len(v)}' for k, v in flagged.items()) or 'nothing flagged'))
        for finding in record['inspection']['findings']:
            print(f'    finding     {finding}')
    for index, check in enumerate(checks):
        print(f'  check {index:<7} {" ".join(check["command"])[:70]} → {check["summary"]} '
              f'({check["seconds"]:g} s, {check["boundary"]})')
    if record['runner']['boundary']:
        print(f'  runner        {record["runner"]["boundary"]}; profile {record["runner"]["profile_sha256"][:12]}; '
              f'timeout {record["runner"]["timeout_seconds"]} s'
              + (f'; exception: {record["runner"]["exception"]}' if record['runner']['exception'] else ''))
    if record['rollback']['demonstrated']:
        print(f'  rollback      demonstrated at {record["rollback"]["demonstrated_at"]}')


def adaptation_template_command(args):
    """``adaptation-template`` -- name the gap; capture and run nothing yet."""
    ledger = session.load(args.session)
    if not session.executes(ledger):
        raise adaptation.AdaptationError(f'{args.session} is a v{ledger["session_version"]} ledger; '
                                         f'engineering executes only under session ledger v2')
    action = next((a for a in ledger['actions'] if a['id'] == args.action), None)
    if action is None or action['kind'] != 'engineering':
        raise adaptation.AdaptationError(f'{args.action} is not an engineering action of {ledger["id"]}')
    plan = intake.load(args.plan) if args.plan else None
    record = adaptation.template(args.id, args.layer, args.hypothesis, ledger['id'], args.action,
                                 args.seconds, args.attempts, plan=plan)
    write_json_atomically(args.output, record)
    _print_record(record)
    print(f'  written       {args.output}; next: patch in a worktree, then adaptation-capture')
    return 0


def adaptation_capture_command(args):
    """``adaptation-capture`` -- the patch as an archive, inspected before any import."""
    record = adaptation.load(args.record)
    captured = trial.capture(args.base, args.worktree)
    record['base'] = captured['base']
    record['patch']['files'] = captured['files']
    record['result_tree_sha256'] = captured['result_tree_sha256']
    record['lock_sha256'] = captured['lock_sha256']
    record['evaluator'] = captured['evaluator']
    record['inspection'] = trial.inspect(captured['files'], args.base)
    if args.method_versions:
        record['method_versions'] = json.loads(args.method_versions)
    if args.baseline_move:
        record['baseline_moves'] = list(args.baseline_move)
    if not captured['files']:
        raise trial.TrialError(f'{args.worktree} does not differ from {args.base}: nothing to capture')
    adaptation.seal(record)
    write_json_atomically(args.record, record)
    _print_record(record)
    blocked = record['inspection']['flags']['evaluator'] or not record['evaluator']['frozen']
    if blocked:
        print('  refused       the patch touches the evaluator set, or the set is not byte-identical to '
              'the base revision: this change goes through ordinary maintenance, not an adaptation')
    return 1 if blocked else 0


def _runner_paths(venv, interpreter):
    """The locked environment and its interpreter as absolute paths.

    The check runs with the worktree as its working directory, and a worktree
    holds no ``.venv``: the second adaptation's first attempt exec'd a relative
    ``.venv/bin/python`` there and ``sandbox-exec`` exited 71 before any import,
    which counted as an attempt. Resolve both here, against the directory the
    command was typed in, before anything changes directory.
    """
    venv = str(Path(venv).resolve())
    interpreter = str(Path(interpreter).resolve()) if interpreter else str(Path(venv) / 'bin' / 'python')
    return venv, interpreter


def adaptation_probe_command(args):
    """``adaptation-probe`` -- demonstrate the boundary with failure cases."""
    venv, interpreter = _runner_paths(args.venv, args.interpreter)
    result = trial.probe(args.worktree, args.scratch, interpreter, venv, args.outside)
    print(f'boundary probe  [{"demonstrated" if result["demonstrated"] else "NOT demonstrated"}]')
    for name, expected in result['expected'].items():
        observed = result['results'].get(name, 'no answer')
        print(f'  {name:<14}{observed:<24}{"" if observed == expected else f"expected {expected}"}')
    print(f'  leaked        {"yes" if result["leaked"] else "no file appeared outside the scratch directory"}')
    print(f'  profile       {result["profile_sha256"][:12]}; exit {result["check"]["exit"]}; '
          f'{result["check"]["seconds"]:g} s; log {result["check"]["output_path"]}')
    return 0 if result['demonstrated'] else 1


def adaptation_run_command(args):
    """``adaptation-run RECORD -- COMMAND`` -- one check inside the boundary, recorded."""
    if not args.command:
        raise trial.TrialError('name the command after `--`, e.g. `-- python -m unittest discover -s tests`')
    record = adaptation.load(args.record)
    if record['inspection'] is None or not record['patch']['files']:
        raise trial.TrialError('capture and inspect the patch before running anything from it')
    if record['inspection']['flags']['evaluator']:
        raise trial.TrialError('the patch touches the evaluator set; it is not run as an adaptation')
    if record['attempts'] >= record['budget']['attempts']:
        raise trial.TrialError(f'{record["attempts"]} of {record["budget"]["attempts"]} attempts used: '
                               f'exhaustion stops new work. The record keeps what was done')
    spent = record['consumption']['seconds'] or 0
    if spent >= record['budget']['seconds']:
        raise trial.TrialError(f'{spent:g} of {record["budget"]["seconds"]} seconds used: exhaustion '
                               f'stops new work. The record keeps what was done')
    worktree, scratch = Path(args.worktree), Path(args.scratch)
    if trial.evaluator_digest(worktree) != record['evaluator']['base_sha256']:
        record['evaluator']['frozen'] = False
        adaptation.seal(record)
        write_json_atomically(args.record, record)
        raise trial.TrialError('the evaluator set in the worktree is not the base revision\'s: a gate '
                               'the patch may have rewritten judges nothing. Refused, and recorded')
    venv, interpreter = _runner_paths(args.venv, args.interpreter)
    boundary = 'harness-only' if args.exception else 'kernel'
    profile_path = None
    if boundary == 'kernel':
        if not trial.available():
            raise trial.TrialError('no kernel boundary can be demonstrated here (sandbox-exec is absent '
                                   'or refused). The default is to stop: record the blocker. The '
                                   'maintainer may record an exception and pass --exception, which '
                                   'labels the check harness-only and counts toward no Done-when')
        scratch.mkdir(parents=True, exist_ok=True)
        profile_path = scratch / 'profile.sb'
        profile_path.write_text(trial.profile(worktree, scratch, interpreter, venv), encoding='utf-8')
    timeout = args.timeout or min(record['budget']['seconds'] - spent, 3600)
    check = trial.execute(args.command, worktree, scratch, timeout, profile_path, interpreter, boundary)
    record['checks'].append(check)
    record['attempts'] += 1
    record['consumption']['seconds'] = round(spent + check['seconds'], 3)
    record['runner'] = {'boundary': boundary,
                        'profile_sha256': sha256_file(profile_path) if profile_path else '',
                        'interpreter': interpreter, 'tmpdir': str(scratch / 'tmp'),
                        'timeout_seconds': int(timeout), 'exception': args.exception or ''}
    if check['timed_out'] and record['adoption']['decision'] == 'pending':
        pass  # the record says interrupted through the check; adoption stays the maintainer's
    adaptation.seal(record)
    write_json_atomically(args.record, record)
    _print_record(record)
    return 0 if check['exit'] == 0 else 1


def adaptation_review_command(args):
    """``adaptation-review`` -- a reviewer's verdict, bound to the patch and checks it read."""
    record = adaptation.load(args.record)
    record['review'] = {'reviewer': args.reviewer, 'verdict': args.verdict,
                        'findings': list(args.finding or []),
                        'patch_sha256': record['patch']['sha256'],
                        'checks_sha256': adaptation.checks_digest(record)}
    adaptation.seal(record)
    write_json_atomically(args.record, record)
    _print_record(record)
    return 0


def adaptation_adopt_command(args):
    """``adaptation-adopt`` -- the decision, by a role, once."""
    record = adaptation.load(args.record)
    if record['adoption']['decision'] != 'pending':
        raise adaptation.AdaptationError(f'{record["id"]} is already {record["adoption"]["decision"]}; '
                                         f'a decision is recorded once')
    record['adoption'] = {'decision': args.decision, 'decided': _now(), 'by': args.by,
                          'reason': args.reason}
    adaptation.seal(record)
    write_json_atomically(args.record, record)
    _print_record(record)
    return 0


def adaptation_rollback_command(args):
    """``adaptation-rollback`` -- prove the base still stands: tree, evaluator, gate."""
    record = adaptation.load(args.record)
    base = Path(args.base)
    problems = []
    if trial.tree_digest(base) != record['base']['tree_sha256']:
        problems.append('the base tree is not the tree the record captured')
    if trial.evaluator_digest(base) != record['evaluator']['base_sha256']:
        problems.append('the evaluator set at the base is not the one the record captured')
    if problems:
        print('rollback  [NOT demonstrated]')
        for problem in problems:
            print(f'  {problem}')
        return 1
    if not args.skip_gate:
        import subprocess
        done = subprocess.run((sys.executable, '-m', 'shopping_advisor', 'maintenance', 'check'),
                              cwd=base, capture_output=True, text=True, timeout=3600)
        if done.returncode != 0:
            print('rollback  [NOT demonstrated]: the gate does not pass at the base')
            print(done.stdout[-2000:])
            return 1
    record['rollback'] = {'instructions': list(args.instruction or record['rollback']['instructions']),
                          'demonstrated': True, 'demonstrated_at': _now()}
    adaptation.seal(record)
    write_json_atomically(args.record, record)
    print(f'rollback  [demonstrated at {record["rollback"]["demonstrated_at"]}]: the base tree, its '
          f'evaluator set and the gate stand as the record captured them')
    return 0


def adaptation_check_command(args):
    """``adaptation-check RECORD`` -- validate and print the record."""
    _print_record(adaptation.load(args.record))
    return 0

def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    # ``adaptation-run RECORD [options] -- COMMAND...``: the command after the
    # separator is the trial's, not this parser's, and is handed over whole.
    trial_command = []
    if argv and argv[0] == 'adaptation-run' and '--' in argv:
        separator = argv.index('--')
        trial_command, argv = argv[separator + 1:], argv[:separator]
    parser = argparse.ArgumentParser(
        prog='shopping_advisor.study',
        description='Persist and replay a research study, offline.')
    commands = parser.add_subparsers(dest='command', required=True)

    controls = commands.add_parser(
        'controls', help='inspect live category controls and their limits as JSON')
    controls.add_argument('--category', required=True,
                          help='registered category key (no default)')
    controls.set_defaults(handler=controls_command)

    capability_index = commands.add_parser(
        'capabilities', help='the capability index as JSON: what each registered '
                             'capability has earned, where it applies, what it '
                             'declines and the evidence behind it')
    capability_index.add_argument('--category', default=None,
                                  help='one registered category key (default: all)')
    capability_index.add_argument('--marketplace', default='',
                                  help='a marketplace host to compare each row '
                                       'against, e.g. www.amazon.de')
    capability_index.set_defaults(handler=capabilities_command)

    planning = commands.add_parser('plan-check', help='validate an intake plan without feeds')
    planning.add_argument('plan', help=f'JSON plan, conventionally under {intake.DEFAULT_PLAN_ROOT}/')
    planning.add_argument('--brief', help='also check the plan-to-brief transition')
    planning.set_defaults(handler=plan_check_command)
    readback = commands.add_parser('plan-readback', help='render this plan revision for read-back')
    readback.add_argument('plan')
    readback.add_argument('--record', action='store_true',
                          help='save presented bytes with no-response status; never confirms')
    readback.set_defaults(handler=plan_readback_command)
    review_template = commands.add_parser(
        'plan-review-template', help='write a pending intake review bound to this plan revision')
    review_template.add_argument('plan')
    review_template.add_argument('-o', '--output', required=True, help='new JSON review path')
    review_template.set_defaults(handler=plan_review_template_command)
    plan_review = commands.add_parser(
        'plan-review', help='check an intake review against its plan and print what it records')
    plan_review.add_argument('plan')
    plan_review.add_argument('review', help='intake review JSON, pending or completed')
    plan_review.set_defaults(handler=plan_review_command)
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
    running.add_argument('--session', help='session resource ledger to snapshot inside the bundle')
    running.add_argument('--intake-review',
                         help='intake review bound to the plan, snapshotted inside the bundle; '
                              'a review recording a failure refuses the run')
    running.add_argument('--adaptation',
                         help='R15: the adaptation record whose method this study rests on; '
                              'its descriptor enters the study id and the record travels in the bundle')
    running.add_argument('--trial', action='store_true',
                         help='run on an adaptation that is not yet adopted, to measure its patch; '
                              'the manifest says so and the bundle delivers nothing')
    running.set_defaults(handler=run_command)

    ledger_check = commands.add_parser(
        'session-check', help='reconcile a session ledger: limits, actions, what is prevented')
    ledger_check.add_argument('ledger', help=f'JSON ledger, conventionally under {session.DEFAULT_SESSION_ROOT}/')
    ledger_check.add_argument('--reference', help='ISO 8601 instant for deadlines; default reads the clock')
    ledger_check.set_defaults(handler=session_check_command)
    authorising = commands.add_parser(
        'session-authorise', help='check one planned action against the remaining limits')
    authorising.add_argument('ledger')
    authorising.add_argument('action')
    authorising.add_argument('--reference', help='ISO 8601 instant for deadlines; default reads the clock')
    authorising.add_argument('--record', action='store_true',
                             help='mark the action authorised in the ledger when it fits')
    authorising.set_defaults(handler=session_authorise_command)
    recording = commands.add_parser(
        'session-record', help='record what an action did, from its run manifest')
    recording.add_argument('ledger')
    recording.add_argument('action')
    recording.add_argument('--run', help='crawl run directory whose manifest reports the consumption')
    recording.add_argument('--adaptation',
                           help='engineering (ledger v2): the adaptation record whose checks report '
                                'the seconds and attempts')
    recording.add_argument('--state', choices=session.DONE,
                           help='without a run: whether it completed or was interrupted')
    recording.add_argument('--consumption', help='without a run: JSON table of unit -> amount, declared')
    recording.add_argument('--assume-allocation', action='store_true',
                           help='without a run: count the whole allocation as spent')
    recording.add_argument('--started-at')
    recording.add_argument('--finished-at')
    recording.add_argument('--result', help='probe: JSON {"summary", "next_action"}')
    recording.add_argument('--promotion',
                           help='probe: JSON {"promoted", "into", "changed_criteria", '
                                '"supplied_candidates", "assessment"}')
    recording.set_defaults(handler=session_record_command)
    resuming = commands.add_parser(
        'resume', help='verify retained artifacts and say which next actions the ledger permits')
    resuming.add_argument('bundle', help='data/studies/<study_id>')
    resuming.add_argument('--session', help='working ledger; default is the bundle snapshot')
    resuming.add_argument('--reference', help='ISO 8601 instant for the freshness recheck; default reads the clock')
    resuming.add_argument('--input-root', default='')
    resuming.set_defaults(handler=resume_command)

    delivering = commands.add_parser(
        'deliver', help='assess current advice at this delivery event and '
                        'freeze the reference in the bundle')
    delivering.add_argument('bundle', help='data/studies/<study_id>')
    delivering.add_argument('--reference',
                            help='ISO 8601 instant with offset to assess against, '
                                 'recorded as declared; default reads the clock')
    delivering.add_argument('--input-root', default='')
    delivering.set_defaults(handler=deliver_command)

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
    reviewing_intake = commands.add_parser(
        'review-intake', help='attach a separate intake review to a plan-backed bundle')
    reviewing_intake.add_argument('bundle')
    reviewing_intake.add_argument('review', help='intake review JSON bound to the bundle\'s plan revision')
    reviewing_intake.add_argument('--input-root', default='')
    reviewing_intake.set_defaults(handler=review_intake_command)
    delivery_template = commands.add_parser(
        'delivery-review-template',
        help='write a pending delivery review bound to one delivery event of a bundle')
    delivery_template.add_argument('bundle')
    delivery_template.add_argument('-o', '--output', required=True, help='new JSON review path')
    delivery_template.add_argument('--event', type=int, default=None,
                                   help='event position in delivery.json; default the latest')
    delivery_template.add_argument('--input-root', default='')
    delivery_template.set_defaults(handler=delivery_review_template_command)
    reviewing_delivery = commands.add_parser(
        'review-delivery', help='attach a delivery review to the event it binds')
    reviewing_delivery.add_argument('bundle')
    reviewing_delivery.add_argument('review', help='delivery review JSON bound to one event of this bundle')
    reviewing_delivery.add_argument('--input-root', default='')
    reviewing_delivery.set_defaults(handler=review_delivery_command)
    adapting = commands.add_parser(
        'adaptation-template', help='R15: a new adaptation record naming the gap, the ledger action and the budget')
    adapting.add_argument('id', help='slug for the adaptation')
    adapting.add_argument('--session', required=True, help='session ledger (v2) holding the engineering action')
    adapting.add_argument('--action', required=True, help='the engineering action id in that ledger')
    adapting.add_argument('--layer', required=True, choices=adaptation.LAYERS)
    adapting.add_argument('--hypothesis', required=True, help='what the patch is expected to change, and why')
    adapting.add_argument('--seconds', required=True, type=int, help='budget in seconds of runner time')
    adapting.add_argument('--attempts', required=True, type=int, help='budget in checks run')
    adapting.add_argument('--plan', help='the intake plan revision the gap was found in')
    adapting.add_argument('-o', '--output', required=True, help='new JSON record path')
    adapting.set_defaults(handler=adaptation_template_command)
    capturing = commands.add_parser(
        'adaptation-capture', help='R15: archive the patch between a base tree and a worktree and inspect it statically')
    capturing.add_argument('record')
    capturing.add_argument('--base', required=True, help='the base checkout (trusted side)')
    capturing.add_argument('--worktree', required=True, help='the patched worktree')
    capturing.add_argument('--method-versions', help='JSON table of capability key -> method version the patch declares')
    capturing.add_argument('--baseline-move', action='append',
                           help='one baseline move the patch needs at adoption (a new capability, a new '
                                'test module, a moved floor); repeat. Declared here so a check the frozen '
                                'evaluator fails for exactly this reason can still be accepted after review')
    capturing.set_defaults(handler=adaptation_capture_command)
    probing = commands.add_parser(
        'adaptation-probe', help='R15: demonstrate the execution boundary with failure cases')
    probing.add_argument('--worktree', required=True)
    probing.add_argument('--scratch', required=True, help='the one writable directory, inside the worktree')
    probing.add_argument('--venv', default='.venv', help='the locked virtual environment to read')
    probing.add_argument('--interpreter', default='', help='default: <venv>/bin/python')
    probing.add_argument('--outside', required=True, help='a directory outside the worktree the probe must not reach')
    probing.set_defaults(handler=adaptation_probe_command)
    running_check = commands.add_parser(
        'adaptation-run', help='R15: run one check on the patched worktree inside the boundary and record it')
    running_check.add_argument('record')
    running_check.add_argument('--worktree', required=True)
    running_check.add_argument('--scratch', required=True, help='the one writable directory, inside the worktree')
    running_check.add_argument('--venv', default='.venv')
    running_check.add_argument('--interpreter', default='')
    running_check.add_argument('--timeout', type=int, default=0, help='seconds; default: the remaining budget')
    running_check.add_argument('--exception', default='',
                               help='the maintainer\'s recorded exception (ledger revision or message ref) '
                                    'that permits a harness-only boundary; the check is labelled so')
    running_check.set_defaults(handler=adaptation_run_command, command=[])
    reviewing_adaptation = commands.add_parser(
        'adaptation-review', help='R15: record a reviewer\'s verdict bound to the patch and checks as they stand')
    reviewing_adaptation.add_argument('record')
    reviewing_adaptation.add_argument('--reviewer', required=True)
    reviewing_adaptation.add_argument('--verdict', required=True, choices=[v for v in adaptation.VERDICTS if v != 'pending'])
    reviewing_adaptation.add_argument('--finding', action='append', help='one finding; repeat')
    reviewing_adaptation.set_defaults(handler=adaptation_review_command)
    adopting = commands.add_parser(
        'adaptation-adopt', help='R15: record the adoption decision, once, by a role')
    adopting.add_argument('record')
    adopting.add_argument('--decision', required=True, choices=[d for d in adaptation.DECISIONS if d != 'pending'])
    adopting.add_argument('--by', required=True, help='the deciding role, never a person')
    adopting.add_argument('--reason', required=True)
    adopting.set_defaults(handler=adaptation_adopt_command)
    rolling_back = commands.add_parser(
        'adaptation-rollback', help='R15: demonstrate that the base tree, its evaluator and the gate still stand')
    rolling_back.add_argument('record')
    rolling_back.add_argument('--base', required=True)
    rolling_back.add_argument('--instruction', action='append', help='one rollback instruction; repeat')
    rolling_back.add_argument('--skip-gate', action='store_true', help='digests only; do not run the gate at the base')
    rolling_back.set_defaults(handler=adaptation_rollback_command)
    checking_adaptation = commands.add_parser('adaptation-check', help='R15: validate and print an adaptation record')
    checking_adaptation.add_argument('record')
    checking_adaptation.set_defaults(handler=adaptation_check_command)
    args = parser.parse_args(argv)
    if trial_command:
        args.command = trial_command
    try:
        return args.handler(args)
    except (BriefError, BundleError, StudyError, audit.AuditError,
            delivery.DeliveryError, session.SessionError, OSError, ValueError) as exc:
        print(f'{exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
