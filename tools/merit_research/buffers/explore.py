"""独立研究分带超员缓冲、取整与压力传导；不运行游戏，不修改游戏规则。"""
import hashlib,json,math,statistics
from pathlib import Path
from model import BASE,trial,summarize,limit,pressure,transmission,upstream_pressure,balanced_round,uniform

CONFIGS={
 'uniform20_legacy':dict(hvec=(.2,.2,.2,.2),upstream='shared',within_up=0),
 'uniform20_w10':dict(hvec=(.2,.2,.2,.2),upstream='shared',within_up=.1),
 'graded_shared':dict(hvec=(.2,.2,.3,.5),upstream='shared',within_up=.1),
 'graded_split':dict(hvec=(.2,.2,.3,.5),upstream='fixed20',within_up=.1),
 'uniform50_split':dict(hvec=(.5,.5,.5,.5),upstream='fixed20',within_up=.1),
 'graded_ceil':dict(hvec=(.2,.2,.3,.5),upstream='fixed20',within_up=.1,limit_rule='ceil'),
 'graded_reserve':dict(hvec=(.2,.2,.3,.5),upstream='fixed20',within_up=.1,limit_rule='reserve-top'),
 'uniform20_reserve':dict(hvec=(.2,.2,.2,.2),upstream='fixed20',within_up=.1,limit_rule='reserve-top'),
 'uniform20_ceil':dict(hvec=(.2,.2,.2,.2),upstream='fixed20',within_up=.1,limit_rule='ceil'),
 'graded40_split':dict(hvec=(.2,.2,.3,.4),upstream='fixed20',within_up=.1),
}

def quantile(values,p):
 if not values:return None
 a=sorted(values);return a[max(0,math.ceil(len(a)*p)-1)]

def summary(runs):
 s=summarize(runs);s['stages']=[]
 for l in range(6):
  exp=sum(r['stage'][l]['exposure'] for r in runs)
  waits=[v for r in runs for v in r['waits40'][l]]
  risk={key:sum(r['risk40'][l][key] for r in runs) for key in runs[0]['risk40'][l]}
  s['stages'].append({**risk,'eligible_person_years':exp,
   'closed_candidate_share':sum(r['stage'][l]['closed_exposure'] for r in runs)/exp if exp else None,
   'raw_space_limited_candidate_share':sum(r['stage'][l]['raw_space_limited_exposure'] for r in runs)/exp if exp else None,
   'candidate_weighted_factor':sum(r['stage'][l]['factor_sum'] for r in runs)/exp if exp else None,
   'candidate_weighted_within_up_loss':sum(r['stage'][l]['within_up_sum'] for r in runs)/exp if exp else None,
   'conditional_success_wait_mean':statistics.mean(waits) if waits else None,
   'conditional_success_wait_p90':quantile(waits,.9),'conditional_wait_sample_n':len(waits)})
 s['overH_years_mean']=[statistics.mean(r['overH_years'][b] for r in runs) for b in range(4)]
 s['atH_years_mean']=[statistics.mean(r['atH_years'][b] for r in runs) for b in range(4)]
 return s

def pure_death(N0,H,d=.03):
 # 首次准入空间：死亡检查后N<H。无进入且独立永久退出时二项分布给出精确首次开放CDF。
 if H<=0:return {'never_open':True,'mean':None,'median':None,'p90':None}
 if N0<H:return {'mean':0,'median':0,'p90':0}
 if d==0:return {'never_open':True,'mean':None,'median':None,'p90':None}
 def tail(t):
  p=(1-d)**t
  return sum(math.comb(N0,j)*p**j*(1-p)**(N0-j) for j in range(H,N0+1))
 out={'mean':0.,'median':None,'p90':None};t=0
 while True:
  v=tail(t);out['mean']+=v
  if out['median'] is None and 1-v>=.5:out['median']=t
  if out['p90'] is None and 1-v>=.9:out['p90']=t
  if v<1e-13 and t>10:break
  t+=1
  if t>10000:raise RuntimeError('纯退出尾和未收敛')
 return out

def top_chain(K,h,J=.0,d=.03,seed=0,years=400):
 # 独立最高带研究链：先退出，再普通进入，再中央净进入。e=20恒供给，无上层。
 H=limit(K,h);N=K;total_q=total_j=total_d=0;measure=[]
 for t in range(years):
  deaths=sum(uniform(seed,j,t,10)<d for j in range(N));N-=deaths
  z=pressure(N,K,H);U=1+.5*max(0,1-N/K)
  q=min(20,max(0,H-N),20*.4*(1-z)*U)
  Q=balanced_round(q,uniform(seed,0,t,11));N+=Q
  C=balanced_round(J,uniform(seed,0,t,12));N+=C
  total_q+=Q;total_j+=C;total_d+=deaths
  assert N==K+total_q+total_j-total_d
  if t>=200:measure.append((N,Q,C,deaths))
 return {'N':statistics.mean(x[0] for x in measure),'ordinary':statistics.mean(x[1] for x in measure),'central':statistics.mean(x[2] for x in measure),'deaths':statistics.mean(x[3] for x in measure),'K':K,'H':H}

