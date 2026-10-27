"""审计候选槽→员额映射；输出自身目录mapping-audit.json，不运行游戏。

通常由研究运行器将三份源码按字节复制到仓库外，再在冻结目录运行，避免运行产物入库。
两路线的三种等总槽结构及边界J完全人工构造，不使用旧探针516作独立槽实测。
"""
from hashlib import sha256
from pathlib import Path
import json
import math
from capacity import MAPPINGS,targets

CASES=(
    ('civil','lower_heavy',[90,24,5,1]),
    ('civil','balanced',[45,45,24,6]),
    ('civil','upper_heavy',[15,25,40,40]),
    ('military','lower_heavy',[22,5,2,1]),
    ('military','balanced',[12,10,6,2]),
    ('military','upper_heavy',[3,5,10,12]),
    ('boundary','zero_middle',[20,0,0,4]),
    ('boundary','only_upper',[0,0,0,4]),
    ('boundary','all_zero',[0,0,0,0]),
    ('boundary','small_realm',[1,0,1,1]),
    ('boundary','no_top',[10,2,1,0]),
    ('boundary','only_lower',[10,0,0,0]),
)
R=.04/.96
CANDIDATE_FRACTION=.25
EPSILON=.1


def _same_total(out,total):
    """仅诊断比例形状：按统一2J的总量同比缩放，不是新增正式映射。

    同比缩放保留required_candidate_fraction与供给标记，但可能低于该映射原始2J基数；
    因此不能把这个对照冒充实际transit2的输出或声称保留原始储备下限。
    """
    current=sum(out['K']);factor=total/current if current else 1.
    return {'kind':'仅审计的等总量形状对照，不作为targets映射',
            'reference_total_K':total,'scale':factor,
            **{key:[v*factor for v in out[key]] for key in ('K','T','target','B','reserve')},
            'required_candidate_fraction':out['required_candidate_fraction'],
            'feasible_at_candidate_fraction':out['feasible_at_candidate_fraction'],
            'warning':'同比缩放后不保证仍大于原始头衔基数，不能称保留2J基准'}


def _audit_result(out):
    """用带/品/尾部恒等式核对输出；不重写映射公式。"""
    check=0
    assert len(out['K'])==4 and len(out['T'])==4 and len(out['target'])==7 and len(out['B'])==6;check+=1
    assert math.isclose(sum(out['target']),sum(out['T']),rel_tol=1e-12,abs_tol=1e-12);check+=1
    for b in range(3):
        assert math.isclose(sum(out['target'][2*b:2*b+2]),out['T'][b],rel_tol=1e-12,abs_tol=1e-12)
        assert math.isclose(out['target'][2*b+1],.6*out['T'][b],rel_tol=1e-12,abs_tol=1e-12);check+=2
    assert out['target'][6]==out['T'][3];check+=1
    for i in range(6):
        assert math.isclose(out['B'][i],sum(out['target'][i+1:]),rel_tol=1e-12,abs_tol=1e-12);check+=1
    assert all(v>=0 for v in out['reserve']);check+=1
    if out['mapping']=='transit2':
        assert out['feasible_at_candidate_fraction'];check+=1
    return check


def main():
    """封存三份源码摘要与全部人工条件，写入本次运行目录。"""
    root=Path(__file__).resolve().parent
    sources={name:sha256((root/name).read_bytes()).hexdigest() for name in ('capacity.py','capacity_checks.py','mapping_audit.py')}
    rows=[];count=0
    for route,structure,J in CASES:
        mappings={};controls={}
        for name in MAPPINGS:
            out=targets(J,name,r=R,candidate_fraction=CANDIDATE_FRACTION,epsilon=EPSILON)
            count+=_audit_result(out);mappings[name]=out
            controls[name]=_same_total(out,2*sum(J))
            assert math.isclose(sum(controls[name]['K']),2*sum(J),rel_tol=1e-12,abs_tol=1e-12);count+=1
        rows.append({'route_label':route,'structure':structure,'J':J,'total_J':sum(J),
                     'mapping_outputs':mappings,'equal_total_controls':controls})
    for route in ('civil','military'):
        assert len({sum(j) for r,_,j in CASES if r==route})==1;count+=1
    result={'version':'capacity-mapping-audit-v1','kind':'纯数学人工结构审计，非原版岗位统计或游戏验收',
            'source_sha256':sources,
            'assumptions':{'r':R,'candidate_fraction':CANDIDATE_FRACTION,'epsilon':EPSILON,'phi':.6,
                           'highest_state':'三二一品合计，不指定内部比例','J':'完全人工；每个独立槽只计一个带',
                           'civil_total_J':120,'military_total_J':30,
                           'input_warning':'两路线规模与结构均非实测；未使用旧需求快照516推定J',
                           'feasibility_warning':'只核对必要供给条件，未校准真实资格/增长/死亡/任命过程',
                           'reserve_meaning':'相对映射base_K的递归额外储备，非全部K-J',
                           'equal_total_reference':'每结构统一2J的总K，诊断结构效果，不是发布规则'},
            'case_count':len(rows),'mapping_count':len(MAPPINGS),'mapping_case_count':len(rows)*len(MAPPINGS),
            'identity_checks_passed':count,'cases':rows}
    destination=root/'mapping-audit.json'
    destination.write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps({'output':str(destination),'cases':len(rows),'mapping_cases':len(rows)*len(MAPPINGS),'identity_checks_passed':count},ensure_ascii=False))

if __name__=='__main__':main()
