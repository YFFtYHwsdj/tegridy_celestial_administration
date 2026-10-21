"""只读检查Markdown链接、标题锚点、模块入口及公共文档的本机路径。"""

from collections import Counter
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit


INLINE_LINK = re.compile(r'!?\[[^\]\n]*\]\(\s*(?:<([^>]+)>|([^\s)]+))(?:\s+"[^"]*")?\s*\)')
REFERENCE = re.compile(r'^\s*\[[^\]]+\]:\s*(?:<([^>]+)>|([^\s]+))')

# 公共文档不得依赖个人目录或具体临时产物；研究原始来源记录不套用此规则。
MACHINE_PATH = re.compile(
    r"/(?:private/tmp|tmp|private/var/folders)/[^\s`<>]+"
    r"|/(?:Users|home)/[^/\s<>]+/"
    r"|[A-Za-z]:[\\/](?:Users|Temp)[\\/]",
    re.IGNORECASE,
)


def prose_lines(text):
    """排除围栏代码块并保留原行号；示例中的旧链接不是实际引用。"""
    fence = None
    for number, line in enumerate(text.splitlines(), 1):
        marker = re.match(r'^\s{0,3}(`{3,}|~{3,})', line)
        if marker:
            token = marker.group(1)
            if fence is None:
                fence = token
            elif token[0] == fence[0] and len(token) >= len(fence):
                fence = None
            continue
        if fence is None:
            yield number, line


def anchors(text):
    """计算本仓库使用的ATX标题锚点，包含中文及重复标题后缀。"""
    counts = Counter()
    result = set()
    for _, line in prose_lines(text):
        heading = re.match(r'^ {0,3}#{1,6}\s+(.+?)\s*#*\s*$', line)
        if not heading:
            continue
        title = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', heading.group(1))
        slug = re.sub(r'[^\w\- ]', '', title.lower()).replace(' ', '-')
        index = counts[slug]
        result.add(slug + (f'-{index}' if index else ''))
        counts[slug] += 1
    return result


def check(root):
    """检查公共根文档及docs／research；返回包含来源行号的问题。"""
    root = Path(root).resolve()
    files = [p for p in root.glob('*.md') if p.is_file()]
    for folder in ('docs', 'research'):
        files.extend((root / folder).rglob('*.md'))
    issues = []
    cache = {}
    for source in sorted(files):
        text = source.read_text(encoding='utf-8-sig')
        # 路径也检查代码块：可复制示例同样必须可移植。
        if source.relative_to(root).parts[0] != 'research':
            for number, line in enumerate(text.splitlines(), 1):
                if MACHINE_PATH.search(line):
                    issues.append(f'{source.relative_to(root)}:{number}: 公共文档包含本机路径，请使用仓库引用或通用参数')
        for number, line in prose_lines(text):
            # 行内代码是标识或示例，不把其中的Markdown形状当链接。
            line = re.sub(r'(`+).*?\1', '', line)
            matches = list(INLINE_LINK.finditer(line))
            reference = REFERENCE.match(line)
            if reference:
                matches.append(reference)
            for match in matches:
                url = match.group(1) or match.group(2)
                parsed = urlsplit(url)
                if parsed.scheme or parsed.netloc:
                    continue
                target = (source.parent / unquote(parsed.path)).resolve() if parsed.path else source
                where = f'{source.relative_to(root)}:{number}'
                if not target.exists():
                    issues.append(f'{where}: 本地目标不存在：{url}')
                elif parsed.fragment and target.is_file() and target.suffix == '.md':
                    if target not in cache:
                        cache[target] = anchors(target.read_text(encoding='utf-8-sig'))
                    if unquote(parsed.fragment) not in cache[target]:
                        issues.append(f'{where}: 标题锚点不存在：{url}')
    # 只要求docs直接模块目录有入口；assets等非Markdown目录不受影响。
    docs = root / 'docs'
    if docs.is_dir():
        for directory in sorted(docs.iterdir()):
            if directory.is_dir() and any(directory.glob('*.md')) and not (directory / 'README.md').is_file():
                issues.append(f'{directory.relative_to(root)}/README.md: 缺少模块入口')
    return issues


def main():
    """从脚本位置解析仓库，便于从任意工作目录运行。"""
    issues = check(Path(__file__).resolve().parents[1])
    for issue in issues:
        print(issue)
    if not issues:
        print('文档链接、标题锚点、模块入口及本机路径检查通过。')
    return bool(issues)


if __name__ == '__main__':
    raise SystemExit(main())
