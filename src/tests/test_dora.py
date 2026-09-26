# ai-generated: 100% - Codex authored independent synthetic metric tests and practice comparison.
from copy import deepcopy
from pathlib import Path
import json
import pytest
from .test_api import call

WINDOW = {'from':'2026-09-01T00:00:00Z', 'to':'2026-09-22T00:00:00Z'}

def score(events, window=WINDOW):
    status, result = call('/dora/metrics','POST',{'window':window,'events':events})
    assert status == 200, result
    return result

def commit(sha='a', at='2026-09-02T00:00:00Z', change='A', reverts=None, branch='main'):
    return dict(event_id='c'+sha,type='commit',at=at,sha=sha,branch=branch,change_id=change,reverts=reverts)

def deploy(did='a', at='2026-09-03T00:00:00Z', shas=None, outcome='success', **extra):
    return dict(event_id='d'+did,type='deployment',at=at,deployment_id=did,environment='production',outcome=outcome,
                commits=['a'] if shas is None else shas,unplanned=False,caused_by=None,**extra)

def incident(iid,phase,at,deps):
    return dict(event_id=iid+phase,type='incident',incident_id=iid,phase=phase,at=at,deployments=deps)

def test_practice_exact():
    root=Path('/app/fixtures')
    events=[json.loads(line) for line in (root/'events-practice.jsonl').read_text().splitlines() if line.strip()]
    expected=json.loads((root/'metrics-practice.json').read_text())
    assert score(events) == expected
    assert score(list(reversed(events))) == expected
    assert score(events+events) == expected

def test_empty_log():
    result=score([])
    assert result['deployment_frequency_per_day'] == 0
    assert result['change_fail_rate'] is None
    assert result['change_lead_time_seconds_p50'] is None
    assert all(n==0 for n in result['counts'].values())

def test_clock_skew_clamped_and_retained():
    result=score([commit(at='2026-09-04T00:00:00Z'),deploy()])
    assert result['anomalies']['negative_lead_time_pairs']==1
    assert result['counts']['lead_time_pairs']==1
    assert result['change_lead_time_seconds_p50']==0

def test_revert_transitive_change_vs_commit():
    result=score([commit(),commit('b','2026-09-02T12:00:00Z',None,'a'),commit('c','2026-09-03T00:00:00Z',None,'b'),deploy(shas=['c'])])
    assert result['counts']['changes']==1
    assert result['anomalies']['revert_chains_collapsed']==2
    assert result['change_lead_time_seconds_p50']==0
    assert result['ground_truth']['true_change_lead_time_seconds_p50']==86400

def test_hotfix_failed_counts_but_not_lead_pair():
    result=score([commit(branch='hotfix'),deploy(outcome='failure')])
    assert result['anomalies']['commits_never_on_main']==1
    assert result['counts']['lead_time_pairs']==0
    assert result['counts']['open_failures']==1

def test_empty_deployment_in_denominators():
    result=score([deploy(shas=[])])
    assert result['counts']['deployments']==1
    assert result['anomalies']['deployments_without_commits']==1
    assert result['change_lead_time_seconds_p50'] is None
    assert result['change_fail_rate']==0

def test_open_covering_incident_wins_even_if_later_one_resolved():
    result=score([commit(),deploy(outcome='failure'),incident('a','opened','2026-09-03T01:00:00Z',['a']),
                  incident('b','opened','2026-09-03T02:00:00Z',['a']),incident('b','resolved','2026-09-03T03:00:00Z',['a'])])
    assert result['counts']['open_failures']==1
    assert result['failed_deployment_recovery_time_seconds_p50'] is None
    assert result['anomalies']['overlapping_incident_pairs']==1

def test_recovery_per_deployment_and_after_window():
    result=score([deploy('a',shas=[],outcome='failure'),deploy('b','2026-09-04T00:00:00Z',[], 'failure'),
        incident('x','opened','2026-09-04T01:00:00Z',['a','b']),incident('x','resolved','2026-09-23T00:00:00Z',['a','b'])])
    assert result['counts']['recovered_failures']==2
    assert result['failed_deployment_recovery_time_seconds_p50']==1684800

def test_half_open_window_and_staging():
    a=deploy('a',WINDOW['from'],[])
    b=deploy('b',WINDOW['to'],[])
    c=deploy('c',shas=[]); c['environment']='staging'
    assert score([a,b,c])['counts']['deployments']==1

def test_first_success_only():
    events=[commit(),deploy('fail',outcome='failure'),deploy('later','2026-09-05T00:00:00Z'),deploy('first','2026-09-04T00:00:00Z')]
    result=score(events)
    assert result['counts']['lead_time_pairs']==1
    assert result['change_lead_time_seconds_p50']==172800

def test_first_duplicate_wins_before_validation():
    first=deploy(shas=[])
    assert score([first,{'event_id':first['event_id'],'type':'garbage'}]) == score([first])

def test_even_median_half_up():
    result=score([commit(),commit('b','2026-09-02T00:00:01Z','B'),deploy(at='2026-09-02T00:00:02Z',shas=['a','b'])])
    assert result['change_lead_time_seconds_p50']==2

def test_recovery_tie_uses_incident_id():
    result=score([deploy(shas=[],outcome='failure'),incident('z','opened','2026-09-03T01:00:00Z',['a']),
        incident('a','opened','2026-09-03T01:00:00Z',['a']),incident('a','resolved','2026-09-03T02:00:00Z',['a'])])
    assert result['failed_deployment_recovery_time_seconds_p50']==7200

def test_rework_requires_both_attributes():
    events=[deploy('a',shas=[]),deploy('b',shas=[]),incident('i','opened','2026-09-03T00:00:00Z',[])]
    events[0]['unplanned']=True
    events[1]['caused_by']='i'
    assert score(events)['deployment_rework_rate']==0
    events[1]['unplanned']=True
    assert score(events)['deployment_rework_rate']==0.5

@pytest.mark.parametrize('events', [[commit(reverts='missing',change=None)], [commit('a',reverts='b',change=None),commit('b',reverts='a',change=None)], [deploy()], [incident('x','resolved','2026-09-03T00:00:00Z',[])]])
def test_malformed_graph(events):
    status,result=call('/dora/metrics','POST',{'window':WINDOW,'events':events})
    assert status in (400,422) and 'error' in result

@pytest.mark.parametrize('body', [[],{}, {'window':WINDOW}, {'window':WINDOW,'events':{}}, {'window':{'from':WINDOW['from'],'to':WINDOW['from']},'events':[]}])
def test_bad_request_shape(body):
    status,result=call('/dora/metrics','POST',body)
    assert status in (400,422) and 'error' in result


def test_ticket_lifecycle_export():
    from .test_api import create, action
    ticket=create()
    action(ticket,'ack')
    action(ticket,'start')
    action(ticket,'resolve')
    status, events=call('/dora/ticket-events')
    assert status==200
    own=[e for e in events if e['ticket_id']==ticket['id']]
    assert {e['phase'] for e in own}=={'created','acknowledged','resolved'}
    assert next(e for e in own if e['phase']=='created')['state']=='new'
    assert events==sorted(events,key=lambda e:(e['at'],e['ticket_id']))
    action(ticket,'reopen')
    own=[e for e in call('/dora/ticket-events')[1] if e['ticket_id']==ticket['id']]
    assert {e['phase'] for e in own}=={'created','acknowledged'}
