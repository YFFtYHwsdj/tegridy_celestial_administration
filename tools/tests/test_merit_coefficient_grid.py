"""全网格覆盖和候选保留策略，不启动长生涯搜索。"""
import importlib.util
from pathlib import Path
import subprocess
import sys
import unittest

FOLDER=Path(__file__).resolve().parents[1]/'merit_research'


class CoefficientGridChecks(unittest.TestCase):
    def call(self,code):
        result=subprocess.run([sys.executable,'-c',code],cwd=FOLDER,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_cartesian_grid_covers_all_four_axes(self):
        self.call("""
import coefficient_grid as grid
rows=grid.configurations()
assert len(rows)==len(set(map(tuple,rows)))==1296
assert rows[0]==[1.5]*4 and rows[-1]==[4]*4
for i in range(4):assert sorted({r[i] for r in rows})==[1.5,2,2.5,3,3.5,4]
""")

    def test_every_top_band_layer_and_user_reference_survive_screening(self):
        self.call("""
import coefficient_grid as grid
ranked=[dict(coefficients=c,worst_tracking=i,mean_tracking=i,budget=sum(c),actual_top_per_empire=-i)
        for i,c in enumerate(grid.configurations())]
selected=grid.select(ranked)
assert {r['coefficients'][3] for r in selected}==set(grid.VALUES)
assert any(r['coefficients']==[1.5,2,3,1.5] for r in selected)
for value in [1.5,2.5,4]:assert any(r['coefficients']==[value]*4 for r in selected)
assert len(selected)<=12
""")

    def test_small_world_uses_shared_initial_population_and_all_routes(self):
        self.call("""
import coefficient_grid as grid
plan=grid.design()
assert len(plan['screen']['initial_counts'])==9
assert plan['screen']['J'][3]==1
jobs=grid.jobs('screen')
assert len(jobs)==8
assert len({(j['route'],j['seed'],j['profile']) for j in jobs})==8
assert len(grid.jobs('validation'))==8
assert set(plan['screen']['seeds']).isdisjoint(plan['validation']['seeds'])
""")


if __name__=='__main__':unittest.main()
