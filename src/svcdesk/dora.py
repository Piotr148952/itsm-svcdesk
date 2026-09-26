# ai-generated: 100% - Codex implemented METRIC-SPEC rules after prediction receipt 153.
"""Pure DORA calculation with explicit validation and decimal rounding."""
from decimal import Decimal, ROUND_HALF_UP
from itertools import combinations
from .clock import parse_instant, stamp


def require(condition, message):
    if not condition:
        raise ValueError(message)


def text(value):
    return isinstance(value, str) and bool(value)


def seconds(delta):
    return Decimal(delta.days * 86400 + delta.seconds) + Decimal(delta.microseconds) / 1000000


def rounded(value, places=0):
    result = value.quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)
    return int(result) if places == 0 else float(result)


def median(values):
    if not values:
        return None
    values = sorted(values)
    n = len(values)
    return rounded(values[n // 2] if n % 2 else (values[n // 2 - 1] + values[n // 2]) / 2)


def calculate(body):
    require(isinstance(body, dict), 'Body must be an object')
    window = body.get('window')
    require(isinstance(window, dict), 'window must be an object')
    require(isinstance(window.get('from'), str) and isinstance(window.get('to'), str), 'Window needs RFC3339 instants')
    start, end = parse_instant(window['from']), parse_instant(window['to'])
    require(end > start, 'Window must have positive duration')
    require(isinstance(body.get('events'), list), 'events must be an array')
    events, seen = [], set()
    for raw in body['events']:
        require(isinstance(raw, dict), 'Every event must be an object')
        eid = raw.get('event_id')
        require(text(eid) and len(eid) <= 64, 'event_id must have 1..64 characters')
        if eid in seen:
            continue
        seen.add(eid)
        require(raw.get('type') in ('commit', 'deployment', 'incident'), 'Unknown event type')
        require(isinstance(raw.get('at'), str), 'at must be an instant')
        events.append({**raw, '_at': parse_instant(raw['at'])})
    commits, deployments, incidents = {}, {}, {}
    for event in events:
        kind = event['type']
        if kind == 'commit':
            require(text(event.get('sha')) and event['sha'] not in commits, 'Duplicate or invalid sha')
            require(isinstance(event.get('branch'), str), 'branch must be text')
            require('reverts' in event and 'change_id' in event, 'Missing commit identity')
            require(event['reverts'] is None or text(event['reverts']), 'Invalid reverts')
            require(text(event['change_id']) if event['reverts'] is None else event['change_id'] is None, 'Invalid change identity')
            commits[event['sha']] = event
        elif kind == 'deployment':
            require(text(event.get('deployment_id')) and event['deployment_id'] not in deployments, 'Duplicate or invalid deployment_id')
            require(isinstance(event.get('environment'), str), 'Invalid environment')
            require(event.get('outcome') in ('success', 'failure'), 'Invalid outcome')
            require(isinstance(event.get('commits'), list) and all(text(s) for s in event['commits']), 'Invalid commits')
            require(type(event.get('unplanned')) is bool, 'unplanned must be boolean')
            require('caused_by' in event and (event['caused_by'] is None or text(event['caused_by'])), 'Invalid caused_by')
            deployments[event['deployment_id']] = event
        else:
            require(text(event.get('incident_id')), 'Invalid incident_id')
            require(event.get('phase') in ('opened', 'resolved'), 'Invalid incident phase')
            require(isinstance(event.get('deployments'), list) and all(text(s) for s in event['deployments']), 'Invalid incident deployments')
            phases = incidents.setdefault(event['incident_id'], {})
            require(event['phase'] not in phases, 'Duplicate incident phase')
            phases[event['phase']] = event
    for event in commits.values():
        require(event['reverts'] is None or event['reverts'] in commits, 'Unknown reverted sha')
    for event in deployments.values():
        require(all(s in commits for s in event['commits']), 'Unknown deployment sha')
        require(event['caused_by'] is None or event['caused_by'] in incidents, 'Unknown caused_by incident')
    for phases in incidents.values():
        require('opened' in phases, 'Incident resolution without opening')
        for event in phases.values():
            require(all(d in deployments for d in event['deployments']), 'Unknown incident deployment')
    identities = {}
    for sha in commits:
        path, visiting, current = [], set(), sha
        while current not in identities:
            require(current not in visiting, 'Cyclic revert chain')
            visiting.add(current)
            path.append(current)
            event = commits[current]
            if event['reverts'] is None:
                identities[current] = event['change_id']
                break
            current = event['reverts']
        for item in path:
            identities[item] = identities[current]
    earliest = {}
    for sha, event in commits.items():
        identity = identities[sha]
        earliest[identity] = min(earliest.get(identity, event['_at']), event['_at'])
    scoped = sorted((d for d in deployments.values() if d['environment'] == 'production' and start <= d['_at'] < end), key=lambda d: (d['_at'], d['deployment_id']))
    successful = [d for d in scoped if d['outcome'] == 'success']
    failed = [d for d in scoped if d['outcome'] == 'failure']
    pairs, delivered, seen_shas, negative = [], {}, set(), 0
    for deployment in successful:
        for sha in deployment['commits']:
            identity = identities[sha]
            delivered.setdefault(identity, deployment['_at'])
            if sha in seen_shas:
                continue
            seen_shas.add(sha)
            duration = seconds(deployment['_at'] - commits[sha]['_at'])
            negative += int(duration < 0)
            pairs.append(max(Decimal(0), duration))
    recovery, open_failures = [], 0
    for deployment in failed:
        covering = [(phases['opened']['_at'], iid.encode('utf-8'), phases) for iid, phases in incidents.items()
                    if deployment['deployment_id'] in phases['opened']['deployments']]
        chosen = min(covering, key=lambda item: (item[0], item[1]))[2] if covering else None
        if chosen is None or 'resolved' not in chosen:
            open_failures += 1
        else:
            recovery.append(max(Decimal(0), seconds(chosen['resolved']['_at'] - deployment['_at'])))
    intervals = [(phases['opened']['_at'], phases['resolved']['_at'] if 'resolved' in phases else end) for phases in incidents.values()]
    overlaps = sum(a[0] < b[1] and b[0] < a[1] for a,b in combinations(intervals, 2))
    total = len(scoped)
    rework = sum(d['unplanned'] and d['caused_by'] is not None for d in scoped)
    def ratio(n):
        return rounded(Decimal(n) / total, 6) if total else None
    return {
        'spec_version': '1.0.0', 'window': {'from': stamp(start), 'to': stamp(end)},
        'deployment_frequency_per_day': rounded(Decimal(total) * 86400 / seconds(end-start), 6),
        'change_lead_time_seconds_p50': median(pairs),
        'failed_deployment_recovery_time_seconds_p50': median(recovery),
        'change_fail_rate': ratio(len(failed)), 'deployment_rework_rate': ratio(rework),
        'counts': {'deployments': total, 'successful_deployments': len(successful), 'failed_deployments': len(failed),
                   'recovered_failures': len(recovery), 'open_failures': open_failures, 'rework_deployments': rework,
                   'lead_time_pairs': len(pairs), 'changes': len(earliest)},
        'anomalies': {'negative_lead_time_pairs': negative, 'deployments_without_commits': sum(not d['commits'] for d in scoped),
                      'commits_never_on_main': len({s for d in scoped for s in d['commits'] if commits[s]['branch'] != 'main'}),
                      'revert_chains_collapsed': sum(c['reverts'] is not None for c in commits.values()),
                      'overlapping_incident_pairs': overlaps},
        'ground_truth': {'changes_delivered': len(delivered),
                         'true_change_lead_time_seconds_p50': median([max(Decimal(0), seconds(at-earliest[c])) for c,at in delivered.items()])}
}
