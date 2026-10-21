"""以真实临时文档验证迁移断链、锚点及模块入口检查。"""

from pathlib import Path
import tempfile
import unittest

from check_docs import check


class DocumentationChecks(unittest.TestCase):
    """遗漏任一检查都应被对应的故障文档检出。"""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def write(self, path, text):
        """创建独立测试文档，不依赖真实仓库内容。"""
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding='utf-8')

    def test_moved_target_reports_source_line(self):
        self.write('README.md', '# 入口\n\n[旧页](docs/old.md)\n')
        issues = check(self.root)
        self.assertEqual(len(issues), 1)
        self.assertIn('README.md:3', issues[0])
        self.assertIn('docs/old.md', issues[0])

    def test_anchor_is_checked_even_when_file_exists(self):
        self.write('README.md', '[旧节](docs/module/README.md#旧节)\n')
        self.write('docs/module/README.md', '# 模块\n\n## 新节\n')
        issues = check(self.root)
        self.assertEqual(len(issues), 1)
        self.assertIn('旧节', issues[0])

    def test_valid_unicode_duplicate_heading_and_encoded_path(self):
        self.write('README.md', '[本页](#入口) [中文](docs/module/README.md#当前行为-1)\n# 入口\n')
        self.write('docs/module/README.md', '# 模块\n## 当前行为\n## 当前行为\n[文件](note%20one.md)\n')
        self.write('docs/module/note one.md', '# 说明\n')
        self.assertEqual(check(self.root), [])

    def test_examples_inline_code_and_remote_links_are_not_local_targets(self):
        self.write('README.md', '# 文档\n```md\n[样例](missing.md)\n```\n`[代码](missing.md)`\n[网页](https://example.invalid/a#b)\n')
        self.assertEqual(check(self.root), [])

    def test_module_requires_readme(self):
        self.write('docs/module/design.md', '# 设计\n')
        issues = check(self.root)
        self.assertEqual(len(issues), 1)
        self.assertIn('docs/module/README.md', issues[0])

    def test_missing_reference_definition_target(self):
        self.write('README.md', '[入口][module]\n\n[module]: docs/missing.md\n')
        issues = check(self.root)
        self.assertEqual(len(issues), 1)
        self.assertIn('README.md:3', issues[0])


    def test_docs_reject_machine_paths_even_in_code_examples(self):
        self.write('docs/module/README.md', '# 模块\n```sh\n--run-root /private/tmp/session/run-old\n```\n')
        issues = check(self.root)
        self.assertEqual(len(issues), 1)
        self.assertIn('README.md:3', issues[0])
        self.assertIn('本机路径', issues[0])

    def test_public_docs_reject_personal_home_but_allow_portable_placeholder(self):
        self.write('README.md', '# 入口\n原始日志在 /Users/example/Desktop/logs/ 。\n')
        self.write('docs/module/README.md', '# 模块\n`--run-root "<仓库外持久产物目录>"`\n')
        issues = check(self.root)
        self.assertEqual(len(issues), 1)
        self.assertIn('README.md:2', issues[0])


class RepositoryDocumentationChecks(unittest.TestCase):
    """默认工具回归直接检查当前仓库，避免只验证检查器的临时样例。"""

    def test_repository_documents_have_no_issues(self):
        root = Path(__file__).resolve().parents[2]
        issues = check(root)
        self.assertEqual(issues, [], '\n'.join(issues))


if __name__ == '__main__':
    unittest.main()
