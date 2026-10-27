"""汇总四级槽位研究；保留描述存量、事件反事实和首次入职的不同分母。"""
import hashlib,json,statistics
from pathlib import Path
ROOT=Path(__file__).parent

def ratio(a,b):return a/b if b else None

def summarize(rows):
 out={'seeds':len(rows),'J':rows[0]['J'],'K':rows[0]['K'],'H':rows[0]['H'],'tiers':[]}
 for b in range(4):
  m={key:sum(r['metrics'][key][b] for r in rows) for key in ['appointments','low_competitive_events','high_wins_with_low','merit_advantage','high_new','score_delta_sums','score_delta_n','filled_years','high_occupied_years','slot_years','relabel_to_high','transfer_release','deaths','vacant_unfilled']}
  out['tiers'].append({**m,'high_filled_share':ratio(m['high_occupied_years'],m['filled_years']),'high_slot_share':ratio(m['high_occupied_years'],m['slot_years']),
   'fill_share':ratio(m['filled_years'],m['slot_years']),'high_with_low_event_share':ratio(m['high_wins_with_low'],m['low_competitive_events']),
   'merit_advantage_event_share':ratio(m['merit_advantage'],m['low_competitive_events']),'high_new_share':ratio(m['high_new'],m['appointments']),
   'mean_score_gap_best_suitable':ratio(m['score_delta_sums'],m['score_delta_n'])})
 out['cohort_n']=sum(r['cohort_n'] for r in rows);out['first_job40']=sum(r['first_job40'] for r in rows);out['first_job40_share']=ratio(out['first_job40'],out['cohort_n'])
 vals=[ratio(r['first_job40'],r['cohort_n']) for r in rows]
 out['first_job40_seed_range']=[min(vals),max(vals)]
 wait=[w for r in rows for w in r['conditional_first_job_wait']]
 out['conditional_first_job_wait_median']=statistics.median(wait) if wait else None
 out['conditional_first_job_wait_n']=len(wait)
 out['population_end_mean']=statistics.mean(r['population_end'] for r in rows)
 out['mean_occupation_matrix']=[[statistics.mean(r['mean_occupation_matrix'][a][b] for r in rows) for b in range(4)] for a in range(9)]
 out['ordinary_success']=sum(r['metrics']['ordinary_success'] for r in rows)
 out['central_grants']=sum(r['metrics']['central_grants'] for r in rows)
 out['death_causes']={}
 for r in rows:
  for key,value in r['metrics']['death_causes'].items():out['death_causes'][key]=out['death_causes'].get(key,0)+value
 return out

def main():
 sources=[json.loads((ROOT/f'run-seed-{s}.json').read_text()) for s in range(4)]
 for d in sources:
  assert all(hashlib.sha256((ROOT/f).read_bytes()).hexdigest()==h for f,h in d['source_sha256'].items())
 dep=ROOT.parent/'merit-buffer-study/model.py'
 dep_sha=hashlib.sha256(dep.read_bytes()).hexdigest()
 sealed=json.loads((ROOT.parent/'merit-buffer-study/results.json').read_text())
 assert dep_sha==sealed['source_sha256']['model.py']
 rows=[r for d in sources for r in d['runs']];groups={}
 for route in ['civil','military']:
  for case in sorted({r['case'] for r in rows}):
   rr=[r for r in rows if r['route']==route and r['case']==case];assert len(rr)==4
   groups[f'{route}/{case}']=summarize(rr)
 static=json.loads((ROOT/'static-results.json').read_text())
 assert all(hashlib.sha256((ROOT/f).read_bytes()).hexdigest()==h for f,h in static['source_sha256'].items())
 out={'version':'occupancy-proxy-v1','kind':'source-anchored synthetic lifecycle/occupation study, not CK3 evidence','source_sha256':{f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in ['simulate.py','aging.py','appointments.py','aggregate.py','static.py']},'dependency_sha256':{'../merit-buffer-study/model.py':dep_sha},'assumptions':sources[0]['assumptions'],'groups':groups,'runs':rows,'static_runs':static['runs']}
 (ROOT/'results.json').write_text(json.dumps(out,ensure_ascii=False));(ROOT/'summary.json').write_text(json.dumps({k:v for k,v in out.items() if k not in ['runs','static_runs']},ensure_ascii=False,indent=2))
 print('DONE',len(groups),'groups',len(rows),'dynamic runs',len(static['runs']),'static allocations')
if __name__=='__main__':main()
