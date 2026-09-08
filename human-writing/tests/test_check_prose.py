import contextlib
import importlib.util
import io
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/check_prose.py'
SPEC = importlib.util.spec_from_file_location('checked_prose', SCRIPT)
g = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = g
exec(compile(SCRIPT.read_text(encoding='utf-8'), str(SCRIPT), 'exec'), g.__dict__)


class CheckerTests(unittest.TestCase):
    def check(self, text, *options):
        out, err = io.StringIO(), io.StringIO()
        with patch.object(sys, 'argv', [str(SCRIPT), '-', *options]), patch.object(sys, 'stdin', io.StringIO(text)), contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = g.main()
        return code, out.getvalue(), err.getvalue()

    def test_hard_words_and_visible_text(self):
        for text in ('说白了，就是省钱。', '资料见 https://example.com。说白了，就是省钱。', '这里有<说白了，就是省钱>。', '说到底，我们想回家。', '---\ntitle: 说白了就是省钱\n---\n今天回家。', '---\ncaption: |\n  说白了就是省钱\n---\n今天回家。'):
            with self.subTest(text=text):
                self.assertEqual(self.check(text)[0], 1)

    def test_markdown_code_forms(self):
        for text in ('```python\nif enabled:\n    print("说白了")\n```', '~~~python\nif enabled:\n    print("说白了")\n~~~', '    if enabled:\n        print("说白了")', '``echo `date`: 说白了``', '````text\n```python\nif x:\n```\n````'):
            with self.subTest(text=text):
                self.assertEqual(self.check('这是正文内容。\n\n' + text)[0], 0)

    def test_code_does_not_hide_following_prose(self):
        self.assertEqual(self.check('这是正文。\n~~~\nx: 1\n~~~\n说白了，就是省钱。')[0], 1)

    def test_bom_and_visible_title(self):
        text = '\ufeff---\ntitle: 普通标题\nlayout: post\n---\n今天我们一起回家。'
        self.assertEqual(self.check(text)[0], 0)
        self.assertEqual(self.check(text.replace('普通标题', '说白了'))[0], 1)

    def test_quote_whitespace(self):
        for whitespace in ('', ' ', '  ', '\t', '    '):
            with self.subTest(whitespace=whitespace):
                self.assertEqual(self.check(f'小王说：{whitespace}“明天再来。”')[0], 0)
        self.assertEqual(self.check('核心是：早点回家。')[0], 1)

    def test_semantic_candidates_are_only_warnings(self):
        for text in ('只说对了一半的题目，老师仍然给了部分分数。', '这不是成本问题，是时间问题。', '不只是孩子来了，父母也来了。'):
            with self.subTest(text=text):
                code, out, _ = self.check(text)
                self.assertEqual(code, 0)
                self.assertIn('需要人工判断', out)

    def test_quoted_jargon_is_not_automatically_exempt(self):
        self.assertEqual(self.check('经理说：“我们需要赋能。”')[0], 1)

    def test_preserve_is_explicit_scoped_and_reported(self):
        text = '经理说：“我们需要赋能。”\n今天大家准时下班。'
        code, out, _ = self.check(text, '--preserve-line', '1=有意塑造角色的对白')
        self.assertEqual(code, 0)
        self.assertIn('已人工保留第 1 行', out)
        self.assertEqual(self.check(text + '\n说白了，就是省钱。', '--preserve-line', '1=人物对白')[0], 1)

    def test_preserve_validation(self):
        for value in ('1', '1=', '0=对白', '3=对白', 'a=对白'):
            with self.subTest(value=value):
                self.assertEqual(self.check('今天回家。', '--preserve-line', value)[0], 2)

    def test_input_does_not_grant_itself_exemption(self):
        self.assertEqual(self.check('<!-- preserve-line 2 -->\n说白了，就是省钱。')[0], 1)

    def test_locations_are_preserved(self):
        code, out, _ = self.check('普通标题。\n\n~~~python\na: 1\n~~~\n说白了，就是省钱。')
        self.assertEqual(code, 1)
        self.assertIn('第 6 行', out)

    def test_mask_preserves_positions(self):
        text = '这是正文。\n~~~python\na: 1\n~~~\n链接 https://example.com。今天回家。'
        masked = g.mask_non_prose(text)
        self.assertEqual(len(masked), len(text))
        self.assertEqual([i for i,c in enumerate(masked) if c == '\n'], [i for i,c in enumerate(text) if c == '\n'])

    def test_overlap_keeps_longest_terms(self):
        self.assertEqual(g.non_overlapping_terms('价值闭环闭环价值闭环', ('闭环', '价值闭环')), [(0, '价值闭环'), (4, '闭环'), (6, '价值闭环')])

    def test_metaphor_window_matches_reference(self):
        for text in ('仓库' * 8000, '仓库坍塌血管', '仓库' + '甲' * 900 + '坍塌血管', '仓库' + '甲' * 790 + '坍塌血管'):
            hits = sorted((m.start(), field, word) for field, words in g.METAPHOR_FIELDS.items() for word in words for m in g.re.finditer(word, text))
            expected = None
            # 只有少量非重复样例使用朴素参考实现。
            if len(hits) < 20:
                for start, _, _ in hits:
                    window = [h for h in hits if start <= h[0] <= start + 800]
                    fields = {h[1] for h in window}
                    if len(fields) >= 3:
                        expected = window, fields
                        break
            self.assertEqual(g.metaphor_cluster(text), expected)

    def test_input_limit(self):
        self.assertEqual(self.check('甲' * 2_000_001)[0], 2)


if __name__ == '__main__':
    unittest.main()
