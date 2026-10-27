"""冻结参数研究的独立只读审计与自适应交互选择器。

不修改parameters/及旧sweep的摘要。交互仅替换原编排器的候选选择函数，
本文件另行冻结并记录来源；政策结果仍由原joint逐人生涯计算。
"""
import argparse
import copy
from concurrent.futures import ProcessPoolExecutor
import hashlib
import importlib
import itertools
import json
import math
import multiprocessing
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parent
FROZEN_NAME = 'parameter_analysis.py'
MANIFEST_NAME = 'parameter-selector.json'
POLICY_FIELDS = ('coefficients', 'phi', 'r', 'gain', 'epsilon', 'temperature', 'reserve')


def digest(path):
    """按实际字节封存；不重签旧阶段结果。"""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_study():
    """用spawn可再次导入的标准模块名加载，并拒绝同名研究模块污染。"""
    path = ROOT / 'parameters/study.py'
    present = sys.modules.get('study')
    if present is not None:
        loaded = getattr(present, '__file__', None)
        if loaded is None or Path(loaded).resolve() != path.resolve():
            raise RuntimeError('已有同名study模块来自其他研究；请在独立进程运行选择器')
        return present
    # multiprocessing的spawn准备数据会携带sys.path；子进程因此能按
    # 标准模块名重新找到batch，而不依赖仅父进程持有的动态模块对象。
    folder = str(path.parent)
    if folder not in sys.path:
        sys.path.insert(0, folder)
    module = importlib.import_module('study')
    if Path(module.__file__).resolve() != path.resolve():
        raise RuntimeError('study解析到了其他研究目录，拒绝混用')
    return module


def _score(group):
    return (group['band_tracking'] + group['tail_tracking']) / 2


