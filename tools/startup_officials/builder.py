"""稳定生成原生人物与任职；仅更新清单中归属本工具的输出。"""
import hashlib
import json
from pathlib import Path
import random
import re
import tempfile

HEADER = '# 工具生成，勿手改；维护入口：python3 tools/build_startup_officials.py。\n'
MANIFEST = 'tools/startup_officials/generated_manifest.json'
DATES = ('1066.9.15', '1178.10.1')
SURNAMES = [('Zhao','赵'),('Qian','钱'),('Sun','孙'),('Li','李'),('Zhou','周'),('Wu','吴'),('Zheng','郑'),('Wang','王'),('Chen','陈'),('Xu','徐'),('Zhang','张'),('Liu','刘'),('Lu','陆'),('Shen','沈'),('Han','韩'),('Yang','杨')]
NAMES = [('Wen','文'),('Zhong','仲'),('Shou','守'),('Yuan','元'),('Jing','景'),('Zhi','志'),('Si','思'),('Yan','彦'),('De','德'),('Cheng','承'),('Ming','明'),('Xiu','修'),('Ren','仁'),('Yi','义'),('Liang','良'),('An','安'),('Qing','清'),('Fu','甫'),('Dao','道'),('Xian','贤')]
PERSONALITIES = [('diligent','patient','honest'),('calm','humble','generous'),('ambitious','gregarious','arrogant'),('just','stubborn','temperate'),('cynical','greedy','patient'),('lazy','content','compassionate'),('wrathful','brave','honest'),('shy','fickle','forgiving')]


def rng(seed, key, channel):
    """属性独立取样；新增官署或属性不扰动其它通道。"""
    digest = hashlib.sha256(f'{seed}:{key}:{channel}'.encode()).digest()
    return random.Random(int.from_bytes(digest, 'big'))


def character_id(row):
    return row.get('holder') or f"tca_gen_{row['date'][:4]}_{row['office']}"


def validate_config(config):
    """检查输入归属与显式空缺；引用及真实适用性另由源码扫描和引擎验证。"""
    if not 0 <= config['noble_probability'] <= 1:
        raise ValueError('世族概率须介于0和1')
    keys, people = set(), set()
    for row in config['offices']:
        if row['date'] not in DATES or row['kind'] not in ('tongpan','judicial'):
            raise ValueError('不支持的开局或职类')
        for field in ('office','jurisdiction','liege','capital'):
            if not re.fullmatch(r'[a-z][a-z0-9_]*', row[field]):
                raise ValueError('非法标识：'+field)
        key = row['date'], row['office']
        if key in keys:
            raise ValueError('重复官署：'+str(key))
        keys.add(key)
        if row.get('empty'):
            if not row.get('reason') or row.get('holder'):
                raise ValueError('明确空缺必须说明理由且不能指定人物')
            continue
        person = character_id(row)
        if not re.fullmatch(r'(?:[a-z][a-z0-9_]*|[0-9]+)', person):
            raise ValueError('非法人物ID')
        pk = row['date'], person
        if pk in people:
            raise ValueError('同一开局重复任职：'+person)
        people.add(pk)


