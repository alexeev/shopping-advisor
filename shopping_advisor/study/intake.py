"""R13 plan v1 and the preservation boundary into an executable brief.

This is a data contract, not a language interpreter, source verifier or grant of
authority. It checks retained structure and live control mappings. It cannot
detect an instruction omitted from both capture and interpretation, or prove
that an executable mapping is semantically adequate. Settled decisive
requirements without an executable control cross this bridge into *bounded*
execution: :mod:`shopping_advisor.study.gates` withholds the full-request
recommendation and keeps the ranking on the available axis as a bounded finding.
"""
import copy
import json
from pathlib import Path
import re

from ..analysis.category import get
from ..provenance import sha256_text
from . import controls

PLAN_VERSION = 1
DEFAULT_PLAN_ROOT = 'data/plans'
SNAPSHOT = 'intake-plan.json'
STAGES = ('intake', 'probe', 'discovery', 'collection', 'candidate_assessment',
          'comparison', 'conclusion', 'delivery', 'revision')


class PlanError(ValueError):
    """An invalid plan or a lossy transition; never a marketplace finding."""


def _fail(where, message):
    raise PlanError(f'{where}: {message}')


def _object(value, keys, where):
    if not isinstance(value, dict) or set(value) != set(keys.split()):
        _fail(where, f'expected exactly these fields: {keys}')


def _text(value, where, empty=False):
    if not isinstance(value, str) or (not empty and not value.strip()):
        _fail(where, 'expected nonempty text' if not empty else 'expected text')


def _enum(value, choices, where):
    if not isinstance(value, str) or value not in choices.split():
        _fail(where, f'expected one of: {choices}')


def _rows(value, where):
    if not isinstance(value, list):
        _fail(where, 'expected a list')
    return value


def _refs(value, available, where, required=False):
    _rows(value, where)
    if any(not isinstance(v, str) for v in value):
        _fail(where, 'references must be strings')
    if len(set(value)) != len(value) or set(value) - set(available):
        _fail(where, 'duplicate or unresolved references')
    if required and not value:
        _fail(where, 'at least one retained reference is required')


def _ids(rows, where):
    _rows(rows, where)
    found = {}
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get('id'), str) or \
                not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,63}', row['id']):
            _fail(where, 'every entry needs a slug id')
        if row['id'] in found:
            _fail(where, 'duplicate id ' + row['id'])
        found[row['id']] = row
    return found


def digest(data):
    """Canonical JSON content digest, independent of path and whitespace."""
    try:
        return sha256_text(json.dumps(data, ensure_ascii=False, sort_keys=True,
                                      separators=(',', ':'), allow_nan=False))
    except (TypeError, ValueError) as exc:
        raise PlanError(f'plan must be finite JSON data: {exc}') from exc


def _sha(value, where, empty=False):
    if empty and value == '':
        return
    if not isinstance(value, str) or not re.fullmatch('[a-f0-9]{64}', value):
        _fail(where, 'expected a SHA-256 digest')


