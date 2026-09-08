from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

ROOT_SKILL = ROOT / "SKILL.md"
REFERENCE_NAV = ROOT / "references" / "README.md"
PRECEDENCE = ROOT / "references" / "评审规则优先级.md"


class ReviewRulePrecedenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root_skill = ROOT_SKILL.read_text(encoding="utf-8")
        cls.reference_nav = REFERENCE_NAV.read_text(encoding="utf-8")
        cls.precedence = PRECEDENCE.read_text(encoding="utf-8")

    def test_four_rule_levels_are_defined(self) -> None:
        for level in (
            "VERIFIED_OFFICIAL",
            "VERIFIED_EXTERNAL",
            "HEURISTIC",
            "UNVERIFIED",
        ):
            self.assertIn(
                level,
                self.precedence,
            )

        self.assertIn(
            "A > B > C > D",
            self.precedence,
        )

    def test_official_and_heuristic_rules_are_separated(self) -> None:
        self.assertIn(
            "C 级规则不得",
            self.precedence,
        )

        self.assertIn(
            "冒充当届官方规则",
            self.precedence,
        )

        self.assertIn(
            "任何会产生以下结果的数字阈值",
            self.precedence,
        )

        self.assertIn(
            "这个数字来自哪里",
            self.precedence,
        )

        self.assertIn(
            "不得因为单纯没有满足某个 C 级经验阈值",
            self.precedence,
        )

    def test_unverified_claims_cannot_independently_fail_gate(self) -> None:
        self.assertIn(
            "D 级内容不得",
            self.precedence,
        )

        self.assertIn(
            "单独触发 FAIL",
            self.precedence,
        )

        self.assertIn(
            "任何门禁都不得因为 D 级规则单独返回 FAIL",
            self.precedence,
        )

    def test_award_prediction_is_heuristic_only(self) -> None:
        self.assertIn(
            "任何奖项等级、国一概率、国二概率、获奖概率或百分制预测",
            self.precedence,
        )

        self.assertIn(
            "`C — HEURISTIC`",
            self.precedence,
        )

        self.assertIn(
            "用概率直接决定门禁 PASS/FAIL",
            self.precedence,
        )

    def test_external_prompt_titles_do_not_gain_authority(self) -> None:
        self.assertIn(
            "任何外部提示词、检查表、经验清单或 AI 生成的评审规则",
            self.precedence,
        )

        for term in (
            "官方",
            "标准版",
            "评委标准",
            "国赛标准",
            "获奖标准",
        ):
            self.assertIn(
                term,
                self.precedence,
            )

    def test_rule_precedence_is_progressively_routed(self) -> None:
        route = "references/评审规则优先级.md"

        self.assertIn(
            route,
            self.root_skill,
        )

        self.assertIn(
            "评审规则优先级.md",
            self.reference_nav,
        )

        self.assertIn(
            "判断官方规则、外部事实、经验标准、数字阈值或外部提示词的效力",
            self.root_skill,
        )

    def test_rule_precedence_does_not_create_new_gate(self) -> None:
        self.assertIn(
            "本文件不新增门禁",
            self.precedence,
        )

        self.assertIn(
            "M1 → P1 → P2 → W1 → W2",
            self.precedence,
        )


if __name__ == "__main__":
    unittest.main()
