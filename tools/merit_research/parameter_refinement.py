"""逐带员额的四组明示交互补充；不改写此前冻结阶段。

本轮补齐五四带来源储备与最高带目标的交互，不改变逐带K=kJ、
资格、功绩或健康模型。独立冻结本驱动，继续使用已封存的父研究
源码与逐人生涯计算；跟踪最低只用于选择留出对象，不宣称福利最优。
"""
import argparse
import copy
from concurrent.futures import ProcessPoolExecutor
import hashlib
import itertools
import json
import math
import multiprocessing
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parent
PARAMETERS = ROOT/'parameters'
sys.path.insert(0, str(PARAMETERS))
import parameter_analysis as parent

FROZEN_NAME = 'parameter_refinement.py'
MANIFEST_NAME = 'refinement-source.json'
VERSION = 'direct-band-refinement-v1'
ROUTES = ['civil', 'military']


def configurations():
    """只列四项明确组合；所有参数文武共享，均不启用隐藏储备。"""
    base = dict(coefficients=[1.5,4,4,1], phi=[.6,.8,.5], r=.06, gain=.9,
                epsilon=.1, temperature=.5, reserve=[0,0,0],
                factor='explicit_refinement', value=None)
    changes = [('A', {}), ('B', dict(coefficients=[1.5,4,6,1])),
               ('C', dict(phi=[.6,.7,.6], gain=.6)),
               ('D', dict(coefficients=[1.5,2,4,1], phi=[.6,.7,.6], gain=.6))]
    return [dict(copy.deepcopy(base), **copy.deepcopy(change), name='refinement-'+name)
            for name, change in changes]


def _parameter_path_first():
    """models会将joint放到首位；每次spawn前恢复正确的study导入目录。"""
    folder = str(PARAMETERS)
    sys.path[:] = [folder] + [item for item in sys.path if item != folder]


def _source(root, study):
    """本驱动与父源码分别封存；旧结果摘要只读，不重签旧证据。"""
    study.verify(root)
    selector = parent.selector_manifest(root, required=True)
    interaction = root/'interaction-results.json'
    assert selector['completed_results'].get('interaction') == parent.digest(interaction)
    interaction_data = json.loads(interaction.read_text())
    assert interaction_data['source_sha256'] == study.hashes(root)
    return dict(refinement_sha256=parent.digest(__file__),
                parent_analysis_sha256=parent.digest(parent.__file__),
                parent_source_sha256=study.hashes(root),
                parent_interaction_result_sha256=parent.digest(interaction))


def manifest(root, study, create=False):
    """核对三层来源及已完成结果；仅本轮完成记录允许追加。"""
    source = _source(root, study)
    path = root/MANIFEST_NAME
    frozen = root/FROZEN_NAME
    if not path.exists():
        if not create:
            raise ValueError('缺少本轮独立来源记录')
        if frozen.exists():
            raise ValueError('已存在孤立驱动副本，拒绝覆盖')
        frozen.write_bytes(Path(__file__).read_bytes())
        data = dict(version=VERSION, source=source, configurations=configurations(), completed_results={})
        with path.open('x', encoding='utf-8') as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
    else:
        data = json.loads(path.read_text())
        assert data['source'] == source, '本轮驱动或父源码/交互结果变化，拒绝沿用'
        assert data['configurations'] == configurations()
    assert parent.digest(frozen) == source['refinement_sha256']
    for phase, digest in data['completed_results'].items():
        assert digest == parent.digest(root/f'refinement-{phase}-results.json')
    return data


def _close(a, b, label):
    if not math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-8):
        raise AssertionError(label)


