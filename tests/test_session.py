"""Stage 8: the session resource ledger and resumption from retained artifacts.

INTAKE §7 and cases 15 and 18 in intake/README.md state the expectations:
declared limits in units the environment observes, action records linked to
the manifests crawls actually write, reconciliation that never counts a replay
as acquisition or a resumed action twice and never reads unknown as zero, a
next-action check that refuses what does not fit, an exhaustion stop that keeps
completed evidence and names what it prevents, probe evidence promoted only
explicitly with its selection-bias record, and resumption from verified
artifacts alone with delivery freshness rechecked.

Every reference here is declared and fixed, and nothing here runs a crawl: a
run manifest is produced by the same ``CrawlRun`` the spider uses, closed or
left open, and the ledger reads it.
"""
import contextlib
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from shopping_advisor import maintenance
from shopping_advisor import run as run_module
from shopping_advisor.analysis import categories  # noqa: F401
from shopping_advisor.study import bundle, delivery, intake, session
from shopping_advisor.study.__main__ import main

HERE = Path(__file__).resolve().parent
INTAKE = HERE / 'intake'
STUDIES = HERE / 'studies'
BRONZE = STUDIES / 'pasta-bronze-die.toml'
LEDGER = INTAKE / 'session-ledger.json'
PLAN, BRIEF = INTAKE / 'delivered-cost-plan.json', INTAKE / 'delivered-cost-brief.json'
AT = '2026-09-17T00:00:00+00:00'
LATER = '2026-10-17T00:00:00+00:00'


class SessionCase(unittest.TestCase):
    def setUp(self):
        self.directory = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.ledger = session.load(LEDGER)

    def action(self, name, ledger=None):
        return next(a for a in (ledger or self.ledger)['actions'] if a['id'] == name)

    def limit(self, name, ledger=None):
        return next(r for r in session.reconcile(ledger or self.ledger, AT)['limits'] if r['id'] == name)

    def write(self, name, data):
        path = self.directory / name
        path.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
        return path

    def cli(self, *argv):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            status = main([str(a) for a in argv])
        return status, output.getvalue()

    def crawl(self, close=True, stats=None):
        """A real run manifest, from the object the spider writes through."""
        run = run_module.CrawlRun(
            root=str(self.directory / 'runs'), spider='amazon_product',
            marketplace='www.amazon.de',
            locale={'language': 'de', 'accept_language': 'de-DE,de;q=0.9', 'status': 'matches'},
            arguments={'keyword': ['spaghetti']}).open()
        if close:
            run.close(stats=stats if stats is not None else {
                'downloader/request_count': 57, 'downloader/response_count': 52,
                'item_scraped_count': 40, 'elapsed_time_seconds': 412.5}, finish_reason='finished')
        else:
            for handle in ('_discovery', '_index'):
                getattr(run, handle).close()
        return run.directory

    def study(self, name='bundle', ledger=LEDGER, plan=PLAN, brief=BRIEF, **kwargs):
        return bundle.run(str(brief), directory=str(self.directory / name), plan=str(plan) if plan else None,
                          session_ledger=str(ledger) if isinstance(ledger, Path) else ledger,
                          started_at='2026-09-16T00:00:00+00:00', finished_at='2026-09-16T00:00:01+00:00',
                          **kwargs)


