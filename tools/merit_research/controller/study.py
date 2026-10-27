"""累计尾部控制器研究；合成人口计数，不代表原生功绩/退出过程。"""
import hashlib
import json
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent
TARGET = np.array([120., 120., 40., 40., 15., 15., 10.])

def quota(n, target, eligible, r=.04/.96, gain=.35):
    """读取六个普通来源和合并三二一品；返回六道期望流量。"""
    tails = np.cumsum(n[::-1])[::-1][1:]
    goals = np.cumsum(target[::-1])[::-1][1:]
    q = np.zeros(6)
    for i, (s, b) in enumerate(zip(tails, goals)):
        if b <= 0:
            continue
        q0 = r*b
        q[i] = q0 + gain*(b-s) if s <= b else q0/(1+gain*(s-b)/q0)
    return np.minimum(q, eligible)

def run(case, seed=None):
    rng = np.random.default_rng(seed)
    stochastic = seed is not None
    target = TARGET*case.get('scale', 1)
    n = target.copy()
    initial = case.get('initial', 'target')
    if initial == 'empty': n *= 0
    if initial == 'bottom': n[:] = 0; n[0] = sum(target)*3
    if initial == 'top': n[:] = 0; n[-1] = sum(target)*3
    if initial == 'high_top': n[-1] *= 100
    if stochastic: n = np.rint(n).astype(int)
    d = case.get('death', .04)
    rate = .04*sum(target)*case.get('entry', 1)
    efrac = case.get('eligible', .5)
    k = case.get('gain', .35)
    rows=[]
    for year in range(400):
        current_target = target * (.5 if case.get('shock') == 'capacity' and 100 <= year < 150 else 1)
        if case.get('shock') == 'mortality' and year == 100:
            n = rng.binomial(n, .5) if stochastic else n*.5
        if case.get('shock') == 'top_surplus' and year == 100:
            n[-1] += 10*target[-1]
        eligible = rng.binomial(n[:6], efrac) if stochastic else n[:6]*efrac
        q=quota(n,current_target,eligible,gain=k)
        if stochastic:
            whole = np.floor(q).astype(int)
            q = whole + (rng.random(6)<q-whole)
        before = n.sum()
        moved=n.copy(); moved[:6]-=q; moved[1:]+=q
        assert abs(moved.sum()-before)<1e-7 and np.all(moved>=-1e-7)
        if stochastic:
            n=rng.binomial(moved.astype(int),1-d)
        else: n=moved*(1-d)
        arrivals=rate*(10 if case.get('shock')=='entry' and 100<=year<120 else 1)
        n[0]+=rng.poisson(arrivals) if stochastic else arrivals
        tails=np.cumsum(n[::-1])[::-1][1:]
        goals=np.cumsum(current_target[::-1])[::-1][1:]
        rows.append({'year':year,'population':float(n.sum()),'n':n.tolist(),'tail_max_error':float(max(abs(tails/goals-1))), 'q':q.tolist()})
    late=rows[250:]
    recovery=None
    if case.get('shock'):
        start=150 if case['shock']=='capacity' else 120 if case['shock']=='entry' else 100
        for y in range(start,396):
            if all(rows[j]['tail_max_error']<=.2 for j in range(y,y+5)):
                recovery=y-start+1;break
    return {'case':case['name'],'seed':seed,'late_tail_max_error_mean':float(np.mean([r['tail_max_error'] for r in late])),
      'late_population_mean':float(np.mean([r['population'] for r in late])),
      'late_n_mean':np.mean([r['n'] for r in late],axis=0).tolist(),
      'late_zero_quota_share':np.mean([np.array(r['q'])==0 for r in late],axis=0).tolist(),
      'recovery_years':recovery,'series':rows if seed is None else []}

CASES=[{'name':'baseline'}]
for key, values in [('initial',['empty','bottom','top','high_top']),('entry',[.25,2,10]),('death',[.02,.08]),('eligible',[.01,.1,1]),('gain',[.2,.6]),('scale',[.05]),('shock',['mortality','capacity','entry','top_surplus'])]:
    CASES += [{'name':f'{key}={v}',key:v} for v in values]

def main():
    runs=[run(c,s) for c in CASES for s in [None,*range(12)]]
    groups={}
    for c in CASES:
        rs=[r for r in runs if r['case']==c['name']]
        st=rs[1:]
        groups[c['name']]={'deterministic':{k:v for k,v in rs[0].items() if k!='series'},
          'stochastic':{'seeds':12,'late_n_mean':np.mean([r['late_n_mean'] for r in st],axis=0).tolist(),
          'late_population_mean':float(np.mean([r['late_population_mean'] for r in st])),
          'late_tail_max_error_mean':float(np.mean([r['late_tail_max_error_mean'] for r in st])),
          'late_zero_quota_share':np.mean([r['late_zero_quota_share'] for r in st],axis=0).tolist()}}
    out={'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'target':TARGET.tolist(),'cases':CASES,'runs':runs,'groups':groups}
    (ROOT/'results.json').write_text(json.dumps(out,ensure_ascii=False))
    (ROOT/'summary.json').write_text(json.dumps({k:v for k,v in out.items() if k!='runs'},ensure_ascii=False,indent=2))
    print(f'{len(CASES)} cases, {len(runs)} runs')
    for k,g in groups.items():
        d=g['deterministic'];s=g['stochastic']
        print(k, 'deterr',round(d['late_tail_max_error_mean'],4),'population',round(s['late_population_mean'],1),'upper', [round(x,1) for x in s['late_n_mean'][1:]],'recovery',d['recovery_years'])

if __name__=='__main__':main()
