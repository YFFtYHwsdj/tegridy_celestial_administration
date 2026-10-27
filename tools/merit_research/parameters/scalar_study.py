"""理想累计人数反馈、功绩温度与相邻整数取整的廉价参数研究。

本文件只研究标量数学性质，不读取或修改游戏世界。固定点和轨迹假设
来源无限、无中央净流、退出比例恒定，不能替代真实资格、健康及生涯
模拟。run()只返回数据；只有显式CLI才写入仓库外的新目录。
"""
import argparse
import bisect
import hashlib
import json
import math
from pathlib import Path
import random

import math_model


VERSION = 'merit-scalar-parameter-study-v1'
SEED = 20261025
DRAWS = 100000
YEARS = 160
TARGET = 100.
EPSILON = .1
R_VALUES = [.02, .04, .06, .10, .16]
GAIN_VALUES = [.15, .35, .6, .9]
EXIT_VALUES = [.02, .04, .08]


def _first_within(errors, tolerance):
    """返回首次进入误差范围的历年；0表示初态已满足，None表示截尾。"""
    return next((year for year, error in enumerate(errors) if error <= tolerance), None)


def _trajectory(initial, equilibrium, d, r, gain, years=YEARS):
    """演算到自身固定点；同时报告对政策目标的偏离，二者不混用。"""
    point = equilibrium['S']
    states = [float(initial)]
    for _ in range(years):
        current = states[-1]
        q = math_model.quota_expectation(current, TARGET, r=r, gain=gain)
        states.append((1-d)*(current+q))
    errors = [abs(value-point) for value in states]
    assert all(after <= before+1e-9 for before, after in zip(errors, errors[1:])), '理想轨迹应单调接近自身固定点'
    signed_target = [value/TARGET-1 for value in states]
    relative_equilibrium = [error/point for error in errors]
    target_membership = [abs(error) <= .1 for error in signed_target]
    return dict(initial=states[0], initial_target_ratio=states[0]/TARGET,
                initial_side_of_equilibrium='below' if initial < point else 'above' if initial > point else 'equal',
                years_observed=years, equilibrium_relative_tolerance=.01,
                first_within_1percent_of_equilibrium_year=_first_within(relative_equilibrium, .01),
                initial_error_half_year=_first_within(errors, errors[0]*.5),
                initial_error_99percent_removed_year=_first_within(errors, errors[0]*.01),
                target_relative_tolerance=.1,
                first_target_10percent_band_year=next((year for year, inside in enumerate(target_membership) if inside), None),
                last40_target_10percent_band_fraction=sum(target_membership[-40:])/40,
                final=states[-1], final_equilibrium_relative_error=relative_equilibrium[-1],
                final_target_relative_bias=signed_target[-1], series=states)


def _closed_form(d, r, gain):
    """独立闭式交叉检查；a是所用统计时点对应的退出赔率，不是退出率。"""
    a = d/(1-d)
    if r <= a:
        ratio = (r+gain)/(a+gain)
    else:
        ratio = (gain-r+math.sqrt((r-gain)**2+4*gain*r*r/a))/(2*gain)
    return TARGET*ratio


def scalar_grid():
    """60个固定点、180条大偏差轨迹及120条局部扰动轨迹。"""
    rows = []
    for r in R_VALUES:
        for gain in GAIN_VALUES:
            for d in EXIT_VALUES:
                equilibrium = math_model.scalar_equilibrium(B=TARGET, d=d, r=r, gain=gain)
                assert math.isclose(equilibrium['S'], _closed_form(d, r, gain), rel_tol=1e-11, abs_tol=1e-9)
                assert abs(equilibrium['fixed_point_residual']) < 1e-8
                assert 0 <= equilibrium['local_multiplier'] < 1
                equilibrium.update(target_relative_bias=equilibrium['ratio']-1,
                                   nominal_K=TARGET/(1+EPSILON),
                                   ratio_to_nominal_K=(1+EPSILON)*equilibrium['ratio'],
                                   relative_excess_over_nominal_K=(1+EPSILON)*equilibrium['ratio']-1,
                                   in_target_10percent_band=abs(equilibrium['ratio']-1) <= .1)
                large = [_trajectory(scale*TARGET, equilibrium, d, r, gain) for scale in [.5, 2., 10.]]
                local = [_trajectory(scale*equilibrium['S'], equilibrium, d, r, gain) for scale in [.99, 1.01]]
                rows.append(dict(r=r, gain=gain, d=d, exit_odds=d/(1-d),
                                 equilibrium=equilibrium, large_deviation=large, local_perturbation=local))
    assert len(rows) == 60
    return rows


def _open_uniform(rng):
    """Gumbel需要开区间均匀数；罕见0重抽，不任意钳制尾部。"""
    value = rng.random()
    while value <= 0 or value >= 1:
        value = rng.random()
    return value


