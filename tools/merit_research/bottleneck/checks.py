"""诊断四格及固定终点的边界；不运行游戏或完整长实验。"""
from copy import deepcopy
from types import SimpleNamespace
import unittest
from observe import Observer

TH=[0,100,1000,2000,3500,5500,8500,12000,17000,23000]
PR=SimpleNamespace(TH=TH,ceiling=lambda seed,pid:9)


def context(people,a,eligible,ignore=False):
    pools={i:[] for i in range(1,7)};pools[a]=[people[i] for i in eligible]
    return dict(cfg={'ignore_merit':ignore},pools=pools,raw=[1]*6,Q=[0]*6,
                frozen={pid:p['rank'] for pid,p in people.items()})


def person(pid,rank=6,cap=9,merit=15000,entry=None):
    return dict(id=pid,rank=rank,cap=cap,m=merit,age=50,active=True,entry=entry,hit={1:0})


class ObserverChecks(unittest.TestCase):
    def test_cap_and_merit_four_cells_are_not_conflated(self):
        people={1:person(1,cap=6,merit=8000),2:person(2,cap=6),
                3:person(3,merit=8000),4:person(4)}
        for ignore,eligible in [(False,[4]),(True,[3,4])]:
            obs=Observer('civil',10,PR);ctx=context(people,6,eligible,ignore)
            obs('decision',0,people,ctx);obs('after',0,people,ctx)
            row=obs.result()['late_stages'][5]
            self.assertEqual([row[k] for k in ['cap_no_merit_no','cap_no_merit_yes','cap_yes_merit_no','cap_yes_merit_yes']],[1]*4)
            self.assertEqual(row['eligible'],len(eligible))

    def test_after_endpoint_cannot_add_wait_or_selected(self):
        p=person(1,rank=1,merit=100,entry=20);p['hit']={1:20};people={1:p}
        obs=Observer('civil',10,PR)
        for year in [20,60]:
            ctx=context(people,1,[]);obs('decision',year,people,ctx);obs('after',year,people,ctx)
        before=deepcopy(obs.records[1]);ctx=context(people,1,[])
        obs('decision',61,people,ctx)
        p['rank']=2;obs('after',61,people,ctx)
        self.assertEqual(obs.records[1],before)
        result=obs.result()['cohort']['natural_cap7']
        self.assertEqual(result['alive_by_rank'][0],1)
        self.assertEqual(result['deaths_by_rank'],[0]*9)

if __name__=='__main__':unittest.main()