class Contract(SessionCase):
    def test_closed_fields_and_vocabularies(self):
        for change in (lambda l: l.update(session_version=2),
                       lambda l: l.update(scheduler='cron'),
                       lambda l: l.update(revision=2),
                       lambda l: l['limits'][0].update(unit='megabytes'),
                       lambda l: l['limits'][0].update(kind='purchase'),
                       lambda l: l['limits'][0].update(amount=float('inf')),
                       lambda l: l['limits'][0].update(amount=12.5),
                       lambda l: l['actions'][0].update(kind='deploy'),
                       lambda l: l['actions'][0].update(state='done'),
                       lambda l: l['actions'][1].update(command='scrapy crawl')):
            ledger = copy.deepcopy(self.ledger)
            change(ledger)
            with self.subTest(change=change), self.assertRaises(session.SessionError):
                session.check(ledger)

    def test_units_are_what_the_manifest_reports_and_estimates_say_so(self):
        for unit, measurement in (('responses', 'estimate'), ('eur', 'observed')):
            ledger = copy.deepcopy(self.ledger)
            ledger['limits'][0].update(unit=unit, measurement=measurement, amount=10)
            with self.subTest(unit=unit), self.assertRaisesRegex(session.SessionError, 'measurement'):
                session.check(ledger)
        ledger = copy.deepcopy(self.ledger)
        ledger['limits'].append(dict(self.ledger['limits'][0], id='spend', unit='eur', amount=3.5,
                                     measurement='estimate', note=''))
        with self.assertRaisesRegex(session.SessionError, 'how the estimate is made'):
            session.check(ledger)
        ledger['limits'][-1]['note'] = 'Estimated from provider list prices; not measured here.'
        session.check(ledger)

    def test_a_strict_ceiling_needs_a_mechanism_and_names_its_overshoot(self):
        ledger = copy.deepcopy(self.ledger)
        ledger['limits'][0]['mode'] = 'strict_ceiling'     # responses: enforceable
        ledger['limits'][0]['note'] = ''
        with self.assertRaisesRegex(session.SessionError, 'known overshoot'):
            session.check(ledger)
        ledger['limits'][0]['note'] = 'CLOSESPIDER_PAGECOUNT per run; in-flight requests overshoot.'
        row = self.limit('research-responses', session.check(ledger))
        self.assertIn('in flight', row['overshoot'])
        for unit in ('requests', 'runs', 'pages_retained'):
            ledger = copy.deepcopy(self.ledger)
            ledger['limits'][0].update(unit=unit, mode='strict_ceiling', note='n/a')
            with self.subTest(unit=unit), self.assertRaisesRegex(session.SessionError, 'no mechanism enforces'):
                session.check(ledger)
        ledger = copy.deepcopy(self.ledger)
        ledger['limits'].append(dict(self.ledger['limits'][0], id='spend', unit='eur', amount=3,
                                     measurement='estimate', mode='strict_ceiling', note='estimate'))
        with self.assertRaisesRegex(session.SessionError, 'no mechanism enforces'):
            session.check(ledger)

    def test_research_and_engineering_allowances_are_kept_apart(self):
        ledger = copy.deepcopy(self.ledger)
        self.action('engineer-1', ledger)['limit_ids'] = ['research-seconds']
        with self.assertRaisesRegex(session.SessionError, 'does not fund engineering'):
            session.check(ledger)
        ledger = copy.deepcopy(self.ledger)
        self.action('probe-1', ledger)['limit_ids'].append('engineering-seconds')
        with self.assertRaisesRegex(session.SessionError, 'does not fund research'):
            session.check(ledger)

    def test_engineering_is_a_proposal_and_never_authorised_or_recorded(self):
        ledger = copy.deepcopy(self.ledger)
        for state in ('authorised', 'running', 'completed'):
            self.action('engineer-1', ledger).update(state=state, authorisation='checked',
                                                     started_at=AT, consumption={'seconds': 1},
                                                     consumption_source='declared')
            with self.subTest(state=state), self.assertRaisesRegex(session.SessionError, 'retained as a proposal'):
                session.check(ledger)
        decision = session.authorise(self.ledger, 'engineer-1', AT)
        self.assertFalse(decision['authorised'])
        self.assertIn('controlled execution and its gates are R15', decision['reasons'][0])
        with self.assertRaisesRegex(session.SessionError, 'retained proposal'):
            session.record(copy.deepcopy(self.ledger), 'engineer-1', state='completed', assume_allocation=True)
        self.assertEqual(session.reconcile(self.ledger, AT)['proposals'], ['engineer-1'])

    def test_inspection_and_analysis_touch_nothing_live(self):
        ledger = copy.deepcopy(self.ledger)
        self.action('inspect-1', ledger)['limit_ids'].append('research-responses')
        self.action('inspect-1', ledger)['allocation']['responses'] = 5
        self.action('inspect-1', ledger)['consumption']['responses'] = 5
        with self.assertRaisesRegex(session.SessionError, 'may not allocate acquisition units'):
            session.check(ledger)
        ledger = copy.deepcopy(self.ledger)
        self.action('analyse-1', ledger)['run_id'] = 'some-run'
        with self.assertRaisesRegex(session.SessionError, 'no crawl run to link'):
            session.check(ledger)

    def test_a_probe_has_a_question_a_finite_live_allocation_a_result_and_a_promotion_record(self):
        for change, message in ((lambda a: a.update(question=''), 'question'),
                                (lambda a: a['allocation'].update(responses=0) or a['consumption'].update(responses=0), 'finite, positive'),
                                (lambda a: a.update(result=None), 'result that determines the next action'),
                                (lambda a: a.update(promotion=None), 'whether its evidence was promoted')):
            ledger = copy.deepcopy(self.ledger)
            change(self.action('probe-1', ledger))
            with self.subTest(message=message), self.assertRaisesRegex(session.SessionError, message):
                session.check(ledger)

    def test_collection_is_only_what_a_brief_declares(self):
        ledger = copy.deepcopy(self.ledger)
        ledger['plan'] = None
        with self.assertRaisesRegex(session.SessionError, 'the ledger names its plan'):
            session.check(ledger)

    def test_an_extension_is_an_explicit_revision_naming_the_previous_digest(self):
        ledger = copy.deepcopy(self.ledger)
        ledger['limits'][0]['amount'] = 400
        ledger['limits'][1]['amount'] = 3600
        ledger['revision'] = 2
        with self.assertRaisesRegex(session.SessionError, 'explicit budget revision'):
            session.check(ledger)
        ledger['supersedes'] = session.digest(self.ledger)
        session.check(ledger)
        self.assertTrue(session.authorise(ledger, 'collect-2', AT)['authorised'])

    def test_the_contract_is_discovered_and_pinned(self):
        self.assertEqual(maintenance._contract_versions()['session_ledger'], session.SESSION_VERSION)
        with patch.object(session, 'SESSION_VERSION', 2):
            findings = maintenance.check_contracts(maintenance.load_baseline()).findings
            self.assertTrue(any(f.code == 'contract_version' and 'session_ledger' in f.message for f in findings))