def temperature_grid(draws=DRAWS, seed=SEED):
    """用同一组双Gumbel噪声配对比较12组温度/功绩差，不直接抽理论概率。"""
    rng = random.Random(seed)
    gaps = []
    for _ in range(draws):
        high_noise = -math.log(-math.log(_open_uniform(rng)))
        low_noise = -math.log(-math.log(_open_uniform(rng)))
        gaps.append(low_noise-high_noise)
    gaps.sort()
    rows = []
    for temperature in [.25, .5, 1., 2.]:
        for stage_gap in [.25, .5, 1.]:
            log_weight_ratio = math.log(2)*stage_gap/temperature
            exact = 1/(1+2**(-stage_gap/temperature))
            winners = bisect.bisect_left(gaps, log_weight_ratio)
            empirical = winners/draws
            standard_error = math.sqrt(exact*(1-exact)/draws)
            within_five_se = abs(empirical-exact) <= 5*standard_error
            assert within_five_se, '配对Gumbel抽选与二人精确概率的差异超过预定五倍标准误'
            rows.append(dict(temperature=temperature, merit_gap_in_stage_differences=stage_gap,
                             log_weight_ratio=log_weight_ratio, exact_probability=exact,
                             high_merit_wins=winners, empirical_probability=empirical,
                             empirical_minus_exact=empirical-exact,
                             binomial_standard_error=standard_error,
                             within_five_standard_errors=within_five_se))
    ordered = sorted(rows, key=lambda row: row['log_weight_ratio'])
    assert all(left['high_merit_wins'] <= right['high_merit_wins'] for left, right in zip(ordered, ordered[1:]))
    return dict(seed=seed, draws=draws, paired=True, sampler='two_independent_gumbels_with_common_draws', rows=rows)


def rounding_grid(draws=DRAWS, seed=SEED+1):
    """所有q复用同一均匀数，比较精确均值、总体方差及零额度概率。"""
    rng = random.Random(seed)
    uniforms = sorted(rng.random() for _ in range(draws))
    rows = []
    for q in [.05, .25, .5, .75, 1.25, 4.5]:
        floor = math.floor(q)
        fraction = q-floor
        upper_count = bisect.bisect_left(uniforms, fraction)
        upper_fraction = upper_count/draws
        mean = floor+upper_fraction
        variance = upper_fraction*(1-upper_fraction)
        second_moment = floor*floor+(2*floor+1)*upper_fraction
        exact = math_model.rounding_moments(q)
        exact_second = exact['variance']+q*q
        standard_error = math.sqrt(exact['variance']/draws)
        within_five_se = abs(mean-q) <= 5*standard_error+1/draws
        variance_tolerance = 5*abs(1-2*fraction)*standard_error+25*exact['variance']/draws+1/draws
        assert within_five_se, '整数取整均值超出预定五倍标准误范围'
        assert abs(variance-exact['variance']) <= variance_tolerance
        rows.append(dict(q=q, theoretical={**exact, 'second_moment': exact_second},
                         empirical=dict(mean=mean, variance=variance, second_moment=second_moment,
                                        zero_probability=1-upper_fraction if floor == 0 else 0.),
                         support_counts={str(floor): draws-upper_count, str(floor+1): upper_count},
                         mean_error=mean-q, variance_error=variance-exact['variance'],
                         mean_standard_error=standard_error,
                         within_five_standard_errors=within_five_se,
                         variance_error_tolerance=variance_tolerance))
    return dict(seed=seed, draws=draws, paired=True, rows=rows)


def run():
    """只返回可序列化数据；不得因导入或调用本函数自动写文件。"""
    return dict(version=VERSION,
                source_sha256={path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                               for path in [Path(__file__), Path(math_model.__file__)]},
                assumptions=dict(ideal_scalar_only=True, infinite_candidate_supply=True,
                                 constant_exit_rate=True, no_central_or_migration_flow=True,
                                 population_clock='ordinary_inflow_then_proportional_exit',
                                 target_B=TARGET, epsilon=EPSILON,
                                 epsilon_and_k_enter_only_as_product=True,
                                 large_initial_target_multipliers=[.5, 2., 10.],
                                 local_initial_equilibrium_multipliers=[.99, 1.01],
                                 trajectory_years=YEARS,
                                 convergence_means_own_equilibrium_not_policy_target=True,
                                 missing_recovery_year_means_censored_at_horizon=True,
                                 monte_carlo_five_se_check_is_not_engine_evidence=True),
                counts=dict(equilibria=60, large_deviation_paths=180, local_paths=120,
                            temperature_cases=12, rounding_cases=6),
                scalar=scalar_grid(), temperature=temperature_grid(), rounding=rounding_grid())


def _outside_repository(path):
    """解析符号链接并查找仓库标识；冻结副本执行时也拒绝写回本模组。"""
    output = path.resolve()
    for ancestor in [output, *output.parents]:
        if (ancestor/'AGENTS.md').is_file() and (ancestor/'ARCHITECTURE.md').is_file() and (ancestor/'tools/merit_research').is_dir():
            raise ValueError('研究产物必须位于模组仓库外')
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    output = _outside_repository(args.output_dir)
    # 连空目录也不覆盖；每次CLI执行都创建新的可审计产物目录。
    output.mkdir(parents=True, exist_ok=False)
    result = run()
    (output/'scalar-results.json').write_text(json.dumps(result, ensure_ascii=False, allow_nan=False), encoding='utf-8')
    print(json.dumps(dict(output_dir=str(output), version=VERSION, counts=result['counts']), ensure_ascii=False))


if __name__ == '__main__':
    main()