def main():
 groups={};allruns=[]
 for route in BASE:
  for profile in ['reference','opportunity']:
   for annual in [240,720]:
    for name,kwargs in CONFIGS.items():
     key=f'{route}/{profile}/{annual}/{name}'
     rr=[trial(route,seed,profile,annual,scenario_id=key,**kwargs) for seed in range(12)]
     groups[key]=summary(rr);allruns.extend(rr)
    print('finished',route,profile,annual,flush=True)
 tables=[{'K':K,'h':h,'floor':limit(K,h),'ceil':limit(K,h,'ceil'),'reserve_top':limit(K,h,'reserve-top',3)} for K in [1,2,3,4,5,8,10,20,24,32,100] for h in [.2,.3,.4,.5,.75]]
 decay=[{'N0':8,'K':K,'h':h,'H':limit(K,h),'exit':.03,**pure_death(8,limit(K,h))} for K in [3,4] for h in [.2,.3,.5,.75]]
 chain=[]
 for K in [4,20]:
  for h in [.2,.5]:
   for d in [.01,.03]:
    for J in [0,.5,1]:
     rr=[top_chain(K,h,J,d,s) for s in range(100)]
     chain.append({'K':K,'h':h,'d':d,'J':J,'H':rr[0]['H'],'mean_N':statistics.mean(x['N'] for x in rr),'mean_ordinary':statistics.mean(x['ordinary'] for x in rr),'mean_central':statistics.mean(x['central'] for x in rr),'mean_deaths':statistics.mean(x['deaths'] for x in rr)})
 paired=[]
 for route in BASE:
  for profile in ['reference','opportunity']:
   for annual in [240,720]:
    lookup={(r['scenario_id'].split('/')[-1],r['seed']):r for r in allruns if r['route']==route and r['profile']==profile and r['annual']==annual}
    for a,b in [('uniform20_legacy','uniform20_w10'),('uniform20_w10','graded_shared'),('graded_shared','graded_split'),('graded_split','graded_ceil'),('graded_split','graded_reserve'),('graded_split','uniform50_split'),('graded40_split','graded_split'),('uniform20_w10','uniform20_reserve'),('uniform20_w10','uniform20_ceil')]:
     differences=[lookup[b,s]['cohort_reached3_40']/lookup[b,s]['cohort_n']-lookup[a,s]['cohort_reached3_40']/lookup[a,s]['cohort_n'] for s in range(12)]
     paired.append({'route':route,'profile':profile,'annual':annual,'from':a,'to':b,'reach3_40_delta_mean':statistics.mean(differences),'seed_delta_range':[min(differences),max(differences)]})
 root=Path(__file__).parent
 result={'version':'buffer-candidate-v1','kind':'mathematical sensitivity exploration, not CK3 evidence','source_sha256':{n:hashlib.sha256((root/n).read_bytes()).hexdigest() for n in ['model.py','explore.py']},'assumptions':{'years':100,'seeds':list(range(12)),'exit':.03,'entrant_civil_military':[26,8],'income_means':[240,720],'growth_log_sigma':.5,'fixed_cap_distribution':{'2':.1,'4':.5,'6':.3,'9':.1},'cohort_entry_years':[10,39],'outcome_window_years':40,'adults_only':True,'growth_and_caps_are_synthetic':True,'no_migration_central_or_bursts_in_micro':True,'top_chain_is_separate_controlled_experiment':True,'controlled_observation_years':[200,399],'controlled_seeds':100,'controlled_total_years':400,'upstream_alpha_when_split':.2,'within_max_up_loss':.1,'rho':.5,'cross_lambda':.25,'cross_max_up_loss':.5,'direct_within_max_loss':.2,'boost':.5},'configs':CONFIGS,'groups':groups,'paired_differences':paired,'integer_tables':tables,'pure_death':decay,'controlled_top_chain':chain,'runs':allruns}
 (root/'results.json').write_text(json.dumps(result,ensure_ascii=False))
 (root/'summary.json').write_text(json.dumps({key:result[key] for key in result if key!='runs'},ensure_ascii=False,indent=2))
 print('DONE',len(groups),'groups',len(allruns),'micro runs',len(chain),'controlled cells')
if __name__=='__main__':main()