def check(data):
    """Validate a plan without requiring a registered category or any feeds."""
    _object(data, 'plan_version id revision supersedes question use_case category '
            'marketplace delivery_region user_evidence sources requirements questions readback', 'plan')
    if type(data['plan_version']) is not int or data['plan_version'] != PLAN_VERSION:
        _fail('plan_version', f'unsupported version; expected {PLAN_VERSION}')
    _ids([{'id': data['id']}], 'plan')
    if type(data['revision']) is not int or data['revision'] < 1:
        _fail('revision', 'expected a positive integer')
    _sha(data['supersedes'], 'supersedes', empty=data['revision'] == 1)
    if data['revision'] == 1 and data['supersedes']:
        _fail('supersedes', 'first revision cannot supersede a revision')
    for key in ('question', 'use_case', 'category', 'marketplace', 'delivery_region'):
        _text(data[key], key, empty=key in ('marketplace', 'delivery_region'))
    if not re.fullmatch(r'[a-z][a-z0-9_]*', data['category']):
        _fail('category', 'use a category key, never an import path')

    evidence = data['user_evidence']
    _object(evidence, 'conversation start selection missing_context messages', 'user_evidence')
    for key in ('conversation', 'start'):
        _text(evidence[key], f'user_evidence.{key}')
    _text(evidence['missing_context'], 'missing_context', empty=True)
    if evidence['selection'] != 'all_user_messages':
        _fail('user_evidence.selection', 'capture by provenance: all user messages in the stated exchange')
    messages = _ids(evidence['messages'], 'messages')
    if not messages:
        _fail('messages', 'retain the user exchange, not just selected requirement excerpts')
    for message in messages.values():
        _object(message, 'id author text redactions', message['id'])
        if message['author'] != 'user':
            _fail(message['id'], 'tool and source content is not user-authored evidence')
        _text(message['text'], message['id'], empty=True)
        for redaction in _rows(message['redactions'], 'redactions'):
            _object(redaction, 'description reason limits_review', 'redaction')
            _text(redaction['description'], 'redaction.description')
            _text(redaction['reason'], 'redaction.reason')
            if type(redaction['limits_review']) is not bool:
                _fail('redaction.limits_review', 'expected boolean')
        if not message['text'] and not message['redactions']:
            _fail(message['id'], 'empty message needs an explicit redaction record')
    sources = _ids(data['sources'], 'sources')
    if set(sources) & set(messages):
        _fail('sources', 'source and user message ids must be distinct')
    for source in sources.values():
        _object(source, 'id locator text', source['id'])
        _text(source['locator'], 'source.locator')
        _text(source['text'], 'source.text')

    requirements = _ids(data['requirements'], 'requirements')
    if not requirements:
        _fail('requirements', 'record at least the request or its unresolved context')
    for req in requirements.values():
        _requirement(req, data, messages, sources, requirements)
    priorities = {}
    for req in requirements.values():
        if req['assessment']['path'] in ('withdrawn', 'revised'):
            continue
        if req['priority'] is not None:
            priorities.setdefault(req['priority'], []).append(req)
    for tied in priorities.values():
        if len(tied) > 1 and any(not req['tradeoff'].strip() for req in tied):
            _fail('requirements', 'equal preference priorities need a declared tradeoff')
    for req in requirements.values():
        visited = set()
        while req['assessment']['path'] == 'revised':
            if req['id'] in visited:
                _fail(req['id'], 'cyclic requirement replacement')
            visited.add(req['id'])
            req = requirements[req['assessment']['change']['replacement']]
    for question in _ids(data['questions'], 'questions').values():
        _object(question, 'id text uncertainty expected_effect requirement_ids answer_message_ids', question['id'])
        for key in ('text', 'uncertainty', 'expected_effect'):
            _text(question[key], f'{question["id"]}.{key}')
        _refs(question['requirement_ids'], requirements, 'question.requirement_ids', required=True)
        _refs(question['answer_message_ids'], messages, 'question.answer_message_ids')

    back = data['readback']
    _object(back, 'revision text response', 'readback')
    if type(back['revision']) is not int or back['revision'] != data['revision']:
        _fail('readback.revision', 'must name this plan revision')
    response = back['response']
    _object(response, 'status message_ids scope', 'readback.response')
    _enum(response['status'], 'not_presented no_response confirmed delegated corrected', 'readback.response.status')
    _text(response['scope'], 'readback.response.scope', empty=True)
    answered = response['status'] in ('confirmed', 'delegated', 'corrected')
    _refs(response['message_ids'], messages, 'readback.response.message_ids', required=answered)
    if not answered and response['message_ids']:
        _fail('readback.response', 'no response cannot cite a response')
    if answered and not response['scope'].strip():
        _fail('readback.response.scope', 'record what the response covers')
    expected = '' if response['status'] == 'not_presented' else render_readback(data)
    if back['text'] != expected:
        _fail('readback.text', 'does not match the authoritative plan revision')
    digest(data)  # Also refuses non-JSON data and NaN in nested parameters.
    return data


