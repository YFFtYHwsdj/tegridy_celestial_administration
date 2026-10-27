"""只读复核联合结果，补充恢复窗口、零额度与竞争挤占诊断。

输入是run.py joint生成的产物根目录。先核对结果及实际冻结文件摘要；
输出到stdout，调用者可重定向到仓库外。20%/连续五年仅为公开诊断线，
不是游戏硬阈值或已获用户认可的平衡验收线。未知持有人不补造成人口。
"""
import argparse
import hashlib
import json
from pathlib import Path


def ratio(a,b):
    return a/b if b else None


def first_window(series,indices,start=60,tolerance=.2,width=5):
    """第一次连续五年各指定尾部都在目标±20%；没有则返回None。"""
    for index,row in enumerate(series):
        window=series[index:index+width]
        if row['year']<start or len(window)<width:continue
        if all(s['tail_error'][i] is not None and s['tail_error'][i]<=tolerance
               for s in window for i in indices):return row['year']-start
    return None


def analyze(root):
    folder=root/'merit-joint-study'
    data=json.loads((folder/'results.json').read_text())
    for name,digest in data['source_sha256'].items():
        if hashlib.sha256((folder/name).read_bytes()).hexdigest()!=digest:
            raise ValueError(f'冻结结果来源不一致：{name}')
    output={}
    for key,g in data['groups'].items():
        route,name=key.split('/')
        runs=[r for r in data['runs'] if r['route']==route and r['config']['name']==name]
        samples=[s for r in runs for s in r['series'][20:]]
        metrics=[r['metrics'] for r in runs]
        detail={'high_win_given_suitable':[ratio(sum(m['high_wins_with_low'][i] for m in metrics),
                            sum(m['competitive_events'][i] for m in metrics)) for i in range(4)],
          'zero_quota_given_candidates':[ratio(sum(s['Q'][i]==0 and s['E'][i]>0 for s in samples),
                            sum(s['E'][i]>0 for s in samples)) for i in range(6)],
          'no_candidates_fraction':[ratio(sum(s['E'][i]==0 for s in samples),len(samples)) for i in range(6)],
          'runs':[]}
        for r in runs:
            series=r['series'];snapshots={}
            for year in [59,60,80,119]:
                row=series[year]
                snapshots[year]={'n':row['decision_n'],'target':row['target'],
                      'tail_error':row['tail_error'],'known':row['known'],'uncovered':row['uncovered']}
            detail['runs'].append({'seed':r['seed'],'snapshots':snapshots,
                'all_tail_recovery5':first_window(series,range(6)),
                'top_tail_recovery5':first_window(series,[5])})
        output[key]=detail
    return {'version':'joint-diagnostics-v1','input_version':data['version'],
       'source_sha256':data['source_sha256'],'diagnostics_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
       'windows':{'competition_and_zero_quota':[20,119],
                  'recovery':'60年起第一次连续5年在目标±20%；None是观察期内未达到，不证明永不恢复'},
       'groups':output}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('output_root',type=Path)
    args=parser.parse_args();print(json.dumps(analyze(args.output_root),ensure_ascii=False,indent=2))

if __name__=='__main__':main()
