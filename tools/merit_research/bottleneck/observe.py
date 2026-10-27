"""只读观察冻结人群；人数年与人物终点分别记账，不推断原生玩家概率。"""
import statistics


def mean(values):
    return statistics.mean(values) if values else None


class Observer:
    """关口四格分解+原始高资格队列，返回值不参与模拟。

    队列为20～59年入仕，在入仕后40年或此前死亡时冻结终点；
    all_qualified干预前的潜在cap仍用同seed/pid读取，保证对照同一批人。
    """
    def __init__(self,route,seed,pr):
        self.pr=pr;self.seed=seed+(1000000 if route=='military' else 0)
        self.years=[];self.records={};self.pending=None;self.exits=[]

    def __call__(self,stage,year,people,context):
        if stage=='exit':
            for p in people.values():
                self.exits.append(dict(year=year,rank=p['rank'],age=p['age'],entry=p['entry'],
                    cap=p['cap'],merit=p['m'],cause=p['health'].get('death_cause')))
                if p['id'] in self.records and year<=p['entry']+40:
                    self.finish(p,year,True)
            return
        if stage=='decision':
            rows=[]
            for a in range(1,7):
                source=[p for p in people.values() if p['active'] and p['rank']==a]
                cells=[0]*4
                for p in source:
                    cap=p['cap']>=a+1;merit=p['m']>=self.pr.TH[a+1]
                    cells[2*int(cap)+int(merit)]+=1
                eligible={p['id'] for p in context['pools'][a]}
                expected=cells[2]+cells[3] if context['cfg'].get('ignore_merit') else cells[3]
                assert expected==len(eligible),'本研究成人且无中央低品年界，四格应覆盖E'
                rows.append(dict(n=len(source),cap_no_merit_no=cells[0],cap_no_merit_yes=cells[1],
                    cap_yes_merit_no=cells[2],cap_yes_merit_yes=cells[3],eligible=len(eligible),q_star=context['raw'][a-1],
                    Q=context['Q'][a-1],age_mean=mean([p['age'] for p in source]),
                    eligible_age_mean=mean([p['age'] for p in source if p['id'] in eligible])))
                for p in source:
                    if p['entry'] is None or not 20<=p['entry']<60 or year>p['entry']+40:continue
                    record=self.records.setdefault(p['id'],dict(id=p['id'],entry=p['entry'],
                        natural_cap=self.pr.ceiling(self.seed,p['id']),cap=p['cap'],
                        merit_wait=[0]*6,eligible_wait=[0]*6,first_eligible=[None]*6,
                        selected=[0]*6,endpoint=None))
                    if p['cap']>=a+1 and p['m']<self.pr.TH[a+1]:record['merit_wait'][a-1]+=1
                    if p['id'] in eligible:
                        if record['first_eligible'][a-1] is None:record['first_eligible'][a-1]=year
                        record['eligible_wait'][a-1]+=1
            self.pending=dict(year=year,stages=rows)
        elif stage=='after':
            for pid,p in people.items():
                if pid in self.records and year<=p['entry']+40:
                    old=context['frozen'].get(pid)
                    if old is not None and p['rank']==old+1 and old<=6:
                        self.records[pid]['selected'][old-1]+=1
                        self.records[pid]['eligible_wait'][old-1]-=1
                    if year==p['entry']+40:self.finish(p,year,False)
            self.years.append(self.pending);self.pending=None

    def finish(self,p,year,dead):
        record=self.records[p['id']]
        if record['endpoint'] is not None:return
        record['endpoint']=dict(year=year,dead=dead,rank=p['rank'],age=p['age'],
            reached3=7 in p['hit'],merit=p['m'],hit=p['hit'])

    def result(self):
        late=self.years[-40:];stages=[]
        for a in range(6):
            rows=[s['stages'][a] for s in late]
            out={key:mean([s[key] for s in rows if s[key] is not None]) for key in rows[0]}
            total_n=sum(s['n'] for s in rows);raw=sum(s['q_star'] for s in rows)
            out.update(eligible_fraction=sum(s['eligible'] for s in rows)/total_n if total_n else None,
                unmet_expected_fraction=sum(max(0,s['q_star']-s['eligible']) for s in rows)/raw if raw else None,
                quota_rejection=sum(s['eligible']-s['Q'] for s in rows))
            stages.append(out)
        records=list(self.records.values())
        assert all(p['endpoint'] is not None for p in records),'队列未完整观察40年'
        cohort={}
        for label,group in [('all',records),('natural_cap7',[p for p in records if p['natural_cap']>=7])]:
            cohort[label]=dict(n=len(group),reached3=sum(p['endpoint']['reached3'] for p in group),
                deaths_by_rank=[sum(p['endpoint']['dead'] and p['endpoint']['rank']==a for p in group) for a in range(1,10)],
                alive_by_rank=[sum(not p['endpoint']['dead'] and p['endpoint']['rank']==a for p in group) for a in range(1,10)],
                merit_wait_mean=[mean([p['merit_wait'][a] for p in group]) for a in range(6)],
                eligible_wait_mean=[mean([p['eligible_wait'][a] for p in group]) for a in range(6)])
        return dict(late_stages=stages,cohort=cohort,years=self.years,exits=self.exits,records=records)