def _requirement(req, plan, messages, sources, requirements):
    name = req['id']
    _object(req, 'id statement role operative decisive settlement provenance assessment effects priority tradeoff', name)
    _text(req['statement'], name + '.statement')
    _enum(req['role'], 'hard_constraint preference objective context', name + '.role')
    _enum(req['settlement'], 'stated delegated assumed unresolved', name + '.settlement')
    for key in ('operative', 'decisive'):
        if type(req[key]) is not bool:
            _fail(name, key + ' must be boolean')
    if req['role'] != 'context' and not req['operative']:
        _fail(name, 'only context may be non-operative; withdraw a requirement explicitly')
    if req['role'] == 'hard_constraint' and not req['decisive']:
        _fail(name, 'hard constraints bind, including assumed ones')
    if req['decisive'] and not req['operative']:
        _fail(name, 'non-operative context cannot be decisive')
    _text(req['tradeoff'], name + '.tradeoff', empty=True)
    if req['role'] in ('preference', 'objective'):
        if type(req['priority']) is not int or req['priority'] < 1:
            _fail(name, 'preferences/objectives need a positive priority')
    elif req['priority'] is not None:
        _fail(name, 'priority belongs to preferences/objectives')

    provenance = req['provenance']
    _object(provenance, 'author wording refs basis applicability rationale if_wrong', name + '.provenance')
    _enum(provenance['author'], 'user cited_source agent', name + '.author')
    _enum(provenance['basis'], 'user_statement source hypothesis reasonableness', name + '.basis')
    for key in ('wording', 'applicability', 'rationale', 'if_wrong'):
        _text(provenance[key], name + '.' + key)
    available = {**messages, **sources}
    _refs(provenance['refs'], available, name + '.refs')
    author = provenance['author']
    if author in ('user', 'cited_source'):
        origin = messages if author == 'user' else sources
        _refs(provenance['refs'], origin, name + '.refs', required=True)
        if not any(provenance['wording'] in origin[ref]['text'] for ref in provenance['refs']):
            _fail(name, 'supporting wording is absent from the retained provenance')
    if req['settlement'] == 'stated' and author != 'user':
        _fail(name, 'stated means stated by the user, not inferred from a source')
    if req['settlement'] == 'delegated':
        if not set(provenance['refs']) & set(messages):
            _fail(name, 'resolved delegation needs retained user authority and rationale')
    effects = _rows(req['effects'], name + '.effects')
    for effect in effects:
        _object(effect, 'stage consequence', name + '.effect')
        if effect['stage'] not in STAGES:
            _fail(name, 'unknown stage effect')
        _text(effect['consequence'], name + '.consequence')
    if bool(effects) != req['operative']:
        _fail(name, 'operative requirements need effects; non-operative context has none')

    assessment = req['assessment']
    _object(assessment, 'path state controls evidence reviews gap change', name + '.assessment')
    _enum(assessment['path'], 'control evidence_review unsupported revised withdrawn not_applicable', name + '.path')
    _enum(assessment['state'], 'not_assessed supported failed unknown', name + '.state')
    for kind in ('evidence', 'reviews'):
        for reference in _rows(assessment[kind], name + '.' + kind):
            _object(reference, 'id sha256', name + '.' + kind)
            _text(reference['id'], name + '.' + kind)
            _sha(reference['sha256'], name + '.' + kind)
    if assessment['state'] in ('supported', 'failed') and not assessment['evidence']:
        _fail(name, 'an assessment outcome needs evidence bindings')
    if assessment['path'] == 'evidence_review' and assessment['state'] in ('supported', 'failed') and not assessment['reviews']:
        _fail(name, 'evidence-and-review outcomes need review bindings')
    mappings = _rows(assessment['controls'], name + '.controls')
    if assessment['path'] == 'control':
        if not mappings:
            _fail(name, 'control path needs resolved controls')
        for mapping in mappings:
            if not isinstance(mapping, dict) or not isinstance(mapping.get('parameters'), dict):
                _fail(name, 'expected a resolved control mapping')
            parameters = dict(mapping['parameters'])
            if mapping.get('axis_source') == 'category_default':
                parameters.pop('axis', None)
            try:
                live = controls.resolve(plan['category'], mapping.get('control'), **parameters)
            except (controls.ControlError, TypeError, OverflowError) as exc:
                _fail(name, str(exc))
            if mapping != live:
                _fail(name, 'resolved control metadata changed; reassess the mapping')
    elif mappings:
        _fail(name, 'only a control path can claim executable controls')
    if assessment['path'] == 'unsupported':
        gap = assessment['gap']
        _object(gap, 'kind reason next_step', name + '.gap')
        for key in gap:
            _text(gap[key], name + '.gap.' + key)
        if assessment['state'] == 'supported':
            _fail(name, 'an unsupported method is not a supported assessment')
    elif assessment['gap'] is not None:
        _fail(name, 'a gap belongs to an unsupported assessment path')
    if assessment['path'] in ('revised', 'withdrawn'):
        change = assessment['change']
        _object(change, 'authority reason replacement', name + '.change')
        _refs(change['authority'], messages, name + '.change.authority', required=True)
        _text(change['reason'], name + '.change.reason')
        if assessment['path'] == 'revised':
            _text(change['replacement'], name + '.change.replacement')
            if change['replacement'] not in requirements or change['replacement'] == name:
                _fail(name, 'a revision needs a distinct retained replacement requirement')
        elif change['replacement'] is not None:
            _fail(name, 'withdrawal has no replacement')
    elif assessment['change'] is not None:
        _fail(name, 'change authority belongs to a revision or withdrawal')
    if assessment['path'] == 'not_applicable' and req['operative']:
        _fail(name, 'only non-operative context needs no assessment path')