class RecordingFromManifests(SessionCase):
    """Consumption is read from what the crawl wrote, in its own units."""

    def planned_probe(self, ledger):
        probe = self.action('probe-1', ledger)
        probe.update(state='planned', authorisation='', started_at='', finished_at='',
                     consumption={}, consumption_source='unknown', result=None, promotion=None)
        return probe

    def test_a_closed_run_records_completion_and_the_manifest_counts(self):
        ledger = copy.deepcopy(self.ledger)
        probe = self.planned_probe(ledger)
        run_dir = self.crawl(close=True)
        with self.assertRaisesRegex(session.SessionError, 'result that determines'):
            session.record(copy.deepcopy(ledger), 'probe-1', run_dir)
        session.record(ledger, 'probe-1', run_dir, result=dict(summary='No page states a shipping cost.', next_action='Run the bounded study.'), promotion=dict(promoted=False, into='none', changed_criteria=False, supplied_candidates=False, assessment=''))
        self.assertEqual(probe['state'], 'completed')
        self.assertEqual(probe['consumption'], {'responses': 52, 'seconds': 412.5})
        self.assertEqual(probe['consumption_source'], 'run_manifest')
        self.assertEqual(probe['authorisation'], 'unchecked')
        manifest = run_module.load_manifest(run_dir)
        self.assertEqual(probe['run_id'], manifest['run_id'])
        self.assertEqual(probe['run_manifest']['path'], str(run_dir / 'manifest.json'))
        self.assertEqual(probe['started_at'], manifest['started_at'])
        self.assertTrue(probe['finished_at'])

    def test_an_interrupted_run_is_interrupted_and_its_consumption_unknown_not_zero(self):
        ledger = copy.deepcopy(self.ledger)
        self.planned_probe(ledger)
        session.record(ledger, 'probe-1', self.crawl(close=False))
        probe = self.action('probe-1', ledger)
        self.assertEqual(probe['state'], 'interrupted')
        self.assertEqual(probe['consumption'], {'responses': None, 'seconds': None})
        self.assertEqual(probe['finished_at'], '')
        self.assertIsNone(probe['result'], 'an interrupted probe determined no next action')
        rows = session.reconcile(ledger, AT)
        self.assertFalse(rows['reconciled'])
        self.assertEqual(self.limit('research-responses', ledger)['unknown'], ['probe-1'])
        self.assertIsNone(self.limit('research-responses', ledger)['remaining'])
        decision = session.authorise(ledger, 'collect-2', AT)
        self.assertFalse(decision['authorised'])
        self.assertTrue(any('cannot be reconciled' in r for r in decision['reasons']), decision['reasons'])

    def test_the_conservative_record_counts_the_whole_allocation(self):
        ledger = copy.deepcopy(self.ledger)
        probe = self.planned_probe(ledger)
        probe.update(result=dict(summary='s', next_action='n'),
                     promotion=dict(promoted=False, into='none', changed_criteria=False,
                                    supplied_candidates=False, assessment=''))
        session.record(ledger, 'probe-1', state='interrupted', assume_allocation=True, started_at=AT)
        self.assertEqual(probe['consumption'], probe['allocation'])
        self.assertEqual(probe['consumption_source'], 'assumed_allocation')
        self.assertTrue(session.reconcile(ledger, AT)['reconciled'])
        self.assertEqual(self.limit('research-responses', ledger)['remaining'], 300 - 60 - 200)

    def test_a_finished_action_is_never_recorded_twice(self):
        with self.assertRaisesRegex(session.SessionError, 'count it twice'):
            session.record(copy.deepcopy(self.ledger), 'probe-1', self.crawl())
        with self.assertRaisesRegex(session.SessionError, 'no crawl run to record'):
            ledger = copy.deepcopy(self.ledger)
            self.action('analyse-1', ledger).update(state='planned', authorisation='', consumption={},
                                                    consumption_source='unknown', started_at='', finished_at='')
            session.record(ledger, 'analyse-1', self.crawl())

    def test_enforced_caps_are_read_from_the_settings_the_crawl_ran_under(self):
        manifest = {'settings': {'CLOSESPIDER_TIMEOUT': 600, 'CLOSESPIDER_ITEMCOUNT': 0,
                                 'CLOSESPIDER_PAGECOUNT': True}}
        self.assertEqual(session.enforced_caps(manifest), {'seconds': 600})
        self.assertEqual(session.consumption_from_manifest({'counts': {'pages_saved': 3}},
                                                           ['pages_retained', 'runs', 'requests']),
                         {'pages_retained': 3, 'runs': 1, 'requests': None})


