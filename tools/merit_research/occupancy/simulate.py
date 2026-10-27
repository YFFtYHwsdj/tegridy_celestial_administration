"""四级竞争头衔、官品与年龄健康的耦合研究；不运行/复刻CK3引擎。"""
import argparse,copy,hashlib,importlib.util,json,math,statistics
from pathlib import Path
import aging
import appointments as app

ROOT=Path(__file__).parent
spec=importlib.util.spec_from_file_location('promotion_research',ROOT.parent/'merit-buffer-study/model.py')
pr=importlib.util.module_from_spec(spec);spec.loader.exec_module(pr)
JOBS={
 'civil':{'base':[348,59,15,8],'lower_heavy':[383,30,9,8],'upper_expanded':[298,89,30,13],'half':[174,29,7,4]},
 'military':{'base':[63,19,3,1],'lower_heavy':[74,9,2,1],'upper_expanded':[51,26,6,3],'half':[31,9,1,1]},
}
HEALTH_CACHE={}

def cached_health(seed,pid,age,profile):
 key=(seed,pid,age,profile)
 if key not in HEALTH_CACHE:HEALTH_CACHE[key]=aging.make_health(seed,pid,age,profile)
 return copy.deepcopy(HEALTH_CACHE[key])

def make_person(seed,pid,rank,merit,cap,entry=None,health_profile='base',age=None):
 if age is None:age=max(18,min(72,18+5*rank+int(10*pr.uniform(seed,pid,0,21)-5)))
 s=cached_health(seed,pid,age,health_profile)
 p={'id':pid,'rank':rank,'m':merit,'cap':cap,'g':pr.growth(seed,pid,720),'score':80+80*pr.uniform(seed,pid,0,22),
    'active':True,'alive':True,'job':None,'cooldown_until':0,'retirement_age':70,'entry':entry,'first_job':None,
    'first_job_rank':None,'first_job_tier':None,'death_year':None,'health':s,'health_pid':pid,'central_year':-1}
 sync_health(p);return p

def sync_health(p):
 s=p['health'];p.update(age=s['age'],elder_count=s['elder_count'],incapable=s['incapable'],blind=s['blind'],age_related_ailment=s['elder_count']>0,alive=s['alive'])

def jobs_for(route,structure,seed):
 result={};jid=0
 for tier,count in enumerate(JOBS[route][structure],1):
  for _ in range(count):
   result[jid]={'id':jid,'tier':tier,'kind':'admin','holder':None,'prominence':10**tier*(1+.5*pr.uniform(seed,jid,0,23))};jid+=1
 return result

