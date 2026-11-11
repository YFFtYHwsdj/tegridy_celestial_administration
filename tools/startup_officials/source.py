"""读取本机原版历史以准备资产；推导结果由原生开局测试核对。"""
from collections import defaultdict
from pathlib import Path
import re
from check_upstream_overrides import definitions


def read(path):
    """原版少数旧历史文件使用西欧编码；模组输出始终UTF-8 BOM。"""
    try:
        return path.read_text(encoding='utf-8-sig')
    except UnicodeDecodeError:
        return path.read_text(encoding='cp1252')


def block(value):
    return definitions(' '.join(value[1:-1]), allow_duplicates=True) if value and value[0]=='{' else {}


def scalar(value):
    return value[0].strip('"') if value and value[0]!='{' else None


def date_key(value):
    return tuple(map(int,value.split('.')))


def dated_state(history, date):
    result={k:v for k,v in history.items() if not re.fullmatch(r'\d+\.\d+\.\d+', k)}
    for d in sorted((d for d in history if re.fullmatch(r'\d+\.\d+\.\d+',d)),key=date_key):
        if date_key(d)<=date_key(date): result.update(block(history[d]))
    return {k:scalar(v) for k,v in result.items() if scalar(v) is not None}


class Vanilla:
    """有限源码快照索引；不重现游戏继任、任命或政府计算。"""
    def __init__(self, game):
        self.game=Path(game);self.parents={};self.titles={};self.history={};self.characters={}
        def walk(values,parent=None):
            for k,v in values.items():
                if re.fullmatch(r'[hek dcb]_[A-Za-z0-9_]+'.replace(' ',''),k) and v[0]=='{':
                    self.parents[k]=parent;self.titles[k]=block(v);walk(self.titles[k],k)
        for path in sorted((self.game/'common/landed_titles').glob('*.txt')):
            if not path.name.startswith('_'):walk(definitions(read(path),allow_duplicates=True))
        for path in sorted((self.game/'history/titles').glob('*.txt')):
            for k,v in definitions(read(path),allow_duplicates=True).items():
                if v[0]=='{': self.history.setdefault(k,{}).update(block(v))
        for path in sorted((self.game/'history/characters').glob('*.txt')):
            for k,v in definitions(read(path),allow_duplicates=True).items():
                if v[0]=='{':self.characters[k]=block(v)

    def offices(self, date):
        """候选源为实际宋朝辖属；排除高级主管兼持县及原版开局军路。"""
        states={k:dated_state(v,date) for k,v in self.history.items()}
        holders=defaultdict(list)
        for k,s in states.items():
            if s.get('holder') not in (None,'0') and not k.startswith(('b_','c_nf_','d_nf_')):
                holders[s['holder']].append(k)
        def belongs(k):
            seen=set()
            while k and k not in seen:
                if k=='h_china':return True
                seen.add(k);k=states.get(k,{}).get('liege')
            return False
        military={'1066.9.15':{'k_hebei','k_guannei','k_lingxi'},
                  '1178.10.1':{'k_huainan','k_shannan','k_xingyuan','k_lingxi','k_xichuan'}}[date]
        rows=[]
        for k,s in sorted(states.items()):
            if not belongs(k) or s.get('government')!='celestial_government' or s.get('holder') in (None,'0'):
                continue
            if k.startswith('k_') and k not in military:
                if any(t.startswith(('h_','e_')) for t in holders[s['holder']]):continue
                cap=scalar(self.titles.get(k,{}).get('capital'))
                # 资本可能是省份ID；从该路法理后代县定位。
                if cap and not cap.startswith('c_'):
                    cap=next((c for c,p in self.parents.items() if c.startswith('c_') and self.parents.get(p)==k),None)
                rows.append(dict(date=date,kind='judicial',office='d_tca_judicial_'+k[2:],jurisdiction=k,liege=k,capital=cap))
            if not k.startswith('c_') or k.startswith('c_nf_'):continue
            held=holders[s['holder']]
            if any(t.startswith(('h_','e_','k_','d_')) for t in held):continue
            counties=[t for t in held if t.startswith('c_') and scalar(self.titles.get(t,{}).get('landless'))!='yes']
            if counties!=[k]:
                raise ValueError('多县主头衔需人工审阅：'+s['holder']+' '+str(counties))
            if scalar(self.titles.get(k,{}).get('landless'))=='yes':continue
            duchy=self.parents.get(k);circuit=self.parents.get(duchy)
            liege=None
            for candidate in (duchy,circuit,'e_minister_chancellor'):
                cs=states.get(candidate,{})
                if cs.get('holder') not in (None,'0',states['h_china'].get('holder')) and belongs(candidate):
                    liege=candidate;break
            if not liege:raise ValueError('找不到通判上级：'+k)
            rows.append(dict(date=date,kind='tongpan',office='c_tca_tongpan_'+k[2:],jurisdiction=k,liege=liege,capital=k))
        return rows

    def validate_holders(self, rows, mod):
        """检测人物引用、目标日年龄、存活与原版兼职；不替代引擎资格。"""
        characters=dict(self.characters)
        for path in (Path(mod)/'history/characters').glob('*.txt'):
            if path.name.startswith('tca_officials_generated_'):continue
            for k,v in definitions(read(path)).items():characters[k]=block(v)
        for row in rows:
            if not row.get('holder'):continue
            person=row['holder'];history=characters.get(person)
            if not history:raise ValueError('人工人物不存在：'+person)
            birth=[d for d,v in history.items() if re.fullmatch(r'\d+\.\d+\.\d+',d) and scalar(block(v).get('birth'))=='yes']
            death=[d for d,v in history.items() if re.fullmatch(r'\d+\.\d+\.\d+',d) and 'death' in block(v)]
            if not birth or date_key(max(birth,key=date_key))[0]+16>date_key(row['date'])[0] or any(date_key(d)<=date_key(row['date']) for d in death):
                raise ValueError('人工人物未成年、未出生或已死亡：'+person)
            held=[k for k,v in self.history.items() if dated_state(v,row['date']).get('holder')==person and not k.startswith(('c_nf_','d_nf_','b_'))]
            if held:raise ValueError('人工人物有原版实职，拒绝强行剥夺：'+person+' '+str(held))
