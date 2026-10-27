"""保持四带系数不变，比较旧统一收入与按来源分账的外部世界。

税额、兵池价值、个人来源及事件频率是公开合成输入；实际系数另从
本机源码核对并封存。每局原始结果立即保存，可按相同源码配置续跑。
"""
import argparse
from concurrent.futures import ProcessPoolExecutor,as_completed
from functools import partial
import importlib.util
import json
import math
import multiprocessing
from pathlib import Path
import re
import shutil
import sys

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent))
import parameter_analysis as parent


def load_model(root):
    path=root/'merit-income-study/model.py'
    spec=importlib.util.spec_from_file_location('source_income_reference',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def variants():
    """只改外部来源，不再搜索员额/反馈参数；中档不称实测均值。"""
    return [dict(name='legacy',legacy=True),
            dict(name='income_only',native_init=False,fiscal_scale=1),
            dict(name='low',native_init=True,fiscal_scale=.25),
            dict(name='reference',native_init=True,fiscal_scale=1),
            dict(name='high',native_init=True,fiscal_scale=4),
            dict(name='events',native_init=True,fiscal_scale=1,events=True),
            dict(name='personal',native_init=True,fiscal_scale=1,personal_fixed=2.5,personal_mult=.2)]


def plan():
    """基准同种子配对；高入仕与失地仅检查收入参考情景，不调参。"""
    return dict(version='source-ledger-v1',coefficients=[1.5,2,3,1.5],phi=[.6,.8,.5],
        r=.06,gain=.9,epsilon=.1,temperature=.5,reserve=[0,0,0],years=120,
        tax_by_tier=[10,60,240,0],maa_by_tier=[500,2500,10000,0],
        learning=10,variants=variants(),
        assumptions=dict(fiscal_bases_synthetic=True,not_real_income_distribution=True,
          ordinary_roles='显式假设民用标准省/军事省；县级契约适用仍待引擎确认',
          higher_titles='研究每人一个职务；中央例外槽固定20月，其余帝级槽仍地方角色',
          personal='默认无个人来源；personal臂假设人人同时有2/月特长、.25师门、.25庄园及.2倍率，不称普遍拥有',
          events='仅events臂显式安排：在任每5年一次发展20建筑；新人入仕15年后一次会试，25年后一次殿试补发分支；是供给压力上界，不是AI发生率',
          annual_timing='年初健康退出，非新建有效人物按上轮在任职务计十二个月；年度内任免/死亡不按日折算'),
        jobs=[dict(route=route,seed=seed,scenario='baseline',variants=[v['name'] for v in variants()])
              for route in ['civil','military'] for seed in [50,51]]+
             [dict(route=route,seed=50,scenario=scenario,variants=['reference'])
              for route in ['civil','military'] for scenario in ['entry4','loss']])


def source_catalog(game,repo):
    """从指定对象中核对关键常数；另扫描全部正式脚本的来源位置。

    不从金额推断发生率，不把测试夹具列成正式来源。原文与完整文件
    哈希仅写仓库外；对象不唯一、数值不符或版本漂移立即停止。
    """
    contract='common/subject_contracts/contracts/celestial.txt'
    specs=[('game',contract,'celestial_province_standard','monthly_merit_per_liege_tax',.8),
      ('game',contract,'celestial_province_industrial','monthly_merit_per_liege_tax',1.2),
      ('game',contract,'celestial_province_metropolitan','monthly_merit_per_liege_tax',2.4),
      ('game',contract,'celestial_province_military','monthly_merit_per_title_maa_value',.024),
      ('game',contract,'celestial_province_protectorate','monthly_merit_per_title_maa_value',.032),
      ('game',contract,'celestial_minister_civil','monthly_merit',20),
      ('game',contract,'celestial_minister_military','monthly_merit',20),
      ('game','common/modifiers/00_basic_modifiers.txt','king_modifier','monthly_merit_mult',.5),
      ('game','common/modifiers/00_basic_modifiers.txt','emperor_modifier','monthly_merit_mult',1),
      ('mod','common/subject_contracts/contracts/tca_official_contracts.txt','tca_official_judicial','monthly_merit',4),
      ('mod','common/subject_contracts/contracts/tca_official_contracts.txt','tca_official_tongpan','monthly_merit',2)]
    records=[]
    for origin,path,block,key,expected in specs:
        file=(game if origin=='game' else repo)/path
        text=file.read_text(encoding='utf-8-sig')
        clean=re.sub(r'#[^\n]*','',text)
        matches=list(re.finditer(r'\b'+re.escape(block)+r'\s*=\s*\{',clean))
        assert len(matches)==1,(block,len(matches))
        start=matches[0].end();end=start;depth=1
        while depth:
            if clean[end]=='{':depth+=1
            elif clean[end]=='}':depth-=1
            end+=1
        values=re.findall(r'\b'+key+r'\s*=\s*(-?[0-9.]+)',clean[start:end-1])
        assert len(values)==1 and float(values[0])==expected,(block,key,values)
        records.append(dict(origin=origin,path=path,object=block,key=key,value=expected,sha256=parent.digest(file)))
    hits=[];files={}
    pattern=re.compile(r'\b(?:monthly_merit\w*|monthly_war_merit\w*|merit_standalone_\w+|change_merit(?:_no_experience)?)\s*=')
    for origin,base in [('game',game),('mod',repo)]:
        for folder in ['common','events']:
            for path in sorted((base/folder).rglob('*.txt')):
                relative=path.relative_to(base).as_posix()
                if '/tests/' in '/'+relative or 'probe' in path.name:continue
                text=path.read_text(encoding='utf-8-sig')
                found=[dict(line=i,text=line.strip()) for i,line in enumerate(text.splitlines(),1)
                       if pattern.search(line.split('#',1)[0])]
                if found:
                    files[origin+'/'+relative]=parent.digest(path)
                    hits.append(dict(origin=origin,path=relative,locations=found))
    return dict(checked_constants=records,source_file_sha256=files,assignments=hits,
                meaning='来源位置清单不是所有条件分支的执行频率；README另列上下文与边界')


def verify(root,study):
    study.verify(root)
    source=json.loads((root/'income-source.json').read_text())
    assert source['dependencies']==study.hashes(root)
    for path in ROOT.glob('*.py'):
        assert parent.digest(path)==source['income'][path.name]==parent.digest(root/'merit-income-study'/path.name)
    assert json.loads((root/'income-plan.json').read_text())==plan()


def prepare(root,study,game):
    if not (root/'income-plan.json').exists():
        catalog=source_catalog(game,study.runner.REPO)
        study.runner.prepare(root,study.runner.selection('joint'))
        for folder,sources in [('merit-parameter-study',study.ROOT),('merit-income-study',ROOT)]:
            target=root/folder;target.mkdir()
            for path in sources.glob('*.py'):shutil.copyfile(path,target/path.name)
        shutil.copyfile(ROOT.parent/'calibrate_joint.py',root/'calibrate_joint.py')
        shutil.copyfile(ROOT.parent/'run.py',root/'runner_reference.py')
        save(root/'income-plan.json',plan());save(root/'income-catalog.json',catalog)
        save(root/'income-source.json',dict(dependencies=study.hashes(root),
             income={p.name:parent.digest(p) for p in ROOT.glob('*.py')},catalog=parent.digest(root/'income-catalog.json')))
    verify(root,study)
    assert json.loads((root/'income-source.json').read_text())['catalog']==parent.digest(root/'income-catalog.json')


def save(path,data):
    """逐局原子保存，断点续跑不覆盖其他已完成局。"""
    tmp=path.with_suffix('.writing');tmp.write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8');tmp.replace(path)


def path_for(root,route,seed,scenario,variant):
    return root/f'income-{route}-{seed}-{scenario}-{variant}.json'


def batch(job):
    """同路同种子配对，共用健康缓存，不共用收入或资格状态。"""
    root,work=job;root=Path(root);study=parent.load_study();verify(root,study)
    joint,capacity,_=study.models(root);model=load_model(root);p=plan()
    original=joint.capacity.targets
    joint.capacity.targets=partial(capacity.targets,coefficients=p['coefficients'],phi=p['phi'],reserve=p['reserve'])
    scenarios={s['name']:s for s in study.VALIDATE}
    try:
        with study.health_cache(joint.world):
            for variant in p['variants']:
                name=variant['name']
                if name not in work['variants']:continue
                output=path_for(root,work['route'],work['seed'],work['scenario'],name)
                if output.exists():continue
                cfg={k:p[k] for k in parent.POLICY_FIELDS}
                cfg.update(policy='requested',mapping='direct_band',**scenarios[work['scenario']])
                cfg=study.external_config(cfg,work['route'],joint.world,study.models(root)[2])
                seed=work['seed']+(1000000 if work['route']=='military' else 0)
                def initialize(person):
                    model.initialize_exams(person,lambda channel:joint.pr.uniform(seed,person['id'],0,channel),learning=p['learning'])
                def income(person,job,year):
                    tier=job['tier'] if job else 0
                    role='none' if job is None else 'minister' if job['central_target'] else ('civil_standard' if work['route']=='civil' else 'military')
                    scale=variant['fiscal_scale']
                    parts=model.annual_components(role=role,head_tier=tier,
                        personal_fixed=variant.get('personal_fixed',0),monthly_mult=variant.get('personal_mult',0),
                        paid_tax=p['tax_by_tier'][tier-1]*scale if tier else 0,
                        maa_value=p['maa_by_tier'][tier-1]*scale if tier else 0)
                    if variant.get('events'):
                        events=[]
                        if job and year%5==0:
                            events.append(dict(id=f'building-{year}',kind='building',development=20))
                        elapsed=year-person['entry'] if person['entry'] is not None else None
                        if elapsed==15 and person['cap']<6:
                            events.append(dict(id='scheduled-metropolitan',kind='metropolitan',score_factor=1,grade_factor=1,eligible=True))
                        if elapsed==25 and person['cap']<9:
                            events.append(dict(id='scheduled-palace',kind='ai_palace_followup',eligible=True))
                        parts['events']=sum(model.apply_event(person,event) for event in events)
                    return parts
                result=joint.trial(work['route'],work['seed'],cfg,years=p['years'],
                    income_step=None if variant.get('legacy') else income,
                    person_init=initialize if variant.get('native_init') else None)
                result['income_variant']=variant
                save(output,result)
                print('SAVED',work['route'],work['seed'],work['scenario'],name,flush=True)
    finally:joint.capacity.targets=original
    return work


def summarize(root,study):
    """逐年重算六关及人口账；收入另查分项守恒，不将贴目标称通过。"""
    verify(root,study);joint,model,_=study.models(root);groups={};count=0;states=0
    for work in plan()['jobs']:
        for name in work['variants']:
            row=json.loads(path_for(root,work['route'],work['seed'],work['scenario'],name).read_text())
            assert row['route']==work['route'] and row['seed']==work['seed'] and row['config']['name']==work['scenario']
            assert row['income_variant']==next(v for v in variants() if v['name']==name)
            cfg=row['config'];assert row['mechanism_errors']==0 and len(row['series'])==plan()['years']
            for field in parent.POLICY_FIELDS:assert cfg[field]==plan()[field]
            seed=row['seed']+(1000000 if row['route']=='military' else 0)
            for year,s in enumerate(row['series']):
                assert s['year']==year and sum(s['decision_n'])==sum(s['post_n'])==s['active']
                t=model.targets(s['J'],coefficients=cfg['coefficients'],phi=cfg['phi'],epsilon=cfg['epsilon'],r=cfg['r'])
                for field in ['K','target']:assert all(math.isclose(a,b,abs_tol=1e-8) for a,b in zip(s[field],t[field]))
                for i in range(6):
                    raw=model.quota_expectation(sum(s['decision_n'][i+1:]),t['B'][i],r=cfg['r'],gain=cfg['gain'])
                    assert math.isclose(raw,s['q_star'][i],abs_tol=1e-8)
                    assert s['Q'][i]==joint.pr.balanced_round(min(s['E'][i],raw),joint.pr.uniform(seed,i+1,year,82))
                for i in range(9):
                    inc=s['Q'][i-1] if 1<=i<=6 else 0;out=s['Q'][i] if i<6 else 0
                    assert s['post_n'][i]==s['decision_n'][i]+inc-out
                if name!='legacy':
                    assert math.isclose(sum(s['income_ledger'].values()),sum(g['total'] for g in s['income_groups'].values()),abs_tol=1e-7)
                states+=1
            key='/'.join([row['route'],work['scenario'],name]);groups.setdefault(key,[]).append(row);count+=1
    out={}
    for key,rows in groups.items():
        value=study.metrics(joint,rows)
        if key.endswith('/events'):
            for field in ['capable3_n','capable_reach3_40','post_capable3_n','post_capable_reach3_40']:value[field]=None
        if not key.endswith('/legacy'):
            samples=[s for row in rows for s in row['series'][-40:]]
            income={}
            for s in samples:
                for name,g in s['income_groups'].items():
                    bucket=income.setdefault(name,dict(n=0,total=0))
                    bucket['n']+=g['n'];bucket['total']+=g['total']
            value['monthly_income_by_rank_and_job']={k:v['total']/v['n']/12 for k,v in income.items() if v['n']}
            value['annual_income_components']={k:sum(s['income_ledger'][k] for s in samples)/len(samples) for k in samples[0]['income_ledger']}
        out[key]=value
    return dict(checks=dict(runs=count,annual_states=states,synthetic_not_engine=True),plan=plan(),groups=out)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',required=True,type=Path)
    parser.add_argument('--game-root',required=True,type=Path)
    parser.add_argument('--workers',type=int,default=4)
    parser.add_argument('--check-only',action='store_true')
    args=parser.parse_args();study=parent.load_study();root=study.runner.outside_repository(args.output_dir)
    prepare(root,study,args.game_root)
    if not args.check_only:
        sys.path.insert(0,str(study.ROOT))
        with ProcessPoolExecutor(max_workers=args.workers,mp_context=multiprocessing.get_context('spawn')) as pool:
            pending=[pool.submit(batch,(str(root),work)) for work in plan()['jobs']]
            for future in as_completed(pending):future.result()
    result=summarize(root,study);save(root/'income-summary.json',result)
    print(json.dumps(result['checks'],ensure_ascii=False),flush=True)


if __name__=='__main__': main()
