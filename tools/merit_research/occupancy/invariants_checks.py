"""核对封存研究结果的分母、守恒与来源，不替代引擎行为验收。"""
import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parent

class ResearchLedgerChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads((ROOT / 'results.json').read_text())

    def test_source_seals(self):
        for key in ('source_sha256', 'dependency_sha256'):
            for name, expected in self.data[key].items():
                with self.subTest(name=name):
                    self.assertEqual(hashlib.sha256((ROOT / name).read_bytes()).hexdigest(), expected)

    def test_coverage(self):
        self.assertEqual(len(self.data['runs']), 160)
        self.assertEqual(len(self.data['static_runs']), 72)
        self.assertEqual(len(self.data['groups']), 40)
        identities = set()
        for run in self.data['runs']:
            identities.add((run['route'], run['case'], run['seed']))
        self.assertEqual(len(identities), 160)

    def test_dynamic_ledgers(self):
        for run in self.data['runs']:
            with self.subTest(route=run['route'], case=run['case'], seed=run['seed']):
                m = run['metrics']
                self.assertEqual(len(run['series']), 80 if run['seed'] == 0 else 0)
                observed = run['series'][20:80]
                for t, slots in enumerate(run['J']):
                    self.assertEqual(m['slot_years'][t], slots * 60)
                    if observed:
                        self.assertEqual(m['filled_years'][t], sum(s['filled'][t] for s in observed))
                        self.assertEqual(m['high_occupied_years'][t], sum(s['high'][t] for s in observed))
                    self.assertLessEqual(m['high_occupied_years'][t], m['filled_years'][t])
                    self.assertLessEqual(m['filled_years'][t], m['slot_years'][t])
                    self.assertEqual(m['vacant_unfilled'][t], m['slot_years'][t] - m['filled_years'][t])
                    self.assertLessEqual(m['merit_advantage'][t], m['high_wins_with_low'][t])
                    self.assertLessEqual(m['high_wins_with_low'][t], m['low_competitive_events'][t])
                    self.assertLessEqual(m['low_competitive_events'][t], m['appointments'][t])
                    self.assertLessEqual(m['high_new'][t], m['appointments'][t])
                    matrix_total = sum(row[t] for row in run['mean_occupation_matrix'])
                    self.assertAlmostEqual(matrix_total * 60, m['filled_years'][t], places=6)
                    for a, row in enumerate(run['mean_occupation_matrix'], 1):
                        if a < 2 * t + 1:
                            self.assertEqual(row[t], 0)
                for s in run['series']:
                    self.assertEqual(sum(s['rank_bands']), s['population'])
                    self.assertLessEqual(sum(s['filled']), s['population'])
                    for t in range(4):
                        self.assertLessEqual(s['high'][t], s['filled'][t])
                        self.assertLessEqual(s['filled'][t], run['J'][t])
                self.assertEqual(m['high_occupied_years'][3], 0)

    def test_fixed_endpoint_cohorts(self):
        for run in self.data['runs']:
            with self.subTest(route=run['route'], case=run['case'], seed=run['seed']):
                self.assertLessEqual(run['first_job40'], run['cohort_n'])
                waits = run['conditional_first_job_wait']
                self.assertEqual(len(waits), run['first_job40'])
                self.assertTrue(all(0 <= w <= 40 for w in waits))
                self.assertEqual(run['cohort_n'], 520 if run['route'] == 'civil' else 160)

    def test_frozen_allocations(self):
        populations = {'civil': [702,81,1,21,6,12,17,11,1], 'military': [244,1,0,1,6,4,8,0,0]}
        for run in self.data['static_runs']:
            with self.subTest(route=run['route'], structure=run['structure'], mode=run['mode'], seed=run['seed']):
                for a, row in enumerate(run['O']):
                    self.assertEqual(sum(row), run['employed_by_rank'][a])
                    self.assertLessEqual(sum(row), populations[run['route']][a])
                for t in range(4):
                    filled = sum(row[t] for row in run['O'])
                    self.assertLessEqual(filled, run['J'][t])
                    self.assertEqual(filled, run['events'][t]['appointments'])

if __name__ == '__main__':
    unittest.main()
