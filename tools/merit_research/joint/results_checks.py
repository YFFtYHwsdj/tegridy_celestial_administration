"""联合结果的运行数、来源封印与逐年守恒验收；缺产物时明确跳过。"""
import json
from pathlib import Path
import unittest
import study

ROOT=Path(__file__).resolve().parent

@unittest.skipUnless((ROOT/'results.json').is_file(),'尚未生成联合结果，仅做源码检查')
class ResultsChecks(unittest.TestCase):
    def test_frozen_results_and_complete_matrix(self):
        pilot=json.loads((ROOT/'pilot.json').read_text())
        result=json.loads((ROOT/'results.json').read_text())
        for data,count,years in [(pilot,36,80),(result,76,120)]:
            self.assertEqual(data['source_sha256'],study.seals())
            self.assertEqual(len(data['runs']),count)
            self.assertEqual(len({(r['route'],r['seed'],r['config']['name']) for r in data['runs']}),count)
            for run in data['runs']:
                self.assertEqual(len(run['series']),years)
                self.assertEqual(run['mechanism_errors'],0)
                for row in run['series']:
                    self.assertEqual(sum(row['decision_n']),row['active'])
                    self.assertEqual(sum(row['post_n']),row['active'])
                    self.assertEqual(sum(row['known'])+sum(row['uncovered']),sum(row['J']))
                    self.assertTrue(all(0<=q<=e for q,e in zip(row['Q'],row['E'])))
                for cohort in [run['cohort'],run['post_cohort']]:
                    if cohort is not None:
                        self.assertEqual(cohort['n'],cohort['first_job40']+cohort['dead_without_first40']+cohort['alive_without_first40'])
                        self.assertLessEqual(cohort['capable_reached3'],cohort['capable3'])
        self.assertEqual(set(pilot['seeds']),{0,1})
        self.assertEqual(set(result['seeds']),{2,3})

if __name__=='__main__':unittest.main()