def build_assets(config):
    """从唯一开局配置生成UTF-8文本映射；无文件副作用。"""
    validate_config(config)
    out, characters, dynasties = {}, {}, []
    loc = {'simp_chinese': ['l_simp_chinese:'], 'english': ['l_english:']}
    effects = [HEADER, '# 全局入口；仅新局维护前调用。初始化不重复抽样、不替换持有人。',
               'tca_initialize_startup_officials_effect = {',
               '    if = {', '        limit = { NOT = { has_global_variable = tca_startup_officials_v1 } }',
               '        set_global_variable = { name = tca_startup_officials_v1 value = yes }']
    rows = sorted(config['offices'], key=lambda r:(r['date'],r['office']))
    for date in DATES:
        effects += ['        if = {', f'            limit = {{ game_start_date = {date} current_date = {date} }}']
        for row in rows:
            if row['date'] != date or row.get('empty'):
                continue
            person = character_id(row); key = date+':'+row['office']; seed=row.get('seed',config['seed'])
            settings = dict(row.get('settings', {}))
            if 'level' not in settings:
                settings['level'] = (1 if row['kind']=='tongpan' else 3) + (rng(seed,key,'level').random() < .2)
            level = settings['level']; merit={1:100,2:1000,3:2000,4:3500}[level]
            noble = settings.get('noble', rng(seed,key,'noble').random() < config['noble_probability'])
            palace = settings.get('palace', rng(seed,key,'palace').random() < .1)
            # 日期之外还核对正式任职关系；不能仅因同一人物存在就改写其旧存档状态。
            effects += [f'            title:{row["office"]} = {{',
                        f'                if = {{ limit = {{ holder ?= character:{person} }}',
                        '                    holder = {']
            if row.get('holder'):
                effects += ['                        add_character_flag = tca_history_defined_character']
            effects += [f'                        tca_initialize_startup_official_effect = {{ LEVEL = {level} MERIT = {merit} NOBLE = {"yes" if noble else "no"} PALACE = {"yes" if palace else "no"} }}',
                        '                    }', '                }', '            }',
                        f'            title:{row["office"]} = {{',
                        f'                set_variable = {{ name = tca_startup_expected_holder value = character:{person} }}',
                        f'                set_variable = {{ name = tca_startup_jurisdiction value = title:{row["jurisdiction"]} }}',
                        f'                add_to_global_variable_list = {{ name = tca_startup_offices target = this }}', '            }']
            if row.get('holder'):
                continue
            surname=rng(seed,key,'surname').choice(SURNAMES)
            parts=rng(seed,key,'name').sample(NAMES,2)
            name_en=''.join(p[0] for p in parts);name_zh=''.join(p[1] for p in parts)
            dynasty='tca_dyn_'+person; name_key='tca_name_'+person
            age=rng(seed,key,'age').randint(25,49); year=int(date[:4]);birth=year-age
            death=year+rng(seed,key,'lifespan').randint(12,30)
            skills={s:rng(seed,key,s).randint(4,12) for s in ('diplomacy','martial','stewardship','intrigue','learning')}
            skills['learning']+=rng(seed,key,'learning_bonus').randint(2,5)
            traits=list(rng(seed,key,'personality').choice(PERSONALITIES))
            traits.append(rng(seed,key,'education').choice(('education_learning_3','education_learning_4')))
            char=[f'{person} = {{',f'    name = {name_key}',f'    dynasty = {dynasty}',
                  '    culture = han','    rite = daoxue',
                  *[f'    {s} = {v}' for s,v in skills.items()],
                  *[f'    trait = {t}' for t in traits],
                  f'    {birth}.1.1 = {{ birth = yes }}',f'    {death}.1.1 = {{ death = yes }}','}']
            bucket=f'history/characters/tca_officials_generated_{date[:4]}_{row["kind"]}.txt'
            characters.setdefault(bucket,[]).append('\n'.join(char))
            dynasties.append(f'{dynasty} = {{ name = {dynasty} culture = han }}')
            loc['simp_chinese'] += [f' {name_key}: "{name_zh}"',f' {dynasty}: "{surname[1]}"']
            loc['english'] += [f' {name_key}: "{name_en}"',f' {dynasty}: "{surname[0]}"']
        effects.append('        }')
    effects += ['    }','}']
    for path, blocks in characters.items():
        out[path]=HEADER+('\n# 下一人物\n'.join(blocks))+'\n'
    out['common/dynasties/tca_officials_generated.txt']=HEADER+'\n'.join(dynasties)+'\n'
    title_lines=[HEADER]
    for office in sorted({r['office'] for r in rows}):
        title_lines.append(office+' = {')
        for date in DATES:
            row=next((r for r in rows if r['date']==date and r['office']==office),None)
            if not row or row.get('empty'):
                title_lines.append(f'    {date} = {{ holder = 0 }}')
                continue
            title_lines += [f'    {date} = {{',f'        holder = {character_id(row)}',
                            '        government = celestial_government',f'        liege = {row["liege"]}']
            if row['kind']=='judicial':
                title_lines += ['        effect = {',f'            tca_bind_judicial_circuit_effect = {{ CIRCUIT = title:{row["jurisdiction"]} }}','        }']
            title_lines.append('    }')
        title_lines.append('}')
    out['history/titles/tca_startup_office_titles.txt']='\n'.join(title_lines)+'\n'
    out['common/scripted_effects/tca_startup_officials_generated_effects.txt']='\n'.join(effects)+'\n'
    for language, lines in loc.items():
        out[f'localization/{language}/tca_officials_generated_l_{language}.yml']='\n'.join(lines)+'\n'
    return out