def selection_plan(sweep):
    """保留单因素实际方向和必要回退；不是各因素最低分的盲目拼装。

    .002是本轮聚合跟踪误差的最小选择差，不是显著性阈值。k<1仅作
    诊断，不用于候选；缩小最高带目标与补足高品来源分开讨论。
    温度只作预先指定的邻近对照，不能凭微小跟踪收益定稿。
    """
    ranked = sweep['ranking']
    anchor_row = next(x for x in ranked if x['config'].get('factor') == 'anchor')
    anchor = copy.deepcopy(anchor_row['config'])
    anchor_score = anchor_row['tracking']
    decisions = []

    def pick(factor):
        rows = [x for x in ranked if x['config'].get('factor') == factor]
        if factor in ('common_k', 'k2', 'k3', 'k4'):
            rows = [x for x in rows if all(k >= 1 for k in x['config']['coefficients'])]
        best = min(rows, key=lambda x: x['tracking']) if rows else None
        useful = best is not None and best['tracking'] < anchor_score - .002
        decisions.append(dict(factor=factor, chosen=best['config']['name'] if useful else 'anchor',
                              best_observed=best['config']['name'] if best else None,
                              improvement=anchor_score-best['tracking'] if best else None,
                              reason='跟踪改善超过.002' if useful else '改善不足，保留锚点'))
        return copy.deepcopy(best['config']) if useful else copy.deepcopy(anchor)

    winners = {factor: pick(factor) for factor in ('k2','k3','k4','phi2','phi3','r','gain')}
    combined = copy.deepcopy(anchor)
    for index, factor in enumerate(('k2','k3','k4'), 1):
        candidate = winners[factor]['coefficients'][index]
        if factor == 'k4' and candidate < anchor['coefficients'][index]:
            decisions.append(dict(factor='k4', chosen='anchor', alternative=candidate,
                                  reason='缩小最高带目标不是改善来源；只列独立对照'))
        else:
            combined['coefficients'][index] = candidate
    for index, factor in ((1,'phi2'),(2,'phi3')):
        combined['phi'][index] = winners[factor]['phi'][index]
    for field in ('r','gain'):
        combined[field] = winners[field][field]
    # 第一带k与phi不可分别辨识；不把共同k扫描胜者自动覆盖到主组合。
    combined['phi'][0] = anchor['phi'][0]
    combined['temperature'] = anchor['temperature']

    configs, reasons, aliases, signatures = [], {}, {}, {}

    def add(name, base, reason, **changes):
        config = copy.deepcopy(base)
        config.update(copy.deepcopy(changes))
        config.update(name=name, factor='adaptive_interaction', value=None)
        signature = json.dumps({k:config[k] for k in POLICY_FIELDS}, sort_keys=True)
        if signature in signatures:
            aliases[name] = dict(same_as=signatures[signature], reason=reason)
            return
        if any(k < 1 for k in config['coefficients']):
            raise AssertionError('交互候选不得以k<1缩目标冒充供给改善')
        signatures[signature] = name
        configs.append(config)
        reasons[name] = reason

    add('reference-anchor', anchor, '保留原逐带1.5、四六、r=.06、gain=.6锚点')
    common = [x for x in ranked if x['config'].get('factor') == 'common_k'
              and min(x['config']['coefficients']) >= 1]
    low = min(common, key=lambda x:x['tracking'])['config'] if common else anchor
    add('reference-uniform', low, '共同k候选限制>=1；只是较低目标参考，不称补足来源')
    first = anchor['coefficients'][0]
    add('reference-tiered', anchor, '保留旧中等逐带参考',
        coefficients=[first,2,4,1.5], phi=[.6,.7,.7])
    add('reference-wide', anchor, '保留旧高储备参考并公开其预算代价',
        coefficients=[first,4,8,1.5], phi=[.6,.7,.8], r=.04, gain=.35)
    add('adaptive-combined', combined, '合入超过选择差的OAT方向；固定第一带解释与默认温度')
    add('adaptive-backoff-turnover', combined, '同一组合回退r/gain，识别周转恢复的交互',
        r=anchor['r'], gain=anchor['gain'])
    add('adaptive-backoff-phi', combined, '同一组合回退三个phi', phi=anchor['phi'])
    add('adaptive-backoff-coefficients', combined, '同一组合回退四带系数', coefficients=anchor['coefficients'])
    for value in (2,4):
        ks=combined['coefficients'][:];ks[2]=value
        add('adaptive-k3-'+str(value), combined, '保留中等五四带梯队，避免直接把8当最优', coefficients=ks)
    k4 = winners['k4']['coefficients'][3]
    ks=combined['coefficients'][:];ks[3]=k4
    add('adaptive-k4-alternative', combined, '最高带目标调整独立对照，不当作来源改善', coefficients=ks)
    ks=combined['coefficients'][:];ks[0]=2.5;ks[2]=4
    add('adaptive-pipeline-combined', combined,
        '第一带通量与五四带储备联合提高；与两项单改构成互补作用对照', coefficients=ks)
    temperatures = [x['config']['temperature'] for x in ranked
                    if x['config'].get('factor') == 'temperature'
                    and x['config']['temperature'] < anchor['temperature']]
    if temperatures:
        tau=max(temperatures)
        add('adaptive-temperature-neighbor', combined,
            '预先取最近较低温度加强Merit倾向，仅与默认温度配对，不按跟踪排名定温度', temperature=tau)
    ks=combined['coefficients'][:];ks[0]=2.5
    add('adaptive-k1-2.5', combined, '与主组合k1=1.5成对，单独检验八品目标及九品等待', coefficients=ks)
    add('adaptive-coefficients-only', anchor, '只合入系数方向，与组合分离', coefficients=combined['coefficients'])
    add('adaptive-phi-only', anchor, '只合入分品方向，与组合分离', phi=combined['phi'])
    assert len(configs) <= 16
    return dict(configs=configs, reasons=reasons, aliases=aliases, decisions=decisions,
                assumptions=dict(minimum_tracking_improvement=.002, k_minimum=1,
                                 epsilon_is_convention=True, phi1_is_convention=True,
                                 temperature_not_selected_by_tracking=True,
                                 comparison_is_not_welfare_optimum=True))


def adaptive_interactions(sweep):
    return selection_plan(sweep)['configs']