def trial(route,seed,structure='base',mortality='base',mode='merit_first',promotion=True,mobility=True,feedback=False,age_shuffle=False,years=80):
 sk=seed+(1000000 if route=='military' else 0)
 health_profile='base' if mortality=='flat3' else mortality
 jobs=jobs_for(route,structure,sk);people={};cohort=[];pid=0;dead=[]
 for rank,(n,e) in enumerate(zip(pr.BASE[route]['n'],pr.BASE[route]['e']),1):
  for j in range(n):
   merit=pr.TH[rank]+(pr.TH[min(9,rank+1)]-pr.TH[rank])*(1.2 if j<e else .25)
   p=make_person(sk,pid,rank,merit,max(rank,pr.ceiling(sk,pid)),health_profile=health_profile)
   people[pid]=p;pid+=1
 if age_shuffle:
  packages=[(p['health'],p['health_pid']) for p in people.values()]
  order=sorted(range(len(packages)),key=lambda x:pr.uniform(sk,x,0,24))
  for p,index in zip(people.values(),order):p['health'],p['health_pid']=packages[index];sync_health(p)
 if mortality=='flat3':
  for p in people.values():
   p['elder_count']=0;p['incapable']=False;p['blind']=False;p['age_related_ailment']=False
 count=JOBS[route][structure];K=[math.floor(c*k) for c,k in zip(count,[3,2,2,4])]
 H=[pr.limit(k,h,'floor',b) for b,(k,h) in enumerate(zip(K,[.2,.2,.3,.5]))]
 # 本次全为抽象竞争槽，容量J按四级现存槽位计，空缺另账；不是对已批准正式D口径的静默替换。
 metrics={'appointments':[0]*4,'low_competitive_events':[0]*4,'high_wins_with_low':[0]*4,'merit_advantage':[0]*4,
          'high_new':[0]*4,'score_delta_sums':[0.]*4,'score_delta_n':[0]*4,'filled_years':[0]*4,
          'high_occupied_years':[0]*4,'slot_years':[0]*4,'relabel_to_high':[0]*4,'transfer_release':[0]*4,
          'deaths':[0]*4,'deaths_unemployed':0,'death_causes':{},'central_grants':0,'ordinary_success':0,'vacant_unfilled':[0]*4}
 matrices=[];death_ages=[];series=[];stockK=[];nature_deaths={}

 def release(p,reason,record):
  old=p['job']
  if old is None:return None
  job=jobs[old];assert job['holder']==p['id'];job['holder']=None;p['job']=None
  if record and reason in ['death','transfer']:metrics['deaths' if reason=='death' else 'transfer_release'][job['tier']-1]+=1
  return old

 def fill(year,record):
  # 每个时点仅处理已有空缺；迁任新释放的槽排入队列，现任不被全体洗牌。
  queue=sorted([j['id'] for j in jobs.values() if j['holder'] is None],key=lambda j:(jobs[j]['tier'],jobs[j]['prominence']),reverse=True)
  attempted=set();events=0
  while queue:
   jid=queue.pop(0)
   if jobs[jid]['holder'] is not None or jid in attempted:continue
   attempted.add(jid);job=jobs[jid];tier=job['tier'];b=tier-1
   candidates=[p for p in people.values() if app.eligible(p,job,jobs,year,mobility)]
   winner,m=app.choose(candidates,job,year,sk,mode=mode)
   if winner is None:
    if record:metrics['vacant_unfilled'][b]+=1
    continue
   if record:
    metrics['appointments'][b]+=1;metrics['low_competitive_events'][b]+=int(m['suitable_available'])
    metrics['high_wins_with_low'][b]+=int(m['winner_high_band'] and m['suitable_available'])
    metrics['merit_advantage'][b]+=int(m['merit_advantage_proxy']);metrics['high_new'][b]+=int(m['winner_high_band'])
    if m['best_suitable_score'] is not None:
     metrics['score_delta_sums'][b]+=m['score_gap_to_best_suitable'];metrics['score_delta_n'][b]+=1
   old=release(winner,'transfer',record)
   job['holder']=winner['id'];winner['job']=jid;winner['cooldown_until']=year+5
   if old is not None and old not in attempted:queue.append(old)
   if winner['first_job'] is None:
    winner['first_job']=year;winner['first_job_rank']=winner['rank'];winner['first_job_tier']=tier
   # 帝级特授在此仅用二品作为抽象情景；不声称原版所有帝级头衔都按此授品。
   if tier==4 and winner['rank']<8:
    winner['rank']=8;winner['m']=pr.TH[8];winner['central_year']=year
    if record:metrics['central_grants']+=1
   events+=1;assert events<=len(jobs)+len(people)

 def promote(year,record):
  if not promotion:return
  work=[0]*4
  for p in people.values():work[pr.band(p['rank'])]+=1
  source={p['id']:p['rank'] for p in people.values()};before=len(people)
  pools={l:[p for p in people.values() if p['rank']==l and p['m']>=pr.TH[l+1] and p['cap']>=l+1 and p['central_year']!=year] for l in range(1,7)}
  for l in range(6,0,-1):
   b=pr.band(l);tar=pr.band(l+1);cross=b!=tar;E=pools[l]
   zl=[pr.pressure(work[j],K[j],H[j]) for j in range(4)];zu=[pr.upstream_pressure(work[j],K[j]) for j in range(4)]
   if cross:
    F=(1-zl[tar])*(1-pr.transmission(zu,tar)) if K[tar]>0 else 0
    U=1+.5*max(0,1-work[tar]/K[tar]) if K[tar] else 1
    q=min(len(E),len(E)*.4*F*U,max(0,H[tar]-work[tar]))
   else:q=len(E)*.75*max(.8,1-.2*zl[b])*(1-pr.transmission(zu,b,.1,.5,.1))
   Q=min(len(E),pr.balanced_round(q,pr.uniform(sk,l,year,25)))
   B=.5*(pr.TH[l+1]-pr.TH[l])
   selected=sorted(E,key=lambda p:p['m']/B*math.log(2)-math.log(-math.log(pr.uniform(sk,p['id'],year,26))),reverse=True)[:Q]
   for p in selected:
    old_high=p['job'] is not None and app.rank_band(p['rank'])>jobs[p['job']]['tier']
    p['rank']=l+1;p['m']=pr.TH[l+1]
    new_high=p['job'] is not None and app.rank_band(p['rank'])>jobs[p['job']]['tier']
    if record:
     metrics['ordinary_success']+=1
     if new_high and not old_high:metrics['relabel_to_high'][jobs[p['job']]['tier']-1]+=1
   if cross:work[b]-=len(selected);work[tar]+=len(selected);assert not selected or work[tar]<=H[tar]
  assert sum(work)==before
  assert all(0<=p['rank']-source[p['id']]<=1 for p in people.values())

 for t in range(years):
  record=t>=20
  if t:
   survivors={}
   for p in people.values():
    if mortality=='flat3':
     p['age']+=1;p['alive']=pr.uniform(sk,p['id'],t,27)>=.03
     cause=None if p['alive'] else 'uniform3_proxy'
    else:
     p['health']=aging.advance_year(p['health'],sk,p['health_pid'],t);sync_health(p);cause=p['health']['death_cause']
    if not p['alive']:
     p['death_year']=t;death_ages.append(p['age']);old=p['job'];release(p,'death',record)
     if record:
      if old is None:metrics['deaths_unemployed']+=1
      metrics['death_causes'][cause]=metrics['death_causes'].get(cause,0)+1
     dead.append(p)
    else:survivors[p['id']]=p
   people=survivors
   for _ in range(pr.BASE[route]['birth']):
    p=make_person(sk,pid,1,100,pr.ceiling(sk,pid),entry=t,health_profile=health_profile,age=18)
    if mortality=='flat3':p.update(elder_count=0,incapable=False,blind=False,age_related_ailment=False)
    people[pid]=p
    if 10<=t<30:cohort.append(p)
    pid+=1
   for p in people.values():
    if p['entry']==t:continue
    premium=1+.2*jobs[p['job']]['tier'] if feedback and p['job'] is not None else 1
    p['m']+=p['g']*premium
  fill(t,record);promote(t,record)
  O=[[0]*4 for _ in range(9)];filled=[0]*4;high=[0]*4
  for j in jobs.values():
   holder=j['holder']
   if holder is not None:
    assert holder in people and people[holder]['job']==j['id'];p=people[holder];b=j['tier']-1
    O[p['rank']-1][b]+=1;filled[b]+=1;high[b]+=int(app.rank_band(p['rank'])>j['tier'])
  occupied=[p['job'] for p in people.values() if p['job'] is not None]
  assert len(occupied)==len(set(occupied))==sum(filled)
  assert sum(sum(row) for row in O)==len(occupied)
  for b in range(4):assert filled[b]<=count[b]
  if record:
   matrices.append(O)
   for b in range(4):
    metrics['filled_years'][b]+=filled[b];metrics['high_occupied_years'][b]+=high[b];metrics['slot_years'][b]+=count[b]
  if seed==0:series.append({'year':t,'population':len(people),'filled':filled,'high':high,'rank_bands':[sum(pr.band(p['rank'])==b for p in people.values()) for b in range(4)],'mean_age':statistics.mean(p['age'] for p in people.values())})

 # 40年固定终点：入仕年10..29，截止79年，死亡作为竞争事件保留在分母。
 entry40=sum(p['first_job'] is not None and p['first_job']-p['entry']<=40 for p in cohort)
 wait=[p['first_job']-p['entry'] for p in cohort if p['first_job'] is not None and p['first_job']-p['entry']<=40]
 Omean=[[statistics.mean(O[a][b] for O in matrices) for b in range(4)] for a in range(9)]
 return {'route':route,'seed':seed,'structure':structure,'mortality':mortality,'mode':mode,'promotion':promotion,'mobility':mobility,'feedback':feedback,'age_shuffle':age_shuffle,
  'J':count,'K':K,'H':H,'metrics':metrics,'cohort_n':len(cohort),'first_job40':entry40,'conditional_first_job_wait':wait,
  'mean_occupation_matrix':Omean,'population_end':len(people),'death_ages':death_ages,'initialization':'合成初始人物/健康/全空槽合法分配，不是自然1066岗位持有分布',
  'series':series}

