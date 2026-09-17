"""Inspection and resolution of existing candidate controls, not an executor.

Category-specific choices come from the live registry on every call. Generic
mechanisms describe the existing implementation; they neither add predicates
nor attest that a control represents a buyer's intent. Units are measured from
cards at ranking time, not inferred from axis labels. No catalogue enters study
identity or report bytes. Intake-plan persistence is a later stage.
"""

import math

from ..analysis.category import get


class ControlError(ValueError):
    """No executable mapping exists for the supplied category/control."""


def catalogue(category_key):
    """Return JSON-ready metadata for all five candidate-set mechanisms."""
    try:
        category = get(category_key)
    except KeyError as exc:
        raise ControlError(str(exc)) from exc
    axes = [dict(key=a.key, label=a.label, better=a.better,
                 rankable=bool(a.better), why=a.why, caveat=a.caveat)
            for a in category.axes]
    claims = [dict(key=c.key, label=c.label, adverse=c.adverse, why=c.why)
              for c in category.claims]
    return {
        'category': category.key, 'label': category.label,
        'default_axis': category.default_axis, 'axes': axes, 'claims': claims,
        'controls': {
            'require_claims': {
                'parameters': {'claims': 'list of category claim keys'},
                'stage': 'candidate_filter', 'optional': True,
                'implementation': 'shopping_advisor.analysis.report.ranking',
                'effect': 'Every named claim must have trusted status on the category card, before grouping.',
                'limits': 'Requires a vendor statement, not external proof or absence of an adverse claim. Adverse keys still require presence.'},
            'max_axis_value': {
                'parameters': {'axis': 'rankable category axis; omitted uses category default',
                               'unit': 'optional exact measured unit; no conversion',
                               'value': 'finite nonnegative inclusive upper bound'},
                'stage': 'ranked_row_filter', 'optional': True,
                'implementation': 'shopping_advisor.study.analysis.analyse',
                'effect': 'Excludes grouped ranking rows whose selected-axis value exceeds the bound, irrespective of better direction.',
                'limits': 'Same axis and unit as ordering; not an independent purchase budget. Folded variants are not reselected after the cap.'},
            'classification': {
                'parameters': {}, 'stage': 'candidate_filter', 'optional': False,
                'implementation': 'shopping_advisor.analysis.category.is_match',
                'effect': 'Only cards whose classification value equals the category key enter ranking.',
                'limits': 'The existing classifier decides category membership; this is not an arbitrary buyer exclusion or a classifier-accuracy guarantee.'},
            'value_usability': {
                'parameters': {'axis': 'rankable category axis; omitted uses category default',
                               'unit': 'optional exact measured unit; no conversion'},
                'stage': 'ranking', 'optional': False,
                'implementation': 'shopping_advisor.analysis.report.ranking.ranked_value',
                'effect': 'Requires a present usable selected-axis value in the ranking unit. A directionless axis or mixed units without a selected unit refuses ranking.',
                'limits': 'Unit availability is checked against evidence at execution; resolving a unit string does not establish availability.'},
            'offer_grouping': {
                'parameters': {}, 'stage': 'ranking', 'optional': False,
                'implementation': 'shopping_advisor.validation.variation.group_offers',
                'effect': 'Folds size variants using pooled marketplace-scoped family matrices and non-size dimensions; the best usable selected-axis member represents each row.',
                'limits': 'Unknown family identity stays separate. Does not enforce a maximum pack size or arbitrary variant restriction.'},
        },
        'not_controls': ['cost_basis', 'unacceptable', 'limits'],
        'limits': ['External evidence claims do not filter candidates.',
                   'This resolves existing mechanisms, not semantic suitability or requirement coverage.'],
    }


def resolve(category_key, control, **parameters):
    """Resolve a closed control name and its parameters, without reading feeds.

    Returned axis/claim descriptors are snapshots of the live category. Reject
    unknown parameters rather than silently treating unsupported intent as applied.
    The caller must use the same axis/unit for cap and ordering; this function does
    not yet validate an intake plan or execute a brief.
    """
    data = catalogue(category_key)
    if control not in data['controls']:
        raise ControlError(f'{control}: unknown control; known: '
                           + ', '.join(data['controls']))
    descriptor = data['controls'][control]
    unknown = set(parameters) - set(descriptor['parameters'])
    if unknown:
        raise ControlError('unsupported parameters: ' + ', '.join(sorted(unknown)))
    resolved = dict(category=category_key, control=control,
                    metadata=descriptor, parameters={})
    if control == 'require_claims':
        keys = parameters.get('claims')
        if not isinstance(keys, (list, tuple)) or any(not isinstance(k, str) for k in keys):
            raise ControlError('claims must be a list of category claim keys')
        claims = {c['key']: c for c in data['claims']}
        for key in keys:
            if key not in claims:
                raise ControlError(f'{key}: unknown claim for {category_key}')
        resolved['parameters']['claims'] = list(keys)
        resolved['claims'] = [claims[key] for key in keys]
    if control in ('max_axis_value', 'value_usability'):
        key = parameters.get('axis', data['default_axis'])
        axis = next((a for a in data['axes'] if a['key'] == key), None)
        if axis is None:
            raise ControlError(f'{key}: unknown axis for {category_key}')
        if not axis['rankable']:
            raise ControlError(f'{key}: no ranking direction for {category_key}')
        unit = parameters.get('unit', '')
        if not isinstance(unit, str):
            raise ControlError('unit must be text; availability is checked at ranking')
        resolved['parameters'].update(axis=key, unit=unit)
        resolved['axis'] = axis
        resolved['axis_source'] = 'explicit' if 'axis' in parameters else 'category_default'
    if control == 'max_axis_value':
        value = parameters.get('value')
        if type(value) not in (int, float) or value < 0 or not math.isfinite(value):
            raise ControlError('value must be a finite nonnegative number')
        resolved['parameters']['value'] = value
    return resolved
