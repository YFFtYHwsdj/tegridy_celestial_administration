"""静态 GUI 绑定检查，不模拟原生状态效果。"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]


class StatusWindowContracts(unittest.TestCase):
    def test_widget_registration_uses_existing_window_without_hud_override(self):
        registry = (ROOT / 'gui/scripted_widgets/tca_test_status_widgets.txt').read_text(encoding='utf-8-sig')
        gui = (ROOT / 'gui/tca_test_status.gui').read_text(encoding='utf-8-sig')
        self.assertIn('gui/tca_test_status.gui = tca_test_status_window', registry)
        self.assertIn('name = "tca_test_status_window"', gui)
        self.assertNotIn('GetPlayer', gui)
        self.assertNotIn('GetHolder', gui)
        self.assertNotIn('IsObserver', gui)

    def test_status_text_and_title_snapshot_bindings_match(self):
        import re
        gui = (ROOT / 'gui/tca_test_status.gui').read_text(encoding='utf-8-sig')
        keys = re.findall(r'text = "(tca_test_status_\w+)"', gui)
        self.assertTrue(keys)
        for lang in ('english', 'simp_chinese'):
            path = ROOT / f'localization/{lang}/tca_court_tests_l_{lang}.yml'
            self.assertTrue(path.read_bytes().startswith(b'\xef\xbb\xbf'))
            text = path.read_text(encoding='utf-8-sig')
            for key in keys:
                self.assertIn(key + ':', text)
        self.assertIn("GetTitleByKey('h_china')", gui)
        self.assertIn("Title.MakeScope.Var('tca_test_status_visible')", gui)


if __name__ == '__main__':
    unittest.main()