def digest(data):
    return hashlib.sha256(data).hexdigest()


def write_assets(root, assets, check=False):
    """先检查全部归属再写入；清理自产失效文件前拒绝外部引用。返回差异列表。"""
    root=Path(root); manifest_path=root/MANIFEST
    old=json.loads(manifest_path.read_text()) if manifest_path.is_file() else {'files':{}}
    encoded={p:('\ufeff'+s).encode('utf-8') for p,s in assets.items()}
    for name in set(old['files']) | set(assets):
        path=Path(name)
        if path.is_absolute() or '..' in path.parts or not name.startswith(('history/','common/','localization/')) or not (root/name).resolve().is_relative_to(root.resolve()):
            raise ValueError('非法输出路径：'+name)
    for name, sha in old['files'].items():
        path=root/name
        if path.exists() and (not path.is_file() or digest(path.read_bytes())!=sha):
            raise ValueError('生成资产已被手改，停止写入：'+name)
    for name in assets:
        path=Path(name)
        if path.is_absolute() or '..' in path.parts or not name.startswith(('history/','common/','localization/')):
            raise ValueError('非法输出路径：'+name)
        if (root/name).exists() and name not in old['files']:
            raise ValueError('拒绝覆盖非工具所有文件：'+name)
    # 所有自产对象（人物、家族与名称键）都参与删除引用保护。
    # 只检查人物会漏掉人工人物对生成家族的引用。
    def symbols(name, data):
        if name.endswith('.yml'):
            return set(re.findall(r'^ (tca_[a-z0-9_]+):',data,re.M))
        return set(re.findall(r'^(tca_[a-z0-9_]+)\s*=\s*\{',data,re.M))
    old_ids=set();new_ids=set()
    for name in old['files']:
        if (root/name).is_file():old_ids.update(symbols(name,(root/name).read_text(encoding='utf-8-sig')))
    for name,data in assets.items():new_ids.update(symbols(name,data))
    removed=old_ids-new_ids
    if removed:
        expression=re.compile(r'\b(?:'+'|'.join(re.escape(x) for x in removed)+r')\b')
        for folder in ('history','common','events','localization','decisions','gui'):
            for p in (root/folder).rglob('*'):
                if p.is_file() and p.relative_to(root).as_posix() not in old['files'] and p.suffix in ('.txt','.yml','.gui'):
                    if expression.search(p.read_text(encoding='utf-8-sig')):
                        raise ValueError('失效生成对象仍被引用：'+p.relative_to(root).as_posix())
    changed=[n for n,b in encoded.items() if not (root/n).exists() or (root/n).read_bytes()!=b]
    stale=sorted(set(old['files'])-set(assets))
    if check:
        if changed or stale:
            raise ValueError('生成资产与配置不一致：'+', '.join(changed+stale))
        return []
    # 各目标先全部暂存；预检或暂存失败均不修改原资产。
    staged=[]
    previous={name:(root/name).read_bytes() if (root/name).is_file() else None for name in changed+stale}
    old_manifest=manifest_path.read_bytes() if manifest_path.is_file() else None
    try:
        for name in changed:
            target=root/name;target.parent.mkdir(parents=True,exist_ok=True)
            with tempfile.NamedTemporaryFile(dir=target.parent,delete=False) as f:
                f.write(encoded[name]);staged.append((Path(f.name),target))
        for temporary,target in staged: temporary.replace(target)
        for name in stale:(root/name).unlink(missing_ok=True)
        manifest_path.parent.mkdir(parents=True,exist_ok=True)
        manifest_path.write_text(json.dumps({'files':{n:digest(b) for n,b in encoded.items()}},ensure_ascii=False,indent=2)+'\n')
    except OSError:
        # 替换阶段失败也恢复已提交的文件；清单与资产不得留下不同代。
        for name,data in previous.items():
            if data is None:(root/name).unlink(missing_ok=True)
            else:(root/name).write_bytes(data)
        if old_manifest is None:manifest_path.unlink(missing_ok=True)
        else:manifest_path.write_bytes(old_manifest)
        raise
    finally:
        for temporary,_ in staged:temporary.unlink(missing_ok=True)
    return changed+stale