def _close(actual, expected, label):
    if not math.isclose(actual, expected, rel_tol=1e-9, abs_tol=1e-8):
        raise AssertionError(f'{label}不符：{actual} != {expected}')


def _recovery(series, start, strict=False):
    """首次15年窗口及窗口之后再偏离；没有后续观察不称永久恢复。"""
    def fits(s):
        for i in range(6):
            B=sum(s['target'][i+1:]);S=sum(s['decision_n'][i+1:])
            tolerance=.25*B if strict else max(2,.25*B)
            if abs(S-B)>tolerance+1e-9:
                return False
        return True
    first=None
    for index in range(start,len(series)-14):
        if all(fits(s) for s in series[index:index+15]):
            first=index;break
    later=series[first+15:] if first is not None else []
    return dict(first15_years=first-start if first is not None else None,
                subsequent_years=len(later),
                subsequent_departure_share=sum(not fits(s) for s in later)/len(later) if later else None,
                permanent_recovery_not_proven=True)


def full_shock_metrics(row):
    """面积覆盖冲击当年至结束，区别编排器原来的末40年面积。"""
    if not row['config'].get('shock'):
        return None
    series=row['series'];start=60;states=series[start:]
    excess=[sum(max(0,sum(s['decision_n'][i+1:])-sum(s['target'][i+1:])) for s in states) for i in range(6)]
    deficit=[sum(max(0,sum(s['target'][i+1:])-sum(s['decision_n'][i+1:])) for s in states) for i in range(6)]
    small=[s for s in states if 0<s['target'][6]<2]
    zeros=sum(sum(s['decision_n'][6:])==0 for s in small)
    return dict(route=row['route'],seed=row['seed'],scenario=row['config']['name'],policy=row['config']['policy'],
                window=[start,len(series)-1],tail_excess_person_years=excess,
                tail_deficit_person_years=deficit,
                original_tolerance=_recovery(series,start),
                strictly_relative_tolerance=_recovery(series,start,strict=True),
                small_top_target_years=len(small),small_top_zero_years=zeros,
                small_top_zero_share=zeros/len(small) if small else None,
                central_is_persistent_input=row['config'].get('shock')=='central')


def selector_manifest(root, required=False):
    """选择器版本单独核验，不改写原研究source_sha256。"""
    path=root/MANIFEST_NAME
    if not path.exists():
        if required:raise ValueError('缺少独立选择器来源记录')
        return None
    data=json.loads(path.read_text())
    assert digest(__file__)==data['selector_sha256']==digest(root/FROZEN_NAME)
    assert digest(root/'sweep-results.json')==data['sweep_result_sha256']
    return data


