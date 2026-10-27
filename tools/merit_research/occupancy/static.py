"""冻结官品与供给，隔离四级槽位结构及选择核；不模拟原版自然初始任职。"""
import hashlib,json
from pathlib import Path
import simulate as sim
import appointments as app

ROOT=Path(__file__).parent

def frozen(route,structure,mode,seed):
 people={};pid=0;jobs=sim.jobs_for(route,structure,seed)
 for rank,n in enumerate(sim.pr.BASE[route]['n'],1):
  for _ in range(n):
   people[pid]={'id':pid,'rank':rank,'score':80+80*sim.pr.uniform(seed,pid,0,33),'age':40,'active':True,'alive':True,'job':None,'cooldown_until':0,'retirement_age':70};pid+=1
 counts=sim.JOBS[route][structure]
 events=[{'appointments':0,'high':0,'suitable_available':0,'high_with_suitable':0,'merit_advantage':0} for _ in range(4)]
 for job in sorted(jobs.values(),key=lambda j:(j['tier'],j['prominence']),reverse=True):
  candidates=[p for p in people.values() if app.eligible(p,job,jobs,0)]
  winner,m=app.choose(candidates,job,0,seed,mode=mode)
  if winner is None:continue
  assert winner['job'] is None
  b=job['tier']-1;winner['job']=job['id'];winner['cooldown_until']=5;job['holder']=winner['id']
  events[b]['appointments']+=1;events[b]['high']+=m['winner_high_band'];events[b]['suitable_available']+=m['suitable_available'];events[b]['high_with_suitable']+=m['winner_high_band'] and m['suitable_available'];events[b]['merit_advantage']+=m['merit_advantage_proxy']
 O=[[0]*4 for _ in range(9)]
 for job in jobs.values():
  if job['holder'] is not None:O[people[job['holder']]['rank']-1][job['tier']-1]+=1
 return {'route':route,'structure':structure,'mode':mode,'seed':seed,'J':counts,'O':O,'events':events,'employed_by_rank':[sum(row) for row in O]}

def main():
 rows=[frozen(route,st,mode,seed) for route in ['civil','military'] for st in ['base','lower_heavy','upper_expanded'] for mode in ['merit_first','score_only','suitable_first'] for seed in range(4)]
 out={'kind':'冻结结构对照，所有人40岁无病，人工分数；不是实测开局','source_sha256':{n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in ['static.py','simulate.py','appointments.py']},'runs':rows}
 (ROOT/'static-results.json').write_text(json.dumps(out,ensure_ascii=False));print('DONE',len(rows),'frozen allocations')
if __name__=='__main__':main()