CASES=[]
for st in ['base','lower_heavy','upper_expanded']:
 for mort in ['flat3','base','longlife']:CASES.append(dict(structure=st,mortality=mort))
for st in ['base','upper_expanded']:CASES.append(dict(structure=st,mortality='base',promotion=False))
CASES.append(dict(mortality='no_elder'))
for st in ['base','lower_heavy']:
 for mode in ['score_only','suitable_first']:CASES.append(dict(structure=st,mode=mode))
CASES.extend([dict(age_shuffle=True),dict(mobility=False),dict(feedback=True),dict(structure='half')])
assert len(CASES)==20

def key(case):
 return ','.join(f'{k}={v}' for k,v in sorted(case.items())) or 'base'

def run_seed(seed):
 runs=[]
 for route in ['civil','military']:
  for case in CASES:
   r=trial(route,seed,**case);r['case']=key(case);runs.append(r)
   print('finished',seed,route,key(case),flush=True)
 return runs

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--seed',type=int,required=True);args=parser.parse_args()
 rows=run_seed(args.seed)
 out={'version':'occupancy-proxy-v1','source_sha256':{n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in ['simulate.py','aging.py','appointments.py']},'seed':args.seed,'runs':rows,'assumptions':{'period_years':80,'occupancy_observation':[20,79],'cohort_entry_years':[10,29],'outcome_window':40,'one_abstract_competitive_slot_per_official':True,'job_counts_are_scenario_inputs_not_measured_independent_jobs':True,'base_job_vectors':JOBS,'promotion_capacity_basis':'研究中按四级槽总数J计算K，不静默替换正式D口径','income_mean':720,'feedback_premium_per_tier':.2,'entry_age':18,'initial_age':'18+5*rank+Uniform(-5,5),clamp18..72','central_proxy':'获帝级槽不足a8时授a8；是研究例子，不是所有原版帝级规则','appointment_score':'人工80..160加原版局部年龄/病理项，非完整candidate_score','annual_aggregation':'死亡/任命/升品按年度边界聚合；占用年是年快照近似，非原生title-days','mortality':aging.ASSUMPTIONS,'appointment':app.ASSUMPTIONS}}
 (ROOT/f'run-seed-{args.seed}.json').write_text(json.dumps(out,ensure_ascii=False))
 print('DONE seed',args.seed,len(rows))
if __name__=='__main__':main()
