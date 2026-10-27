"""纯数学情景实验；不读取或模拟CK3引擎接口，不构成游戏行为回归。"""
import hashlib, json, math, random, statistics
from pathlib import Path
TH=[0,100,1000,2000,3500,5500,8500,12000,17000,23000]
BASE={
 'civil': {'n':[702,81,1,21,6,12,17,11,1], 'e':[0,0,0,6,0,8,0,0,0], 'd':[348,59,15,8], 'k':[2.5,2,2,4], 'birth':26},
 'military': {'n':[244,1,0,1,6,4,8,0,0], 'e':[0,0,0,1,0,3,0,0,0], 'd':[63,19,3,1], 'k':[4,2,4,10], 'birth':8}}

def band(level): return min(3,(level-1)//2)
def tally(people):
 out=[0]*4
 for p in people:out[band(p['l'])]+=1
 return out

def pressure(N,K,H):
 if N<=K:return 0
 return min(1,(N-K)/max(1,H-K))
def rate(work,K,target,h=.2,lam=.25,rho=.5,maximum=.5):
 H=[math.floor((1+h)*x) for x in K]
 z=[pressure(work[b],K[b],H[b]) for b in range(4)]
 if K[target]<=0:return 0
 direct=1-z[target]
 indirect=min(maximum,lam*sum(rho**(j-target-1)*z[j] for j in range(target+1,4)))
 return direct*(1-indirect)

def uniform(seed,pid,year,channel):
 # 分用途计数器随机数；政策改变抽选次数不会改变潜在死亡、入仕禀赋或其他人的抽签冲击。
 mask=(1<<64)-1
 x=(seed*0x9E3779B97F4A7C15+pid*0xD1B54A32D192ED03+year*0x94D049BB133111EB+channel*0xBF58476D1CE4E5B9)&mask
 x=(x^(x>>30))*0xBF58476D1CE4E5B9&mask;x=(x^(x>>27))*0x94D049BB133111EB&mask;x^=x>>31
 return ((x>>11)+.5)/(1<<53)
def growth(seed,pid,annual):
 z=math.sqrt(-2*math.log(uniform(seed,pid,0,1)))*math.cos(2*math.pi*uniform(seed,pid,0,2))
 return annual*math.exp(-.5*.5**2+.5*z)
def ceiling(seed,pid):
 u=uniform(seed,pid,0,3)
 return 2 if u<.1 else 4 if u<.6 else 6 if u<.9 else 9
def balanced_round(q,u): return math.floor(q)+(u<q-math.floor(q))
def entitlement(rng):return rng.choices([2,4,6,9],[.1,.5,.3,.1])[0]
def newperson(pid,level,merit,g,cap,entry=None):
 return {'id':pid,'l':level,'m':merit,'g':g,'cap':cap,'entry':entry,'hit':{},'ever3':False}

def trial(route,seed,profile='middle',annual=240,years=100,temp=.5,exit_rate=.03,entrants=None,shock=False,allqualified=False,commonk=False,policy='A',boost=.5,scenario_id=None):
 d=BASE[route];seedkey=seed+(1000000 if route=='military' else 0)
 ratio={'wide':(1.25,.45,.25),'middle':(1,.35,.15),'tight':(.8,.25,.08),'reference':(1,.6,.25),'opportunity':(1,.75,.4),'reference_top':(1,.6,.25)}[profile]
 ks=[3,2,2,4] if commonk else d['k']
 if profile in ['reference','reference_top']:ks=[2.5,1.5,1.5,3]
 elif profile=='opportunity':ks=[3,2,2,4]
 if profile=='reference_top' and route=='military':ks=[2.5,1.5,1.5,8]
 K=[math.floor(a*b*ratio[0]) for a,b in zip(d['d'],ks)]
 H=[math.floor(1.2*x) for x in K]
 people=[];pid=0;departed=[];cohort=[];rows=[]
 for l,(n,e) in enumerate(zip(d['n'],d['e']),1):
  for j in range(n):
   g=growth(seedkey,pid,annual)
   m=TH[l]+(TH[min(9,l+1)]-TH[l])*(1.2 if j<e else .25)
   people.append(newperson(pid,l,m,g,9 if allqualified else max(l,ceiling(seedkey,pid))));pid+=1
 for t in range(years):
  if t:
   survivors=[]
   for p in people:
    if uniform(seedkey,p['id'],t,4)<exit_rate:
     if p['entry'] is not None:departed.append(p)
    else:survivors.append(p)
   people=survivors
   for _ in range(d['birth'] if entrants is None else entrants):
    p=newperson(pid,1,100,growth(seedkey,pid,annual),9 if allqualified else ceiling(seedkey,pid),t)
    people.append(p);pid+=1
    if 10<=t<40:cohort.append(p)
   for p in people:
    if p['entry']!=t:p['m']+=p['g']
  if shock and t==40:
   K=[math.floor(x*.5) for x in K];H=[math.floor(1.2*x) for x in K]
  work=tally(people);source=[p['l'] for p in people];pre_merit=[p['m'] for p in people];pre_counts=[sum(p['l']==l for p in people) for l in range(1,10)];candidates={l:[p for p in people if p['l']==l and p['cap']>=l+1 and p['m']>=TH[l+1]] for l in range(1,7)}
  flow=[0]*6;eligible=[len(candidates[l]) for l in range(1,7)]
  for l in range(6,0,-1):
   b=band(l);tar=band(l+1);cross=tar!=b;E=candidates[l]
   F=rate(work,K,tar) if cross else (max(.8,1-.2*pressure(work[b],K[b],H[b])) if K[b] else .8)
   U=1+boost*max(0,1-work[tar]/K[tar]) if cross and K[tar]>0 else 1
   if cross and policy=='B':q=.03*K[tar]*F
   elif cross and policy=='C':q=.25*max(0,K[tar]-work[tar])*F
   else:q=len(E)*(ratio[2] if cross else ratio[1])*F*U
   q=min(q,len(E))
   V=max(0,H[tar]-work[tar]) if cross else len(E)
   Q=min(len(E),V,balanced_round(min(q,V),uniform(seedkey,l,t,5)))
   # 精确实数指数的Gumbel排序；不声称再现引擎定点pow与截断。
   B=max(1,temp*(TH[l+1]-TH[l]))
   scores=[((p['m']/B)*math.log(2)-math.log(-math.log(uniform(seedkey,p['id'],t,6))),p) for p in E]
   chosen=[p for _,p in sorted(scores,key=lambda x:x[0],reverse=True)[:Q]]
   for p in chosen:
    p['l']=l+1;p['m']=TH[l+1];flow[l-1]+=1
    if p['entry'] is not None:p['hit'].setdefault(l+1,t-p['entry'])
    if l+1==7:p['ever3']=True
   if cross:
    before=work[tar];work[b]-=len(chosen);work[tar]+=len(chosen)
    assert len(chosen)==0 or work[tar]<=H[tar]
    assert before<=H[tar] or len(chosen)==0
  assert work==tally(people)
  post_counts=[sum(p['l']==l for p in people) for l in range(1,10)]
  for l in range(1,10):
   incoming=flow[l-2] if 2<=l<=7 else 0
   outgoing=flow[l-1] if l<=6 else 0
   assert post_counts[l-1]==pre_counts[l-1]+incoming-outgoing
  for p,old_l,old_m in zip(people,source,pre_merit):
   assert p['m']==(TH[p['l']] if p['l']!=old_l else old_m)
  assert all(0<=p['l']-a<=1 for p,a in zip(people,source))
  rows.append({'year':t,'bands':tally(people),'flow':flow,'eligible':eligible,'K':K[:],'H':H[:]})
 # 入仕年10..39，第99年结束：最短60历年及61次脉冲；40年固定观察终点完整，死亡是竞争事件。
 reached=[p for p in cohort if p['ever3']]
 time=[p['hit'][7] for p in reached]
 under40=sum(p['ever3'] and p['hit'][7]<=40 for p in cohort)
 capable=[p for p in cohort if p['cap']>=7]
 time40=[p['hit'][7] for p in reached if p['hit'][7]<=40]
 liveids={p['id'] for p in people}
 progress={str(l):sum(any(k>=l and v<=40 for k,v in p['hit'].items()) for p in cohort) for l in range(2,8)}
 return {'scenario_id':scenario_id or f'{route}/{annual}/{profile}/{policy}', 'policy':policy,'boost':boost,'shock':shock,'exit_rate':exit_rate,'entrants':d['birth'] if entrants is None else entrants,'route':route,'profile':profile,'annual':annual,'temp':temp,'seed':seed,'allqualified':allqualified,'commonk':commonk,
 'initial_bands':[sum(n for l,n in enumerate(d['n'],1) if band(l)==b) for b in range(4)],'last_bands':rows[-1]['bands'],'K':K,'H':H,
 'first_eligible':[len(candidates[l]) for l in range(1,7)] if years==1 else rows[0]['eligible'],'last20_top_flow':statistics.mean(x['flow'][5] for x in rows[-20:]),
 'last20_total_flow':statistics.mean(sum(x['flow']) for x in rows[-20:]),
 'cohort_n':len(cohort),'cohort_capable':len(capable),'cohort_capable_reached40':sum(p['ever3'] and p['hit'][7]<=40 for p in capable),'progress40':progress,'reached3_years40':time40,'cohort_reached3':len(reached),'cohort_reached3_40':under40,
 'reached3_years_sum':sum(time),'reached3_years':time,
 'cohort_alive_unreached':sum(not p['ever3'] and p['id'] in liveids for p in cohort),
 'trajectory':rows if seed==0 else []}

def summarize(rs):
 times=[x for r in rs for x in r['reached3_years40']];n=sum(r['cohort_n'] for r in rs)
 vals=[r['cohort_reached3_40']/r['cohort_n'] for r in rs]
 return {'runs':len(rs),'cohort_n':n,'reach3_within40':sum(r['cohort_reached3_40'] for r in rs)/n,
 'reach3_within40_seed_minmax':[min(vals),max(vals)],
 'reach3_within40_capable':sum(r['cohort_capable_reached40'] for r in rs)/max(1,sum(r['cohort_capable'] for r in rs)),
 'progress40':{str(l):sum(r['progress40'][str(l)] for r in rs)/n for l in range(2,8)},
 'conditional_reach3_within40_median_years':statistics.median(times) if times else None,
 'last20_top_flow_mean':statistics.mean(r['last20_top_flow'] for r in rs),
 'last20_top_flow_seed_minmax':[min(r['last20_top_flow'] for r in rs),max(r['last20_top_flow'] for r in rs)],
 'last_bands_mean':[statistics.mean(r['last_bands'][b] for r in rs) for b in range(4)],'K':rs[0]['K'],'H':rs[0]['H']}

def main():
 results=[];groups={}
 for route in BASE:
  for annual in [60,240,720]:
   for profile in ['tight','middle','wide']:
    key=f'{route}/{annual}/{profile}'
    rr=[trial(route,s,profile,annual,scenario_id=key) for s in range(12)];results.extend(rr);groups[key]=summarize(rr)
 for tag,kwargs in [('allqualified',{'allqualified':True}),('commonk',{'commonk':True}),('shock',{'shock':True}),('sharp',{'temp':.2}),('soft',{'temp':1.0})]:
  for route in BASE:
   rr=[trial(route,s,'middle',720,scenario_id=f'{route}/720/middle/{tag}',**kwargs) for s in range(12)];results.extend(rr);groups[f'{route}/720/middle/{tag}']=summarize(rr)
 for policy in ['B','C']:
  for route in BASE:
   key=f'{route}/720/middle/policy{policy}'
   rr=[trial(route,s,'middle',720,policy=policy,scenario_id=key) for s in range(12)];results.extend(rr);groups[key]=summarize(rr)
 for profile in ['reference','opportunity','reference_top']:
  for route in BASE:
   key=f'{route}/720/{profile}'
   rr=[trial(route,s,profile,720,scenario_id=key) for s in range(12)];results.extend(rr);groups[key]=summarize(rr)
 out=Path(__file__).parent
 (out/'results.json').write_text(json.dumps({'model_version':'candidate-v2','source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'kind':'hypothetical mathematical sensitivity study, not CK3 regression','assumptions':{'all_simulated_people_are_adults':True,'years':100,'cohort_entry_years':[10,39],'seeds':list(range(12)),'exit':.03,'ceiling_distribution':{'2':.1,'4':.5,'6':.3,'9':.1},'growth_lognormal_cv_log':.5,'growth_timing':'before pulse for existing people; new entrants start at100 and first gain next year; t0 artificial conditional merit snapshot','random_design':'counter-based per seed/actor/year/channel; exogenous random shocks shared across policies','initial_merit_and_ceiling':'synthetic subject to observed n and preliminary merit-qualified counts; complete eligible counts not observed','policyB_mu':.03,'policyC_gamma':.25,'missing_capacity_boost':.5,'central_flow':0,'uniform_exit_hazard':True,'mathematical_ideal_weights':True},'groups':groups,'runs':results},ensure_ascii=False))
 print(json.dumps(groups,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
