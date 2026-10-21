"""平台默认路径：只检查路径拼接与选择，不访问真实安装。"""
from pathlib import Path
import os
import tempfile
import unittest
from unittest.mock import patch

import platform_paths
from platform_paths import game_executable, steam_library_with_app

# Steam 的库登记文件中路径使用双反斜杠转义。
LIBRARY_FOLDERS = r'''"libraryfolders"
{
	"0"
	{
		"path"		"C:\\Steam"
		"apps"
		{
			"228980"		"1"
		}
	}
	"1"
	{
		"path"		"D:\\Steam"
		"apps"
		{
			"1158310"		"1"
		}
	}
}
'''


class PlatformPathTests(unittest.TestCase):
    def test_executable_follows_platform(self):
        root = Path('/games/Crusader Kings III')
        self.assertEqual(game_executable(root, 'win32'), root / 'binaries/ck3.exe')
        self.assertEqual(game_executable(root, 'darwin'), root / 'binaries/ck3.app/Contents/MacOS/ck3')

    def test_library_with_app_is_found_in_libraryfolders(self):
        with tempfile.TemporaryDirectory() as temp:
            steam = Path(temp) / 'Steam'
            (steam / 'steamapps').mkdir(parents=True)
            (steam / 'steamapps/libraryfolders.vdf').write_text(LIBRARY_FOLDERS, encoding='utf-8')
            self.assertEqual(steam_library_with_app(steam), Path('D:\\Steam'))
            # 没有登记文件时退回 Steam 根目录。
            self.assertEqual(steam_library_with_app(Path(temp) / 'missing'), Path(temp) / 'missing')

    def test_environment_override_wins(self):
        with patch.dict(os.environ, {'CK3_GAME_DIR': '/custom/ck3'}):
            self.assertEqual(platform_paths.default_game_dir(), Path('/custom/ck3'))


if __name__ == '__main__':
    unittest.main()