class Reconciliation(SessionCase):
    def test_a_replay_is_not_new_acquisition(self):
        ledger = copy.deepcopy(self.ledger)
        replay = copy.deepcopy(self.action('analyse-1'))
        replay.update(id='analyse-2', replay_of='analyse-1', consumption={'seconds': 4})
        ledger['actions'].append(replay)
        session.check(ledger)
        self.assertEqual(self.limit('research-responses', ledger)['consumed'], 245)
        replay.update(limit_ids=['research-seconds', 'research-responses'],
                      allocation={'seconds': 60, 'responses': 10}, consumption={'seconds': 4, 'responses': 10})
        with self.assertRaisesRegex(session.SessionError, 'may not allocate acquisition units'):
            session.check(ledger)
        probe = copy.deepcopy(self.action('probe-1'))
        probe.update(id='probe-2', replay_of='probe-1')
        ledger = copy.deepcopy(self.ledger)
        ledger['actions'].append(probe)
        with self.assertRaisesRegex(session.SessionError, 'not acquisition'):
            session.check(ledger)

    def test_a_resumed_action_counts_its_predecessor_once_and_itself_separately(self):
        row = self.limit('research-responses')
        self.assertEqual((row['consumed'], row['reserved'], row['remaining']), (245, 0, 55))
        decision = session.authorise(self.ledger, 'collect-2', AT)
        self.assertFalse(decision['authorised'])
        self.assertIn('100 responses asked, 55 remaining of 300 (245 consumed, 0 reserved)', decision['reasons'][0])
        self.assertIn('completed evidence stands', decision['reasons'][0])
        ledger = copy.deepcopy(self.ledger)
        self.action('collect-2', ledger)['allocation'] = {'responses': 50, 'seconds': 300}
        self.assertTrue(session.authorise(ledger, 'collect-2', AT)['authorised'])
        self.action('collect-2', ledger).update(state='authorised', authorisation='checked')
        row = self.limit('research-responses', ledger)
        self.assertEqual((row['consumed'], row['reserved'], row['remaining']), (245, 50, 5))
        # The resumption may not point at completed work, and never at itself.
        ledger = copy.deepcopy(self.ledger)
        self.action('collect-2', ledger)['resumes'] = 'probe-1'
        with self.assertRaisesRegex(session.SessionError, 'continues an interrupted action of the same kind'):
            session.check(ledger)

    def test_exhaustion_stops_new_work_keeps_evidence_and_names_what_it_prevents(self):
        result = session.reconcile(self.ledger, AT)
        self.assertTrue(result['reconciled'])
        self.assertEqual([d['action'] for d in result['prevented']], ['collect-2'])
        self.assertEqual(result['permitted'], [])
        self.assertEqual(result['interrupted'], ['collect-1'])
        self.assertEqual([a['id'] for a in result['actions'] if a['state'] == 'completed'],
                         ['inspect-1', 'probe-1', 'analyse-1'])
        self.assertEqual(session.load(LEDGER), self.ledger, 'reconciliation writes nothing')

    def test_a_dependency_on_interrupted_work_refuses(self):
        ledger = copy.deepcopy(self.ledger)
        self.action('collect-2', ledger).update(depends_on=['collect-1'], allocation={'responses': 10, 'seconds': 10})
        decision = session.authorise(ledger, 'collect-2', AT)
        self.assertFalse(decision['authorised'])
        self.assertIn('depends on collect-1, which is interrupted', decision['reasons'][0])
        self.assertIn('never assumed complete', decision['reasons'][0])

    def test_a_deadline_counts_time_elapsed_during_the_interruption(self):
        ledger = copy.deepcopy(self.ledger)
        ledger['limits'][1]['deadline'] = '2026-09-16T12:00:00+00:00'
        self.action('collect-2', ledger)['allocation'] = {'responses': 10, 'seconds': 10}
        self.assertTrue(session.authorise(ledger, 'collect-2', '2026-09-16T11:00:00+00:00')['authorised'])
        decision = session.authorise(ledger, 'collect-2', AT)
        self.assertFalse(decision['authorised'])
        self.assertIn('deadline 2026-09-16T12:00:00+00:00 has passed', decision['reasons'][0])
        self.assertIn('explicit budget revision', decision['reasons'][0])
        self.assertTrue(self.limit('research-seconds', ledger)['deadline_passed'])

    def test_an_allocation_needs_a_declared_limit_in_its_unit(self):
        ledger = copy.deepcopy(self.ledger)
        self.action('collect-2', ledger)['allocation']['items'] = 20
        with self.assertRaisesRegex(session.SessionError, 'names no declared limit in that unit'):
            session.check(ledger)

    def test_only_a_planned_action_is_authorised(self):
        decision = session.authorise(self.ledger, 'probe-1', AT)
        self.assertFalse(decision['authorised'])
        self.assertIn('already completed', decision['reasons'][0])


