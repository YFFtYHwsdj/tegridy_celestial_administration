"""固定参数的核查范围与数学解释，防止重新扩成参数搜索。"""
from pathlib import Path
import subprocess
import sys
import unittest

FOLDER=Path(__file__).resolve().parents[1]/'merit_research'


class FixedParameterChecks(unittest.TestCase):
    def call(self,code):
        result=subprocess.run([sys.executable,'-c',code],cwd=FOLDER,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_only_one_policy_and_twelve_worlds(self):
        self.call("""
import parameter_check as check
p=check.plan()
assert p['policy']['coefficients']==[1.5]*4
assert p['policy']['phi']==[.6]*3
assert len(p['jobs'])==12
assert len({(w['route'],w['seed'],w['profile'],w['scenario']) for w in p['jobs']})==12
assert sum(w['scenario']=='baseline' for w in p['jobs'])==8
assert {w['scenario'] for w in p['jobs']}=={'baseline','loss','mortality'}
""")

    def test_fixed_math_is_stable_without_claiming_exact_target(self):
        self.call("""
from pathlib import Path
import parameter_check as check
study=check.parent.load_study()
model=study.load(Path('parameters/math_model.py'),'fixed_check_math')
r=check.mathematical_check(model)
assert r['temperature']['exact']==.8
assert len(r['scalar'])==3
assert all(0<=s['equilibrium']['local_multiplier']<1 for s in r['scalar'])
slow=r['scalar'][0]
assert slow['equilibrium_to_K']>1.2
assert slow['paths'][1]['first_within_target10percent'] is None
""")


if __name__=='__main__':unittest.main()
