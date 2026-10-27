"""单组明示系数的定向生涯试验；逐局保存，支持中断后续跑。

复用逐参数研究，不搜索或自动挑选其他参数。源码、配置和原始结果
保存在仓库外的指定目录；check复算目标、六关额度、取整及人口守恒。
"""
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import itertools
import json
import math
import multiprocessing
from pathlib import Path
import shutil
import sys

import parameter_analysis as parent

ROOT = Path(__file__).resolve().parent


def plan(coefficients):
    """基准双种子；八种压力单种子。情景不用于优化参数。"""
    config = dict(name='requested', coefficients=coefficients, phi=[.6,.8,.5],
                  r=.06, gain=.9, epsilon=.1, temperature=.5, reserve=[0,0,0])
    names = ['baseline','entry4','longlife','loss','mortality','empty','no_middle',
             'upper_heavy','low_access']
    return dict(config=config, years=120, jobs=[dict(route=route, seed=seed, scenario=scenario)
        for route in ['civil','military']
        for scenario in names for seed in ([50,51] if scenario == 'baseline' else [50])])


def save(path, data):
    """单文件原子替换；完成局不等待其他局才落盘。"""
    temporary = path.with_suffix('.writing')
    temporary.write_text(json.dumps(data,ensure_ascii=False), encoding='utf-8')
    temporary.replace(path)


def prepare(root, study, experiment):
    """首次冻结全部依赖；续跑严格核对配置与源码。"""
    if not (root/'trial-plan.json').exists():
        study.runner.prepare(root, study.runner.selection('joint'))
        folder = root/'merit-parameter-study'; folder.mkdir()
        for source in study.ROOT.glob('*.py'): shutil.copyfile(source,folder/source.name)
        for name, target in [('calibrate_joint.py','calibrate_joint.py'),('run.py','runner_reference.py'),
                             ('parameter_trial.py','parameter_trial.py')]:
            shutil.copyfile(ROOT/name,root/target)
        save(root/'trial-plan.json', experiment)
        save(root/'trial-source.json',dict(dependencies=study.hashes(root),driver=parent.digest(__file__)))
    assert json.loads((root/'trial-plan.json').read_text()) == experiment
    study.verify(root)
    assert json.loads((root/'trial-source.json').read_text()) == dict(
        dependencies=study.hashes(root),driver=parent.digest(__file__))
    assert parent.digest(root/'parameter_trial.py') == parent.digest(__file__)


def row_path(root, job):
    return root/('trial-'+job['route']+'-'+str(job['seed'])+'-'+job['scenario']+'.json')


def audit(root, study, experiment, rows):
    """不依赖摘要判通过，逐年重新计算六道关口。"""
    prepare(root,study,experiment)
    joint,model,_ = study.models(root)
    for row,job in zip(rows,experiment['jobs']):
        assert (row['route'],row['seed'],row['config']['name']) == (job['route'],job['seed'],job['scenario'])
        cfg=row['config']; assert row['mechanism_errors']==0
        for key,value in experiment['config'].items():
            if key!='name': assert cfg[key]==value
        assert len(row['series'])==experiment['years']
        seed=row['seed']+(1000000 if row['route']=='military' else 0)
        for year,s in enumerate(row['series']):
            assert s['year']==year
            target=model.targets(s['J'],coefficients=cfg['coefficients'],phi=cfg['phi'],
                                 epsilon=cfg['epsilon'],r=cfg['r'],reserve=cfg['reserve'])
            for field,expected in [('K',target['K']),('target',target['target'])]:
                assert all(math.isclose(a,b,abs_tol=1e-8) for a,b in zip(s[field],expected))
            assert sum(s['decision_n'])==sum(s['post_n'])==s['active']
            for i in range(6):
                raw=model.quota_expectation(sum(s['decision_n'][i+1:]),target['B'][i],r=cfg['r'],gain=cfg['gain'])
                assert math.isclose(raw,s['q_star'][i],abs_tol=1e-8)
                q=min(raw,s['E'][i])
                assert s['Q'][i]==joint.pr.balanced_round(q,joint.pr.uniform(seed,i+1,year,82))
                assert 0<=s['Q'][i]<=s['E'][i]
            for i in range(9):
                incoming=s['Q'][i-1] if 1<=i<=6 else 0
                outgoing=s['Q'][i] if i<6 else 0
                assert s['post_n'][i]==s['decision_n'][i]+incoming-outgoing
    return dict(runs=len(rows),annual_states=sum(len(r['series']) for r in rows),synthetic_not_engine=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--coefficients',type=float,nargs=4,required=True)
    parser.add_argument('--output-dir',type=Path,required=True)
    parser.add_argument('--workers',type=int,default=4)
    parser.add_argument('--check-only',action='store_true')
    args=parser.parse_args()
    assert all(math.isfinite(k) and k>0 for k in args.coefficients)
    study=parent.load_study(); root=study.runner.outside_repository(args.output_dir)
    experiment=plan(args.coefficients); prepare(root,study,experiment)
    scenarios={s['name']:s for s in study.VALIDATE}
    missing=[job for job in experiment['jobs'] if not row_path(root,job).exists()]
    if args.check_only and missing: raise ValueError('仍有未完成情景')
    if missing:
        sys.path.insert(0,str(study.ROOT))
        with ProcessPoolExecutor(max_workers=args.workers,mp_context=multiprocessing.get_context('spawn')) as pool:
            pending={pool.submit(study.batch,(str(root),job['route'],job['seed'],
                scenarios[job['scenario']],[experiment['config']],experiment['years'])):job for job in missing}
            for future in as_completed(pending):
                job=pending[future]; result=future.result()
                save(row_path(root,job),result['runs'][0])
                print('SAVED',job,flush=True)
    rows=[json.loads(row_path(root,job).read_text()) for job in experiment['jobs']]
    checked=audit(root,study,experiment,rows)
    save(root/'trial-summary.json',dict(plan=experiment,checks=checked,groups=study.summarize(root,rows)))
    print(json.dumps(checked,ensure_ascii=False),flush=True)


if __name__=='__main__': main()