class ProbePromotion(SessionCase):
    """Case 15: explicit promotion, and the selection-bias record beside it."""

    def test_promotion_is_explicit_and_a_material_change_needs_an_assessment(self):
        ledger = copy.deepcopy(self.ledger)
        probe = self.action('probe-1', ledger)
        probe['promotion'].update(promoted=True, into='none')
        with self.assertRaisesRegex(session.SessionError, 'explicitly'):
            session.check(ledger)
        probe['promotion'].update(promoted=True, into='plan_inputs', assessment='')
        with self.assertRaisesRegex(session.SessionError, 'promotion.assessment'):
            session.check(ledger)
        probe['promotion'].update(changed_criteria=True, supplied_candidates=True,
                                  assessment='Seeing the probe pages narrowed the claim filter and supplied two '
                                             'candidates; broader discovery is needed before the comparison is unbiased.')
        session.check(ledger)
        self.assertEqual(self.limit('research-responses', ledger)['consumed'], 245,
                         'promotion moves evidence into the plan, not consumption into the ledger')

    def test_the_fixture_probe_was_not_promoted_and_says_so(self):
        probe = self.action('probe-1')
        self.assertEqual(probe['promotion']['into'], 'none')
        self.assertFalse(probe['promotion']['promoted'])
        self.assertIn('not promoted', probe['promotion']['assessment'])
        self.assertIn('next_action', probe['result'])