def check(root, study=None):
    """逐阶段核对精确身份集合、来源、目标、期望额度和实际人口流。"""
    study = study or parent.load_study()
    root = study.runner.outside_repository(Path(root))
    source = manifest(root, study)
    joint, model, _ = study.models(root)
    counts = {}; annual_states = 0
    try:
        for phase, seeds, scenarios, years in [('pilot', [46,47], [dict(name='baseline')], 80),
                                              ('validation', [48,49], study.VALIDATE, 120)]:
            path = root/f'refinement-{phase}-results.json'
            if not path.exists():
                continue
            data = json.loads(path.read_text())
            assert source['completed_results'].get(phase) == parent.digest(path)
            assert data['source'] == source['source']
            assert data['seeds'] == seeds and data['scenarios'] == scenarios and data['years'] == years
            if phase == 'pilot':
                configs = configurations()
            else:
                pilot = json.loads((root/'refinement-pilot-results.json').read_text())
                configs = [pilot['ranking'][0]['config']]
            assert data['configs'] == configs
            planned_configs = {c['name']: c for c in configs}
            planned_scenarios = {s['name']: s for s in scenarios}
            expected = set(itertools.product(ROUTES, seeds, planned_scenarios, planned_configs))
            identities = [(row['route'], row['seed'], row['config']['name'], row['config']['policy'])
                          for row in data['runs']]
            assert len(identities) == len(set(identities)) and set(identities) == expected
            for row in data['runs']:
                cfg = row['config']
                planned = {**planned_configs[cfg['policy']], **planned_scenarios[cfg['name']]}
                for field in parent.POLICY_FIELDS:
                    assert cfg[field] == planned[field], field
                assert row['mechanism_errors'] == 0
                assert row['years'] == years == len(row['series'])
                assert [state['year'] for state in row['series']] == list(range(years))
                seed = row['seed'] + (1000000 if row['route'] == 'military' else 0)
                for state in row['series']:
                    assert len(state['decision_n']) == len(state['post_n']) == 9
                    assert len(state['J']) == len(state['K']) == 4 and len(state['target']) == 7
                    assert len(state['E']) == len(state['Q']) == len(state['q_star']) == 6
                    target = model.targets(state['J'], r=cfg['r'], epsilon=cfg['epsilon'],
                                           coefficients=cfg['coefficients'], phi=cfg['phi'], reserve=cfg['reserve'])
                    for actual, goal in zip(state['K'], target['K']):
                        _close(actual, goal, '逐带员额不符')
                    for actual, goal in zip(state['target'], target['target']):
                        _close(actual, goal, '逐品目标不符')
                    assert sum(state['decision_n']) == sum(state['post_n']) == state['active']
                    assert all(isinstance(n, int) and not isinstance(n, bool) and n >= 0
                               for n in state['decision_n'] + state['post_n'])
                    for i in range(6):
                        raw = model.quota_expectation(sum(state['decision_n'][i+1:]), target['B'][i],
                                                      r=cfg['r'], gain=cfg['gain'])
                        _close(state['q_star'][i], raw, '原始期望额度不符')
                        E, Q = state['E'][i], state['Q'][i]
                        assert isinstance(E, int) and not isinstance(E, bool) and E >= 0
                        assert isinstance(Q, int) and not isinstance(Q, bool) and 0 <= Q <= E
                        q = min(E, raw)
                        assert math.floor(q) <= Q <= math.ceil(q)
                        assert Q == min(E, joint.pr.balanced_round(q, joint.pr.uniform(seed, i+1, state['year'], 82)))
                    for i in range(9):
                        incoming = state['Q'][i-1] if 1 <= i <= 6 else 0
                        outgoing = state['Q'][i] if i < 6 else 0
                        assert state['post_n'][i] == state['decision_n'][i]+incoming-outgoing
                    annual_states += 1
            assert data['ranking'] == study.diagnostic_rank(study.summarize(root, data['runs']), configs)
            counts[phase] = len(expected)
    finally:
        _parameter_path_first()
    assert counts, '没有已完成的补充研究阶段'
    return dict(phases=counts, annual_states_checked=annual_states, not_engine_evidence=True)