def render_readback(plan):
    """Render from the plan, never from a Brief that already lost context.

    The response is deliberately outside these bytes: a response to a read-back
    cannot change the read-back it answered. Validate with check() on ingestion.
    """
    lines = [f'Plan {plan["id"]}, revision {plan["revision"]}',
             plan['question'], 'Use case: ' + plan['use_case'],
             f'Category: {plan["category"]}; marketplace: {plan["marketplace"] or "unresolved"}; '
             f'delivery: {plan["delivery_region"] or "unresolved"}.']
    for req in plan['requirements']:
        provenance, assessment = req['provenance'], req['assessment']
        lines += [f'- {req["id"]}: {req["statement"]}',
                  f'  Role: {req["role"]}; operative: {req["operative"]}; decisive: {req["decisive"]}; '
                  f'settlement: {req["settlement"]}; introduced by: {provenance["author"]}.',
                  f'  Basis ({provenance["basis"]}): {provenance["wording"]}',
                  '  Rationale: ' + provenance['rationale'],
                  '  Applies to: ' + provenance['applicability'],
                  '  If wrong: ' + provenance['if_wrong'],
                  f'  Assessment: {assessment["path"]}; state: {assessment["state"]}.']
        if req['priority'] is not None:
            lines += [f'  Priority: {req["priority"]}; tradeoff: {req["tradeoff"] or "none declared"}.']
        for mapping in assessment['controls']:
            lines += [f'  Control: {mapping["control"]} '
                      + json.dumps(mapping['parameters'], ensure_ascii=False, sort_keys=True),
                      '  Control limits: ' + mapping['metadata']['limits']]
        if assessment['gap']:
            lines += ['  Gap: ' + assessment['gap']['reason'],
                      '  Next step: ' + assessment['gap']['next_step']]
        if assessment['change']:
            lines += ['  Change: ' + assessment['change']['reason']]
        for effect in req['effects']:
            lines += [f'  {effect["stage"]}: {effect["consequence"]}']
    for question in plan['questions']:
        lines += ['Question: ' + question['text'],
                  '  Uncertainty: ' + question['uncertainty'],
                  '  Expected effect: ' + question['expected_effect']]
    if plan['user_evidence']['missing_context']:
        lines += ['Missing context: ' + plan['user_evidence']['missing_context']]
    for message in plan['user_evidence']['messages']:
        for redaction in message['redactions']:
            lines += [f'Redaction in {message["id"]}: {redaction["description"]}; '
                      f'reason: {redaction["reason"]}; limits review: {redaction["limits_review"]}.']
    return '\n'.join(lines) + '\n'


def load(path):
    try:
        return check(json.loads(Path(path).read_text(encoding='utf-8')))
    except (OSError, ValueError) as exc:
        raise PlanError(f'{path}: {exc}') from exc


def binding(plan):
    """The brief's lossless requirement projection and its snapshot binding."""
    check(plan)
    return {'plan_version': PLAN_VERSION, 'plan_id': plan['id'],
            'revision': plan['revision'], 'plan_sha256': digest(plan),
            'requirements': copy.deepcopy(plan['requirements'])}


def check_binding(value):
    """Shape only; exact meanings and controls are checked with the plan."""
    _object(value, 'plan_version plan_id revision plan_sha256 requirements', 'brief.intake')
    if type(value['plan_version']) is not int or value['plan_version'] != PLAN_VERSION:
        _fail('brief.intake', 'unsupported plan version')
    _ids([{'id': value['plan_id']}], 'brief.intake.plan_id')
    if type(value['revision']) is not int or value['revision'] < 1:
        _fail('brief.intake.revision', 'expected a positive integer')
    _sha(value['plan_sha256'], 'brief.intake.plan_sha256')
    _ids(value['requirements'], 'brief.intake.requirements')