def audit(root, study=None):
    """只读重算实际轨迹与完整组合，不以摘要条数替代逐年审计。"""
    study=study or load_study();root=study.runner.outside_repository(Path(root))
    study.verify(root);joint,model,_=study.models(root)
    manifest=selector_manifest(root)
    counts={};states_checked=0;shock=[]
    for phase in ('sweep','interaction','validation'):
        path=root/(phase+'-results.json')
        if not path.exists():continue
        data=json.loads(path.read_text())
        assert data['source_sha256']==study.hashes(root)
        assert len({c['name'] for c in data['configs']})==len(data['configs'])
        assert len({s['name'] for s in data['scenarios']})==len(data['scenarios'])
        assert len(set(data['seeds']))==len(data['seeds'])
        expected=set(itertools.product(('civil','military'),data['seeds'],
                     [s['name'] for s in data['scenarios']],[c['name'] for c in data['configs']]))
        identities=[(r['route'],r['seed'],r['config']['name'],r['config']['policy']) for r in data['runs']]
        assert len(identities)==len(set(identities)) and set(identities)==expected
        configs={c['name']:c for c in data['configs']}
        scenarios={s['name']:s for s in data['scenarios']}
        if manifest and phase in ('interaction','validation'):
            assert manifest['completed_results'].get(phase)==digest(path), '选择器阶段缺成功封存或结果已变化'
            if phase=='interaction':assert data['configs']==manifest['selection']['configs']
        for row in data['runs']:
            cfg=row['config'];planned={**configs[cfg['policy']],**scenarios[cfg['name']]}
            for field in POLICY_FIELDS:assert cfg[field]==planned[field],field
            assert row['mechanism_errors']==0
            assert row['years']==data['years']==len(row['series'])
            assert [s['year'] for s in row['series']]==list(range(data['years']))
            sk=row['seed']+(1000000 if row['route']=='military' else 0)
            for s in row['series']:
                assert len(s['decision_n'])==len(s['post_n'])==9
                assert len(s['J'])==len(s['K'])==4 and len(s['target'])==7
                assert len(s['E'])==len(s['Q'])==len(s['q_star'])==6
                target=model.targets(s['J'],r=cfg['r'],epsilon=cfg['epsilon'],
                                     coefficients=cfg['coefficients'],phi=cfg['phi'],reserve=cfg['reserve'])
                for actual,value in zip(s['K'],target['K']):_close(actual,value,'K')
                for actual,value in zip(s['target'],target['target']):_close(actual,value,'逐品目标')
                assert sum(s['decision_n'])==sum(s['post_n'])==s['active']
                assert all(isinstance(n,int) and not isinstance(n,bool) and n>=0 for n in s['decision_n']+s['post_n'])
                for i in range(6):
                    B=target['B'][i];S=sum(s['decision_n'][i+1:])
                    raw=model.quota_expectation(S,B,r=cfg['r'],gain=cfg['gain'])
                    _close(s['q_star'][i],raw,'原始期望额度')
                    E=s['E'][i];Q=s['Q'][i]
                    assert isinstance(E,int) and not isinstance(E,bool) and E>=0
                    assert isinstance(Q,int) and not isinstance(Q,bool)
                    q=min(E,s['q_star'][i])
                    assert 0<=Q<=E and math.floor(q)<=Q<=math.ceil(q)
                    expected_Q=min(E,joint.pr.balanced_round(q,joint.pr.uniform(sk,i+1,s['year'],82)))
                    assert Q==expected_Q,'相邻随机取整与固定随机命名空间不符'
                for i in range(9):
                    incoming=s['Q'][i-1] if 1<=i<=6 else 0
                    outgoing=s['Q'][i] if i<6 else 0
                    assert s['post_n'][i]==s['decision_n'][i]+incoming-outgoing
                states_checked+=1
            extra=full_shock_metrics(row)
            if extra:shock.append(extra)
        counts[phase]=len(expected)
    assert counts,'没有完成的参数研究阶段'
    return dict(phases=counts,annual_states_checked=states_checked,
                audit_selector_sha256=digest(__file__),
                adaptive_selector_present=manifest is not None,
                full_shock_metrics=shock,not_engine_evidence=True)


def execute(phase,root,workers):
    """原编排器继续消费旧冻结结果；仅interaction候选选择被显式替换。"""
    study=load_study();root=study.runner.outside_repository(Path(root));study.verify(root)
    if phase=='interaction':
        sweep_path=root/'sweep-results.json';sweep=json.loads(sweep_path.read_text())
        assert sweep['source_sha256']==study.hashes(root)
        if (root/'interaction-results.json').exists():raise ValueError('拒绝覆盖已有交互阶段')
        manifest=selector_manifest(root)
        if manifest is None:
            frozen=root/FROZEN_NAME
            if frozen.exists():raise ValueError('已存在孤立选择器副本，拒绝覆盖')
            shutil.copyfile(__file__,frozen)
            manifest=dict(selector_sha256=digest(__file__),sweep_result_sha256=digest(sweep_path),
                          original_source_sha256=sweep['source_sha256'],selection=selection_plan(sweep),
                          completed_results={})
            (root/MANIFEST_NAME).write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
        else:assert manifest['selection']==selection_plan(sweep)
        study.interactions=adaptive_interactions
        print(json.dumps(manifest['selection'],ensure_ascii=False,indent=2),flush=True)
    else:
        manifest=selector_manifest(root,required=True)
        assert manifest['completed_results'].get('interaction')==digest(root/'interaction-results.json')
    argv=sys.argv[:]
    try:
        sys.argv=[str(ROOT/'parameters/study.py'),phase,'--output-dir',str(root),'--workers',str(workers)]
        study.main()
    finally:sys.argv=argv
    manifest['completed_results'][phase]=digest(root/(phase+'-results.json'))
    (root/MANIFEST_NAME).write_text(json.dumps(manifest,ensure_ascii=False,indent=2))


