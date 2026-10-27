"""只读验收合成校准的源码、矩阵及逐年人口账，不把数值目标强改为通过。"""
import argparse
import hashlib
import json
from pathlib import Path
import run as runner


def check(root):
    """核对声明的训练和留出矩阵，缺文件/改版/断言失败均直接报错。"""
    result=json.loads((root/'calibration-results.json').read_text())
    pilot=json.loads((root/'calibration-pilot.json').read_text())
    runner.verify_snapshot(root,runner.selection('joint'),[])
    for name,item in result['source_manifest'].items():
        assert hashlib.sha256((root/name).read_bytes()).hexdigest()==item['sha256'],name
    for source in [root/'calibrate_joint.py',Path(__file__).with_name('calibrate_joint.py')]:
        assert hashlib.sha256(source.read_bytes()).hexdigest()==result['calibration_sha256'],str(source)
    count=0
    for rows,expected,years,seeds in [(pilot['runs'],result['training_runs'],result['training_years'],set(result['training_seeds'])),
                                     (result['runs'],result['validation_runs'],result['validation_years'],set(result['validation_seeds']))]:
        assert len(rows)==expected
        assert {r['seed'] for r in rows}==seeds
        assert len({(r['route'],r['seed'],r['config']['name']) for r in rows})==expected
        for row in rows:
            assert row['mechanism_errors']==0 and len(row['series'])==years
            assert 'military_low' not in row['config']
            assert row['config']['coefficients']==result['selected']['coefficients'] or rows is pilot['runs']
            if rows is result['runs']:
                assert row['config']['r']==result['selected']['r']
                assert row['config']['gain']==result['selected']['gain']
                assert row['config']['temperature']==.5 and row['config']['epsilon']==.1
            for i,s in enumerate(row['series']):
                assert s['year']==i
                assert sum(s['decision_n'])==sum(s['post_n'])==s['active']
                assert all(0<=q<=e for q,e in zip(s['Q'],s['E']))
                assert sum(s['known'])+sum(s['uncovered'])==sum(s['J'])
                assert abs(sum(s['target'])-1.1*sum(s['K']))<1e-7
                for b in range(3):
                    assert abs(s['target'][2*b+1]-.6*sum(s['target'][2*b:2*b+2]))<1e-7
                count+=1
            for cohort in [row['cohort'],row['post_cohort']]:
                if cohort is not None:
                    assert cohort['n']==cohort['first_job40']+cohort['dead_without_first40']+cohort['alive_without_first40']
    return dict(training_runs=result['training_runs'],validation_runs=result['validation_runs'],annual_states_checked=count,selected=result['selected'])


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('output_root',type=Path)
    args=parser.parse_args();print(json.dumps(check(args.output_root),ensure_ascii=False))

if __name__=='__main__':main()
