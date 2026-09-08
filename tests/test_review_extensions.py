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




class ModelingAndResultReviewExtensionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.model_role = (
            ROOT
            / "references"
            / "roles"
            / "建模手"
            / "SKILL.md"
        ).read_text(encoding="utf-8")

        cls.model_review = (
            ROOT
            / "references"
            / "roles"
            / "建模手"
            / "references"
            / "模型适配性终检.md"
        ).read_text(encoding="utf-8")

        cls.program_role = (
            ROOT
            / "references"
            / "roles"
            / "编程手"
            / "SKILL.md"
        ).read_text(encoding="utf-8")

        cls.result_review = (
            ROOT
            / "references"
            / "roles"
            / "编程手"
            / "references"
            / "结果可靠性终检.md"
        ).read_text(encoding="utf-8")

    def test_m1_extension_is_routed_only_to_m1(self) -> None:
        self.assertIn(
            "模型适配性终检.md",
            self.model_role,
        )

        self.assertIn(
            "执行 `M1` 时",
            self.model_role,
        )

        self.assertIn(
            "本文件只在执行 `M1` 时加载",
            self.model_review,
        )

    def test_m1_separates_design_from_actual_results(self) -> None:
        self.assertIn(
            "M1 不负责证明",
            self.model_review,
        )

        self.assertIn(
            "这些属于 P1/P2",
            self.model_review,
        )

        self.assertIn(
            "验证计划",
            self.model_review,
        )

    def test_m1_does_not_require_complexity_or_fake_innovation(self) -> None:
        self.assertIn(
            "模型简单或复杂都不是独立优缺点",
            self.model_review,
        )

        self.assertIn(
            "不得为了满足所谓“必须创新”而制造伪创新",
            self.model_review,
        )

        self.assertIn(
            "没有所谓“必须 2–3 个创新点”的规则",
            self.model_review,
        )

    def test_p2_extension_is_routed_only_to_p2(self) -> None:
        self.assertIn(
            "结果可靠性终检.md",
            self.program_role,
        )

        self.assertIn(
            "执行 `P2` 时",
            self.program_role,
        )

        self.assertIn(
            "本文件只在执行 `P2` 时加载",
            self.result_review,
        )

    def test_p2_requires_actual_execution_evidence(self) -> None:
        self.assertIn(
            "真实数据、真实代码和真实运行结果",
            self.result_review,
        )

        self.assertIn(
            "唯一复现命令",
            self.result_review,
        )

        self.assertIn(
            "输入 → 代码 → 结果文件 → 图/表 → 论文主张",
            self.result_review,
        )

    def test_p2_checks_model_code_consistency(self) -> None:
        self.assertIn(
            "M1 模型合同与代码一致性",
            self.result_review,
        )

        self.assertIn(
            "代码不得实现另一套模型",
            self.result_review,
        )

        self.assertIn(
            "约束实际执行",
            self.result_review,
        )

    def test_p2_conditional_checks_are_not_universal_requirements(self) -> None:
        for phrase in (
            "每个模型都必须交叉验证",
            "每个参数都必须敏感性分析",
            "每个模型都必须超参数调优",
            "每个子问题都必须建立基线",
            "每个模型都必须泛化测试",
        ):
            self.assertIn(
                phrase,
                self.result_review,
            )

        self.assertIn(
            "不能作为所有项目的统一硬要求",
            self.result_review,
        )

    def test_extensions_preserve_original_five_gates(self) -> None:
        self.assertIn(
            "M1 → P1 → P2 → W1 → W2",
            self.model_review,
        )

        self.assertIn(
            "M1 → P1 → P2 → W1 → W2",
            self.result_review,
        )


class ReviewLayerSeparationTests(unittest.TestCase):
    def test_m1_extension_does_not_replace_author_self_check(self) -> None:
        review = (
            ROOT
            / "references"
            / "roles"
            / "建模手"
            / "references"
            / "模型适配性终检.md"
        ).read_text(encoding="utf-8")

        self.assertIn(
            "不替代",
            review,
        )
        self.assertIn(
            "建模手作者自检",
            review,
        )

    def test_p2_extension_does_not_replace_mechanical_audits(self) -> None:
        review = (
            ROOT
            / "references"
            / "roles"
            / "编程手"
            / "references"
            / "结果可靠性终检.md"
        ).read_text(encoding="utf-8")

        self.assertIn(
            "不替代",
            review,
        )
        self.assertIn(
            "图表机械审计",
            review,
        )


if __name__ == "__main__":
    unittest.main()