def self_test():
    """小型合成检查；不运行长生涯、不写研究结果。"""
    study=load_study();configs=study.sweeps();ranking=[]
    # 显式spawn而非平台默认fork；这里只传递同模块的小函数，不跑生涯。
    # 它与batch共享模块名，能暴露“父进程可调用、子进程不可导入”的故障。
    context=multiprocessing.get_context('spawn')
    with ProcessPoolExecutor(max_workers=1,mp_context=context) as pool:
        from_child=pool.submit(study.sweeps).result(timeout=30)
        batch_module=pool.submit(getattr,study.batch,'__module__').result(timeout=30)
    assert from_child==configs
    assert batch_module=='study'
    for c in configs:
        score=.3
        if c['factor']=='anchor':score=.2
        if c['factor']=='k2' and c['value']==4:score=.17
        if c['factor']=='k4' and c['value']==1:score=.16
        if c['factor']=='phi3' and c['value']==.5:score=.19
        if c['factor']=='temperature':score=.01
        ranking.append(dict(config=c,tracking=score))
    plan=selection_plan(dict(ranking=sorted(ranking,key=lambda x:x['tracking'])))
    assert len(plan['configs'])<=16
    combined=next(c for c in plan['configs'] if c['name']=='adaptive-combined')
    assert combined['coefficients']==[1.5,4,1.5,1.5]
    assert combined['phi']==[.6,.6,.5] and combined['temperature']==.5
    assert any(c['coefficients'][0]==2.5 for c in plan['configs'])
    assert all(min(c['coefficients'])>=1 for c in plan['configs'])
    # 小池长期为0会被原绝对容差接受；严格相对容差必须拒绝。
    series=[dict(target=[0]*6+[1],decision_n=[0]*9) for _ in range(100)]
    assert _recovery(series,60)['first15_years']==0
    assert _recovery(series,60,strict=True)['first15_years'] is None
    # 首次15年后再偏离不能被窗口内的合格年份稀释。
    series=[dict(target=[0]*6+[4],decision_n=[0]*6+[4,0,0]) for _ in range(80)]
    series.extend(dict(target=[0]*6+[4],decision_n=[0]*9) for _ in range(5))
    result=_recovery(series,60)
    assert result['first15_years']==0 and result['subsequent_years']==10
    assert result['subsequent_departure_share']==.5
    return dict(selection_configs=len(plan['configs']),spawn_importable=True,status='通过')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase',choices=['self-test','audit','interaction','validation','plan'])
    parser.add_argument('--output-dir',type=Path)
    parser.add_argument('--workers',type=int,default=4)
    parser.add_argument('--report',type=Path,help='可选的新建仓库外审计报告，不覆盖旧报告')
    args=parser.parse_args()
    if args.phase=='self-test':print(json.dumps(self_test(),ensure_ascii=False));return
    if args.output_dir is None:parser.error('该阶段需要--output-dir')
    study=load_study();root=study.runner.outside_repository(args.output_dir)
    if args.phase=='plan':
        study.verify(root)
        sweep=json.loads((root/'sweep-results.json').read_text())
        assert sweep['source_sha256']==study.hashes(root)
        print(json.dumps(selection_plan(sweep),ensure_ascii=False,indent=2));return
    if args.phase=='audit':
        result=audit(root,study)
        if args.report:
            report=study.runner.outside_repository(args.report)
            if report.exists():raise ValueError('拒绝覆盖旧审计报告')
            report.write_text(json.dumps(result,ensure_ascii=False,indent=2))
        print(json.dumps(result,ensure_ascii=False));return
    execute(args.phase,root,args.workers)


if __name__=='__main__':
    main()
