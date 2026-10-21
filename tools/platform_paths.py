"""按操作系统给出 CK3 安装目录、可执行文件及「文档」目录的默认值，供测试与检查工具共用。

macOS 沿用原有 Steam 默认路径；Windows 从注册表读取 Steam 位置，并在各 Steam 库中查找
CK3（应用 1158310），找不到时退回 Steam 默认库。环境变量 CK3_GAME_DIR 可覆盖安装目录。
命令行参数 --game-dir、--settings 仍优先于这里的默认值。
"""
import os
from pathlib import Path
import re
import sys

APP_ID = '1158310'
MAC_STEAM = Path.home() / 'Library/Application Support/Steam'


def windows_steam_root():
    """返回注册表登记的 Steam 根目录；读不到时返回默认安装位置。"""
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Valve\Steam') as key:
            return Path(winreg.QueryValueEx(key, 'SteamPath')[0])
    except OSError:
        return Path(os.environ.get('ProgramFiles(x86)', r'C:\Program Files (x86)')) / 'Steam'


def steam_library_with_app(steam_root, app_id=APP_ID):
    """在 libraryfolders.vdf 中查找包含指定应用的库；没有登记文件或未找到时返回 Steam 根目录。

    只做文本匹配：每个库块含 "path" 与 "apps" 列表，应用 ID 出现在该库的 apps 中即视为已安装。
    """
    vdf = steam_root / 'steamapps/libraryfolders.vdf'
    try:
        text = vdf.read_text(encoding='utf-8', errors='replace')
    except OSError:
        return steam_root
    for block in re.split(r'\n\s*"\d+"\s*\n', text):
        path = re.search(r'"path"\s+"([^"]+)"', block)
        if path and re.search(r'"' + app_id + r'"\s+"', block):
            return Path(path.group(1).replace('\\\\', '\\'))
    return steam_root


def default_game_dir():
    """CK3 安装根目录（含 binaries/ 与 game/），不是 game/ 目录本身。"""
    override = os.environ.get('CK3_GAME_DIR')
    if override:
        return Path(override)
    if sys.platform == 'win32':
        library = steam_library_with_app(windows_steam_root())
    else:
        library = MAC_STEAM
    return library / 'steamapps/common/Crusader Kings III'


def game_executable(game_dir, platform=None):
    """按平台返回安装根目录下的游戏可执行文件。"""
    if (platform or sys.platform) == 'win32':
        return game_dir / 'binaries/ck3.exe'
    return game_dir / 'binaries/ck3.app/Contents/MacOS/ck3'


def documents_dir():
    """当前用户的「文档」目录；Windows 用系统已知文件夹接口，兼容被 OneDrive 重定向的情况。"""
    if sys.platform == 'win32':
        try:
            import ctypes
            # FOLDERID_Documents = {FDD39AD0-238F-46AF-ADB4-6C85480369C7}
            guid = (ctypes.c_ubyte * 16)(*bytes.fromhex('d09ad3fd8f23af46adb46c85480369c7'))
            buffer = ctypes.c_wchar_p()
            if ctypes.windll.shell32.SHGetKnownFolderPath(guid, 0, None, ctypes.byref(buffer)) == 0:
                path = Path(buffer.value)
                ctypes.windll.ole32.CoTaskMemFree(buffer)
                return path
        except (OSError, AttributeError):
            pass
    return Path.home() / 'Documents'


def default_settings():
    """只读来源：本机 CK3 用户目录中的 pdx_settings.txt。"""
    return documents_dir() / 'Paradox Interactive/Crusader Kings III/pdx_settings.txt'