def execute(phase, root, workers):
    """先导16次，随后只对跟踪最低的一组做64次独立情景验证。"""
    study = parent.load_study()
    root = study.runner.outside_repository(Path(root))
    output = root/f'refinement-{phase}-results.json'
    summary = root/f'refinement-{phase}-summary.json'
    if output.exists() or summary.exists():
        raise ValueError('拒绝覆盖本轮已有结果或摘要')
    record = manifest(root, study, create=phase == 'pilot')
    if phase == 'pilot':
        configs, seeds, scenarios, years = configurations(), [46,47], [dict(name='baseline')], 80
    else:
        pilot_path = root/'refinement-pilot-results.json'
        assert record['completed_results'].get('pilot') == parent.digest(pilot_path)
        pilot = json.loads(pilot_path.read_text())
        configs, seeds, scenarios, years = [pilot['ranking'][0]['config']], [48,49], study.VALIDATE, 120
    jobs = [(str(root), route, seed, scenario, configs, years)
            for route in ROUTES for seed in seeds for scenario in scenarios]
    # 任何前置核验/摘要都可能将joint加到首位，spawn前必须重新排序。
    _parameter_path_first()
    rows, cache = [], []
    with ProcessPoolExecutor(max_workers=workers, mp_context=multiprocessing.get_context('spawn')) as pool:
        for result in pool.map(study.batch, jobs):
            rows.extend(result['runs']); cache.append(result['cache'])
    groups = study.summarize(root, rows)
    ranking = study.diagnostic_rank(groups, configs)
    data = dict(version=VERSION, phase=phase, source=record['source'], configs=configs,
                seeds=seeds, scenarios=scenarios, years=years, runs=rows, groups=groups,
                ranking=ranking, cache_stats=cache,
                assumptions=dict(shared_parameters=True, direct_band_no_hidden_reserve=True,
                                 explicit_top_target_and_middle_supply_interaction=True,
                                 selection='最低平均带与尾部跟踪误差；预算/队列代价完整保留，不称福利最优',
                                 synthetic_not_engine=True))
    assert manifest(root, study)['source'] == record['source']
    with output.open('x', encoding='utf-8') as handle:
        json.dump(data, handle, ensure_ascii=False)
    with summary.open('x', encoding='utf-8') as handle:
        json.dump({k: v for k, v in data.items() if k != 'runs'}, handle, ensure_ascii=False, indent=2)
    record['completed_results'][phase] = parent.digest(output)
    (root/MANIFEST_NAME).write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
    print('DONE', phase, len(rows), json.dumps(check(root, study), ensure_ascii=False), flush=True)


def self_test():
    """只验证四组配置与spawn导入，不启动长生涯或写产物。"""
    study = parent.load_study()
    configs = configurations()
    assert [c['name'] for c in configs] == ['refinement-A','refinement-B','refinement-C','refinement-D']
    assert [c['coefficients'] for c in configs] == [[1.5,4,4,1],[1.5,4,6,1],[1.5,4,4,1],[1.5,2,4,1]]
    assert [c['phi'] for c in configs] == [[.6,.8,.5],[.6,.8,.5],[.6,.7,.6],[.6,.7,.6]]
    assert [c['gain'] for c in configs] == [.9,.9,.6,.6]
    assert all(c['temperature'] == .5 and c['epsilon'] == .1 and c['reserve'] == [0,0,0] for c in configs)
    _parameter_path_first()
    with ProcessPoolExecutor(max_workers=1, mp_context=multiprocessing.get_context('spawn')) as pool:
        module = pool.submit(getattr, study.batch, '__module__').result(timeout=30)
        anchor = pool.submit(study.sweeps).result(timeout=30)[0]
    assert module == 'study' and anchor['name'] == 'anchor'
    return dict(configurations=4, pilot_runs=16, validation_runs=64, spawn_importable=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=['pilot','validation','check','self-test'])
    parser.add_argument('--output-dir', type=Path)
    parser.add_argument('--workers', type=int, default=4)
    args = parser.parse_args()
    if args.phase == 'self-test':
        print(json.dumps(self_test(), ensure_ascii=False)); return
    if args.output_dir is None:
        parser.error('该阶段需要--output-dir')
    if args.phase == 'check':
        print(json.dumps(check(args.output_dir), ensure_ascii=False)); return
    execute(args.phase, args.output_dir, args.workers)


if __name__ == '__main__':
    main()