class Resumption(SessionCase):
    """Case 18: from verified artifacts alone, without the conversation."""

    def test_the_fixture_study_resumes_from_its_own_snapshot(self):
        directory, manifest = self.study()
        self.assertEqual(manifest['study_id'], 'pasta-delivered-cost-608160f72d15',
                         'a session snapshot moves no identity')
        self.assertEqual(manifest['session']['id'], 'pasta-delivered-session')
        self.assertIn(session.SNAPSHOT, manifest['artifacts'])
        self.assertEqual(bundle.verify(directory)[1], [])
        report = session.resume(directory, None, AT)
        self.assertTrue(report['resumable'], report['findings'])
        self.assertEqual(report['plan']['match'], True)
        self.assertEqual(report['interrupted'], ['collect-1'])
        self.assertTrue(report['resources']['reconciled'])
        self.assertEqual([(s['action'], s['status']) for s in report['next_actions']],
                         [('collect-2', 'prevented'), ('engineer-1', 'proposal')])
        self.assertEqual(report['review'], 'pending')
        self.assertEqual(report['delivery']['recheck']['current_advice'], delivery.NOT_IN_SCOPE)
        self.assertIsNone(report['delivery']['latest'])
        self.assertIn('not a delivery', report['delivery']['recheck']['note'])
        self.assertFalse((directory / delivery.RECORD).exists(), 'resumption writes nothing')

    def test_resumption_needs_neither_the_working_ledger_nor_the_plan_file(self):
        working = self.write('working-ledger.json', self.ledger)
        plan = self.write('working-plan.json', intake.load(PLAN))
        directory, _ = self.study(ledger=working, plan=plan)
        working.unlink(), plan.unlink()
        report = session.resume(directory, None, AT)
        self.assertTrue(report['resumable'], report['findings'])
        status, text = self.cli('resume', directory, '--reference', AT)
        self.assertEqual(status, 0, text)   # verified state; a prevented next action is a fact, not a failure
        self.assertIn('[resumable]', text)
        self.assertIn('interrupted   collect-1: never assumed complete', text)
        self.assertIn('prevented     collect-2', text)
        self.assertIn('proposal      engineer-1', text)
        self.assertIn('recheck       not_in_scope', text)

    def test_unverified_artifacts_are_not_resumed(self):
        directory, _ = self.study()
        (directory / bundle.CANDIDATES).write_text('tampered\n')
        report = session.resume(directory, None, AT)
        self.assertFalse(report['resumable'])
        self.assertEqual(report['findings'][0]['code'], 'artifacts_not_verified')
        self.assertIn('artifact_altered', report['findings'][0]['message'])
        self.assertIsNone(report['delivery']['recheck'], 'no freshness recheck on unverified bytes')

    def test_a_missing_or_altered_run_manifest_is_named_precisely(self):
        ledger = copy.deepcopy(self.ledger)
        run_dir = self.crawl()
        probe = self.action('probe-1', ledger)
        probe['run_manifest'] = {'path': str(run_dir / 'manifest.json'),
                                 'sha256': session.sha256_file(run_dir / 'manifest.json')}
        directory, _ = self.study(ledger=ledger)
        self.assertTrue(session.resume(directory, None, AT)['resumable'])
        (run_dir / 'manifest.json').write_text('{}')
        report = session.resume(directory, None, AT)
        self.assertEqual([f['code'] for f in report['findings']], ['run_manifest_altered'])
        (run_dir / 'manifest.json').unlink()
        report = session.resume(directory, None, AT)
        self.assertEqual([f['code'] for f in report['findings']], ['run_manifest_missing'])
        self.assertIn(str(run_dir / 'manifest.json'), report['findings'][0]['message'])

    def test_a_ledger_for_another_plan_revision_is_refused_and_reported(self):
        ledger = copy.deepcopy(self.ledger)
        ledger['plan']['revision'] = 2
        with self.assertRaisesRegex(bundle.BundleError, 'revision 2'):
            self.study(ledger=ledger)
        directory, _ = self.study()
        report = session.resume(directory, ledger, AT)
        self.assertFalse(report['resumable'])
        self.assertEqual(report['findings'][0]['code'], 'plan_revision_mismatch')
        self.assertEqual(report['plan']['match'], False)

    def test_without_any_ledger_nothing_new_is_authorised(self):
        directory, _ = bundle.run(str(BRONZE), directory=str(self.directory / 'legacy'))
        report = session.resume(directory, None, AT)
        self.assertFalse(report['resumable'])
        self.assertEqual([f['code'] for f in report['findings']], ['session_missing'])
        self.assertEqual(report['next_actions'], [])
        self.assertEqual(report['delivery']['recheck']['current_advice'], delivery.NOT_IN_SCOPE)

    def test_unreconciled_consumption_blocks_resumption_of_acquisition(self):
        ledger = copy.deepcopy(self.ledger)
        self.action('collect-1', ledger).update(consumption={'responses': None, 'seconds': None},
                                                consumption_source='unknown')
        directory, _ = self.study(ledger=ledger)
        report = session.resume(directory, None, AT)
        self.assertFalse(report['resumable'])
        self.assertEqual([f['code'] for f in report['findings']], ['unreconciled_consumption'])
        self.assertIn('unknown stays unknown, not zero', report['findings'][0]['message'])

    def test_freshness_is_rechecked_at_the_resumption_reference(self):
        source = STUDIES / '.tmp-session-current.toml'
        source.write_text(BRONZE.read_text(encoding='utf-8').replace(
            'price_max_age_days = 7', 'price_max_age_days = 7\nscope = "current_advice"'), encoding='utf-8')
        self.addCleanup(source.unlink)
        directory, _ = bundle.run(str(source), directory=str(self.directory / 'current'))
        self.cli('deliver', directory, '--reference', '2026-09-16T12:00:00+00:00')
        report = session.resume(directory, None, LATER)
        self.assertEqual(report['delivery']['latest']['current_advice'], delivery.PERMITTED)
        self.assertEqual(report['delivery']['recheck']['current_advice'], delivery.BLOCKED)
        self.assertIn('No current purchasing recommendation', report['delivery']['recheck']['statement'])
        record = delivery.read(directory / delivery.RECORD)
        self.assertEqual(len(record['events']), 1, 'a recheck records no event')

    def test_a_tampered_snapshot_fails_verify(self):
        directory, _ = self.study()
        snapshot = json.loads((directory / session.SNAPSHOT).read_text())
        snapshot['limits'][0]['amount'] = 10_000
        (directory / session.SNAPSHOT).write_text(json.dumps(snapshot))
        manifest = json.loads((directory / bundle.MANIFEST).read_text())
        manifest['artifacts'] = bundle.artifact_digests(directory)
        (directory / bundle.MANIFEST).write_text(json.dumps(manifest))
        findings = bundle.verify(directory)[1]
        self.assertEqual([f['code'] for f in findings], ['session_invalid'])
        self.assertIn('different session ledger digest', findings[0]['message'])

    def test_a_ledger_naming_a_plan_needs_the_plan(self):
        with self.assertRaisesRegex(bundle.BundleError, 'run this study with --plan'):
            bundle.run(str(BRONZE), directory=str(self.directory / 'x'), session_ledger=str(LEDGER))


