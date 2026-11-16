"""基督教局势兼容覆盖契约；不以静态检查代替住所参与者的引擎验收。"""
from pathlib import Path
import unittest

from check_upstream_overrides import tokens


ROOT = Path(__file__).resolve().parents[2]


class ChurchDomicileOverrideContractTests(unittest.TestCase):
    def test_only_candidate_collection_and_two_sync_calls_change(self):
        """原版资格、区域条件及阶段规则必须逐token保留。"""
        override = ROOT / "common/situation/situations/zz_tca_church_domicile.txt"
        baseline = ROOT / "tools/baselines/tca_church_domicile.txt"
        self.assertTrue(override.is_file(), "缺少住所候选入口兼容覆盖")
        self.assertTrue(baseline.is_file(), "缺少已审阅原版基线")
        expected = tokens(baseline.read_text(encoding="utf-8-sig"))
        for group in (
            "christian_clerical_main_power_rulers",
            "christian_regular_main_power_rulers",
            "christian_clerical_secondary_powers_rulers",
            "christian_regular_secondary_powers_rulers",
            "christian_clerical_heretic_rulers",
            "christian_regular_heretic_rulers",
        ):
            start = expected.index(group) + 3
            expected[start:start] = ["auto_add_landless_rulers", "=", "no"]
        start = expected.index("on_monthly") + 3
        expected[start:start] = ["tca_church_sync_domicile_candidates_effect", "=", "yes"]
        start = expected.index("the_christian_church_add_clerical_title_holders_as_manual_participants_effect") + 3
        expected[start:start] = ["tca_church_sync_domicile_candidates_effect", "=", "yes"]
        self.assertEqual(tokens(override.read_text(encoding="utf-8-sig")), expected)


if __name__ == "__main__":
    unittest.main()
