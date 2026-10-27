"""收入研究的来源边界、奖与资格分离及年度接入检查。"""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

FOLDER=Path(__file__).resolve().parents[1]/'merit_research'


class MeritIncomeChecks(unittest.TestCase):
    def test_source_ledger_boundaries(self):
        result=subprocess.run([sys.executable,str(FOLDER/'income/checks.py')],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_exam_reward_eligibility_is_not_pass_eligibility(self):
        code="""
from model import apply_event
p=dict(cap=4)
event=dict(id='lowborn-pass',kind='metropolitan',eligible=False,score_factor=1,grade_factor=1)
assert apply_event(p,event)==0
assert p['cap']==6
assert apply_event(p,event)==0
"""
        result=subprocess.run([sys.executable,'-c',code],cwd=FOLDER/'income',capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_annual_hooks_credit_once_after_creation(self):
        with tempfile.TemporaryDirectory() as temporary:
            frozen=Path(temporary)/'frozen'
            result=subprocess.run([sys.executable,str(FOLDER/'run.py'),'joint','--prepare-only',
                                   '--output-dir',str(frozen)],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            code="""
import study
created=[];income=[];snapshots=[]
def initialize(person):
 person['m']+=100;person['cap']=2;created.append(person['id'])
def credit(person,job,year):
 income.append((person['id'],year))
 return dict(fixed=20,tax=0,maa=0,funding=0,events=3)
def observe(stage,year,people,context):
 if stage=='decision' and year==2:
  snapshots.extend((p['entry'],p['m']) for p in people.values())
result=study.trial('civil',50,dict(mapping='uniform2',J=[1,0,0,0],initial='empty',entry_mult=1/26),
 years=3,income_step=credit,person_init=initialize,observer=observe)
assert len(created)==2 and len(income)==1
assert income[0][1]==2
assert sorted(snapshots)==[(1,223),(2,200)],snapshots
assert result['series'][2]['income_ledger']['fixed']==20
assert result['series'][2]['income_ledger']['events']==3
"""
            result=subprocess.run([sys.executable,'-c',code],cwd=frozen/'merit-joint-study',capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)

    def test_output_must_be_outside_repository(self):
        forbidden=FOLDER/'income/forbidden-output'
        result=subprocess.run([sys.executable,str(FOLDER/'income/study.py'),'--output-dir',str(forbidden),
                               '--game-root','unused'],capture_output=True,text=True)
        self.assertNotEqual(result.returncode,0)
        self.assertIn('仓库外',result.stderr)
        self.assertFalse(forbidden.exists())


if __name__=='__main__': unittest.main()