def check_transition(plan, brief):
    """Refuse loss before feed reads, candidate decisions or bundle writes."""
    if plan is None:
        if brief.intake is not None:
            _fail('brief.intake', 'bound brief requires its intake plan snapshot')
        return
    check(plan)
    expected = binding(plan)
    if brief.intake is None:
        _fail('brief.intake', 'missing requirement binding; bind the brief explicitly')
    check_binding(brief.intake)
    actual = {r['id']: r for r in brief.intake['requirements']}
    for req in expected['requirements']:
        if digest(actual.get(req['id'])) != digest(req):
            _fail(req['id'], 'requirement dropped or changed in the brief (meaning, role or disposition)')
    if digest(brief.intake) != digest(expected):
        _fail('brief.intake', 'binding belongs to a different plan revision or contains added requirements')
    for field in ('question', 'use_case', 'category', 'marketplace', 'delivery_region'):
        if getattr(brief, field) != plan[field]:
            _fail(field, 'brief differs from the authoritative plan')
    if plan['readback']['response']['status'] == 'corrected':
        _fail('readback', 'correction remains unreconciled; revise the plan before translation')
    applied = []
    for req in plan['requirements']:
        assessment = req['assessment']
        if assessment['path'] in ('withdrawn', 'revised'):
            continue
        if req['decisive'] and req['settlement'] == 'unresolved':
            _fail(req['id'], 'decisive requirement is unresolved')
        # A decisive requirement with no executable control is not refused
        # here: it enters bounded execution, and the conclusion gate withholds
        # the recommendation. Refusing it outright would forbid the bounded
        # item-price finding INTAKE §3 explicitly permits.
        for mapping in assessment['controls']:
            _check_control(req['id'], mapping, brief)
            applied.append(mapping)
    expected_claims = {claim for mapping in applied if mapping['control'] == 'require_claims'
                       for claim in mapping['parameters']['claims']}
    if set(brief.require_claims) != expected_claims:
        _fail('require_claims', 'brief adds a filter with no active requirement/provenance in the plan')
    if brief.max_axis_value is not None and not any(m['control'] == 'max_axis_value' for m in applied):
        _fail('max_axis_value', 'brief adds a cap with no active requirement/provenance in the plan')
    from collections import Counter
    mapped_bounds = Counter(_bound_key(m['parameters']) for m in applied if m['control'] == 'axis_bound')
    if Counter(_bound_key(b) for b in brief.axis_bounds) != mapped_bounds:
        _fail('axis_bounds', 'brief adds or drops a bound with no active requirement/provenance in the plan')
    if (brief.axis or brief.unit) and not any(m['control'] in ('value_usability', 'max_axis_value') for m in applied):
        _fail('axis', 'explicit ordering needs a resolved mapping in the plan')


def _bound_key(bound):
    """One bound as a comparable identity: axis, unit, floor, ceiling."""
    return (bound['axis'], bound.get('unit') or '', bound.get('min'), bound.get('max'))


def _check_control(name, mapping, brief):
    control, parameters = mapping['control'], mapping['parameters']
    if control == 'axis_bound':
        if _bound_key(parameters) not in {_bound_key(b) for b in brief.axis_bounds}:
            _fail(name, 'axis bound did not reach constraints.axis_bounds with the same axis, unit, min and max')
    if control == 'require_claims':
        if not set(parameters['claims']).issubset(brief.require_claims):
            _fail(name, 'required claims did not reach constraints.require_claims')
    if control in ('value_usability', 'max_axis_value'):
        if parameters['axis'] != (brief.axis or get(brief.category).default_axis):
            _fail(name, 'selected axis changed in the brief')
        if parameters['unit'] != brief.unit:
            _fail(name, 'selected unit changed in the brief; no unit substitution')
        if ('explicit' if brief.axis else 'category_default') != mapping['axis_source']:
            _fail(name, 'axis attribution changed between explicit choice and category default')
    if control == 'max_axis_value' and parameters['value'] != brief.max_axis_value:
        _fail(name, 'selected-axis cap changed or disappeared in the brief')
    # Classification and grouping have no optional switches; naming the same
    # category above binds their fixed behavior. No narrative field is a control.