class CommandLine(SessionCase):
    def test_session_check_reports_and_exits_on_reconciliation(self):
        status, text = self.cli('session-check', LEDGER, '--reference', AT)
        self.assertEqual(status, 0, text)
        self.assertIn('reconciled at', text)
        self.assertIn('research-responses  research    responses      55 remaining of 300 (245 consumed, 0 reserved)', text)
        self.assertIn('strict_ceiling: a timeout closure may leave requests in flight', text)
        self.assertIn('prevented     collect-2', text)
        self.assertIn('proposal      engineer-1', text)
        self.assertIn('nothing here ran or will run anything', text)
        ledger = copy.deepcopy(self.ledger)
        self.action('collect-1', ledger).update(consumption={'responses': None, 'seconds': 900},
                                                consumption_source='declared')
        status, text = self.cli('session-check', self.write('l.json', ledger), '--reference', AT)
        self.assertEqual(status, 1)
        self.assertIn('NOT reconciled', text)
        self.assertIn('unreconciled: collect-1', text)

    def test_session_authorise_records_only_a_fit_and_never_runs(self):
        path = self.write('ledger.json', self.ledger)
        status, text = self.cli('session-authorise', path, 'collect-2', '--reference', AT, '--record')
        self.assertEqual(status, 1)
        self.assertIn('REFUSED', text)
        self.assertEqual(session.load(path), self.ledger, 'a refusal writes nothing')
        ledger = copy.deepcopy(self.ledger)
        self.action('collect-2', ledger)['allocation'] = {'responses': 50, 'seconds': 300}
        path = self.write('ledger.json', ledger)
        status, text = self.cli('session-authorise', path, 'collect-2', '--reference', AT, '--record')
        self.assertEqual(status, 0, text)
        self.assertIn('it has not run', text)
        recorded = session.load(path)
        self.assertEqual((self.action('collect-2', recorded)['state'], self.action('collect-2', recorded)['authorisation']),
                         ('authorised', 'checked'))

    def test_session_record_reads_the_run_manifest(self):
        ledger = copy.deepcopy(self.ledger)
        self.action('collect-2', ledger)['allocation'] = {'responses': 50, 'seconds': 300}
        self.action('collect-2', ledger).update(state='authorised', authorisation='checked')
        path = self.write('ledger.json', ledger)
        run_dir = self.crawl(close=False)
        status, text = self.cli('session-record', path, 'collect-2', '--run', run_dir)
        self.assertEqual(status, 0, text)
        self.assertIn('collect-2: interrupted; consumption from run_manifest', text)
        self.assertIn('responses      unknown', text)
        recorded = self.action('collect-2', session.load(path))
        self.assertEqual(recorded['authorisation'], 'checked')
        self.assertEqual(recorded['run_manifest']['path'], str(run_dir / 'manifest.json'))
        status, text = self.cli('session-check', path, '--reference', AT)
        self.assertEqual(status, 1)
        status, text = self.cli('session-record', path, 'collect-2', '--state', 'interrupted', '--assume-allocation')
        self.assertEqual(status, 2, 'a finished action is not recorded twice')

    def test_run_snapshots_the_ledger_and_resume_reads_it_back(self):
        output = self.directory / 'cli-bundle'
        status, text = self.cli('run', BRIEF, '--plan', PLAN, '--session', LEDGER, '-o', output)
        self.assertEqual(status, 0, text)
        self.assertEqual(session.load(output / session.SNAPSHOT), self.ledger)
        status, text = self.cli('verify', output)
        self.assertEqual(status, 0, text)
        status, text = self.cli('resume', output, '--session', LEDGER, '--reference', AT)
        self.assertIn('[resumable]', text)
        self.assertIn('plan          pasta-delivered-intake revision 1 (the ledger agrees)', text)


class Gate(unittest.TestCase):
    def test_the_resumption_example_is_replayed_through_the_documented_commands(self):
        example = next(e for e in maintenance.load_baseline()['examples'] if e.get('session'))
        self.assertEqual(example['name'], 'pasta-delivered-cost')
        self.assertEqual(example['expect']['resumable'], 'yes')
        result = maintenance.check_examples({'examples': [example]})
        self.assertTrue(result.passed, result.findings)
        moved = dict(example, expect=dict(example['expect'], resumable='no'))
        result = maintenance.check_examples({'examples': [moved]})
        self.assertEqual([f.code for f in result.findings], ['example_decision_changed'])
        self.assertIn('resumable', result.findings[0].message)


if __name__ == '__main__':
    unittest.main()
