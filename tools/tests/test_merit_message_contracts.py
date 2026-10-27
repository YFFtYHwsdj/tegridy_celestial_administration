"""功绩简报与原生消息模板的连接契约；不模拟铨叙业务或界面渲染。"""
from pathlib import Path
import unittest

from check_upstream_overrides import definitions

ROOT = Path(__file__).resolve().parents[2]


class MeritMessageContractTests(unittest.TestCase):
    def test_briefing_template_consumes_the_rendered_effect_description(self):
        # 原版 common/messages/00_messages.txt 的 event_generic_*_text 用此占位键，
        # messages_l_* 中它为 $DESCRIPTION$。直接绑定摘要会在消息数据上下文
        # 再求值 TopScope，导致发送效果已有数值而界面人数为空。
        messages = definitions((ROOT / 'common/messages/tca_merit_feedback_messages.txt').read_text(encoding='utf-8-sig'))
        briefing = messages['tca_merit_feedback_emperor_briefing']
        desc_at = briefing.index('desc')
        self.assertEqual(briefing[desc_at:desc_at + 3], ['desc', '=', 'event_message_text'])
