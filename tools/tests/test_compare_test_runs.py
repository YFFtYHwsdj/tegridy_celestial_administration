"""比较两次运行证据的逐用例结果与断言计数，不启动游戏。"""
import json
from pathlib import Path
import tempfile
import unittest

from compare_test_runs import compare, load_verification, main


def write_verification(root, name, cases, counts, makedir=True):
    """在临时目录写出最小 verification.json 证据。"""
    path = Path(root) / name
    if makedir:
        path.mkdir()
    (path / 'verification.json').write_text(
        json.dumps({'scope': 'selection', 'cases': cases, 'counts': counts,
                    'issues': [], 'verification_exit': 0}, ensure_ascii=False),
        encoding='utf-8')
    return path


class CompareTestRunsTests(unittest.TestCase):
    def test_identical_runs_have_no_differences(self):
        with tempfile.TemporaryDirectory() as temp:
            cases = {'tca_test_alpha': 'PASS', 'tca_test_beta': 'FAIL'}
            counts = {'BEGIN': 2, 'PASS': 1, 'FAIL': 1, 'PRECONDITION_FAIL': 0, 'CHECK_PASS': 3}
            first = write_verification(temp, 'run-a', cases, counts)
            second = write_verification(temp, 'run-b', cases, counts)
            result = compare(first, second)
            self.assertTrue(result['ok'])
            self.assertEqual(result['differences'], [])
            self.assertEqual(main([str(first), str(second)]), 0)

    def test_case_and_check_pass_differences_are_reported(self):
        with tempfile.TemporaryDirectory() as temp:
            first = write_verification(temp, 'run-a',
                                       {'tca_test_alpha': 'PASS', 'tca_test_beta': 'PASS'},
                                       {'CHECK_PASS': 5, 'PASS': 2})
            second = write_verification(temp, 'run-b',
                                        {'tca_test_alpha': 'FAIL', 'tca_test_beta': 'PASS'},
                                        {'CHECK_PASS': 4, 'PASS': 1})
            result = compare(first, second)
            self.assertFalse(result['ok'])
            self.assertEqual(result['cases']['differences'],
                             [{'case': 'tca_test_alpha', 'first': 'PASS', 'second': 'FAIL'}])
            self.assertEqual(result['count_differences'],
                             [{'kind': 'CHECK_PASS', 'first': 5, 'second': 4},
                              {'kind': 'PASS', 'first': 2, 'second': 1}])
            self.assertEqual(main([str(first), str(second)]), 1)

    def test_ignore_accepts_comma_separated_and_missing_cases(self):
        with tempfile.TemporaryDirectory() as temp:
            first = write_verification(temp, 'run-a', {'tca_test_alpha': 'PASS'},
                                       {'CHECK_PASS': 2})
            second = write_verification(temp, 'run-b',
                                        {'tca_test_alpha': 'FAIL', 'tca_test_new': 'PASS'},
                                        {'CHECK_PASS': 2})
            result = compare(first, second, ['tca_test_alpha,tca_test_new'])
            self.assertTrue(result['ok'])
            self.assertEqual(len(result['cases']['ignored']), 2)
            self.assertIn('<missing>', {item['first'] for item in result['cases']['ignored']})
            self.assertEqual(main([str(first), str(second),
                                   '--ignore', 'tca_test_alpha', '--ignore', 'tca_test_new']), 0)

    def test_json_output_records_evidence_paths_and_differences(self):
        with tempfile.TemporaryDirectory() as temp:
            first = write_verification(temp, 'run-a', {'tca_test_alpha': 'PASS'},
                                       {'CHECK_PASS': 1})
            second = write_verification(temp, 'run-b', {'tca_test_alpha': 'FAIL'},
                                        {'CHECK_PASS': 1})
            output = Path(temp) / 'comparison.json'
            self.assertEqual(main([str(first), str(second), '--json', str(output)]), 1)
            data = json.loads(output.read_text(encoding='utf-8'))
            self.assertFalse(data['ok'])
            self.assertEqual(data['total_differences'], 1)
            self.assertTrue(data['first'].endswith('verification.json'))

    def test_invalid_evidence_fails_without_crashing(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'verification.json'
            path.write_text('{}', encoding='utf-8')
            with self.assertRaises(ValueError):
                load_verification(path)
            self.assertEqual(main([str(path), str(path)]), 1)
            self.assertEqual(main([str(Path(temp) / 'missing.json'), str(path)]), 1)

    def test_direct_file_and_directory_inputs_are_equivalent(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = write_verification(temp, 'run-a', {'tca_test_alpha': 'PASS'},
                                           {'CHECK_PASS': 1})
            self.assertEqual(load_verification(directory)['cases'],
                             load_verification(directory / 'verification.json')['cases'])


if __name__ == '__main__':
    unittest.main()
