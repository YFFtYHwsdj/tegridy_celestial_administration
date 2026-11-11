#!/usr/bin/env python3
"""预览、校验或显式更新双开局官员；原版只读，人工文件永不写入。"""
import argparse
import json
from pathlib import Path
import sys
from platform_paths import default_game_dir
from startup_officials.builder import build_assets, character_id, write_assets
from startup_officials.source import Vanilla

ROOT=Path(__file__).resolve().parents[1]
CONFIG=ROOT/'tools/startup_officials/config.json'


def validate_sources(vanilla, config, root):
    """配置与本机原版适用目录一致；人工人物引用须有效且没有实职冲突。"""
    import hashlib
    for name,sha in config.get('upstream_sha256', {}).items():
        if hashlib.sha256((vanilla.game/name).read_bytes()).hexdigest()!=sha:
            raise ValueError('上游依赖已变化，请先人工审阅再更新配置摘要：'+name)
    expected={(r['date'],r['office']):r for date in ('1066.9.15','1178.10.1') for r in vanilla.offices(date)}
    actual={(r['date'],r['office']):r for r in config['offices']}
    if expected.keys()!=actual.keys():
        raise ValueError('开局目录缺失或多余：'+str(sorted(expected.keys()^actual.keys())))
    from check_upstream_overrides import definitions
    mod_titles=set()
    for p in (root/'common/landed_titles').glob('tca_*.txt'):
        mod_titles.update(definitions(p.read_text(encoding='utf-8-sig')))
    for key,row in actual.items():
        for field in ('jurisdiction','liege','capital','kind'):
            if row[field]!=expected[key][field]:raise ValueError('原版配置漂移：'+str(key)+' '+field)
        if row['office'] not in vanilla.titles:
            if row['office'] not in mod_titles:
                raise ValueError('官署不存在：'+row['office'])
    vanilla.validate_holders(config['offices'],root)
    generated={character_id(r) for r in config['offices'] if not r.get('holder') and not r.get('empty')}
    collision=generated & vanilla.characters.keys()
    if collision:raise ValueError('人物ID与原版冲突：'+str(collision))
    # 人工人物文件出现生成ID时也拒绝，以免同名定义靠加载顺序竞争。
    from check_upstream_overrides import definitions
    for p in (root/'history/characters').glob('*.txt'):
        if not p.name.startswith('tca_officials_generated_'):
            duplicate=generated & definitions(p.read_text(encoding='utf-8-sig')).keys()
            if duplicate:raise ValueError('人物ID与人工文件冲突：'+str(duplicate))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game-dir',type=Path,default=default_game_dir()/'game',help='原版game目录')
    mode=parser.add_mutually_exclusive_group()
    mode.add_argument('--check',action='store_true',help='只读检查配置、引用与自产文件')
    mode.add_argument('--write',action='store_true',help='显式接受预览差异并更新工具自产内容')
    parser.add_argument('--refresh-catalog', action='store_true', help='从原版刷新适用目录，默认预览，配合--write落地；保留人工指定')
    parser.add_argument('--reroll',action='append',default=[],help='重抽指定人物：开局年:官署ID；须与--write使用')
    parser.add_argument('--seed',type=int,help='指定重抽种子，不改变其它官员')
    args=parser.parse_args()
    try:
        config=json.loads(CONFIG.read_text(encoding='utf-8'))
        if args.reroll:
            if not args.write or args.seed is None:raise ValueError('定向重抽须指定--write与--seed')
            selected=set(args.reroll)
            for row in config['offices']:
                key=row['date'][:4]+':'+row['office']
                if key in selected:
                    if row.get('holder') or row.get('empty'):raise ValueError('不能重抽人工人物或明确空缺：'+key)
                    row['seed']=args.seed;selected.remove(key)
            if selected:raise ValueError('没有对应官署：'+str(selected))
        elif args.seed is not None:raise ValueError('--seed只能用于定向--reroll')
        vanilla=Vanilla(args.game_dir)
        if args.refresh_catalog:
            if args.check:raise ValueError('--check不能同时刷新目录')
            fresh=[r for d in ('1066.9.15','1178.10.1') for r in vanilla.offices(d)]
            old={(r['date'],r['office']):r for r in config['offices']}
            keys={(r['date'],r['office']) for r in fresh}
            for key,row in old.items():
                if key not in keys and row.get('holder'):
                    raise ValueError('原版不再适用的人工指定职位须先人工审阅：'+str(key))
            for row in fresh:
                previous=old.get((row['date'],row['office']),{})
                row.update({k:v for k,v in previous.items() if k not in row})
            config['offices']=fresh
        validate_sources(vanilla,config,ROOT)
        assets=build_assets(config)
        if args.check:
            write_assets(ROOT,assets,check=True)
        elif args.write:
            changes=write_assets(ROOT,assets)
            if args.reroll or args.refresh_catalog:CONFIG.write_text(json.dumps(config,ensure_ascii=False,indent=2)+'\n')
            print('更新文件：'+str(len(changes)))
        else:
            for name,data in assets.items():
                path=ROOT/name
                if not path.is_file() or path.read_text(encoding='utf-8-sig')!=data:print('待更新 '+name)
        for date in ('1066.9.15','1178.10.1'):
            for kind in ('judicial','tongpan'):
                rows=[r for r in config['offices'] if r['date']==date and r['kind']==kind]
                from startup_officials.builder import rng
                nobles=sum(r.get('settings',{}).get('noble',rng(r.get('seed',config['seed']),date+':'+r['office'],'noble').random()<config['noble_probability']) for r in rows if not r.get('empty'))
                print(f'{date} {kind}: {len(rows)} 个职位，{sum(bool(r.get("holder")) for r in rows)} 名人工指定，{nobles} 名计划持世族')
        return 0
    except (ValueError,OSError,KeyError) as e:
        print('检查失败：'+str(e),file=sys.stderr);return 1


if __name__=='__main__':sys.exit(main())
