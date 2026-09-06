"""claim_verifier 无 LLM 配置时的保守降级回归测试。

背景：verify() 在有证据但无 Prism 配置时，llm_config 惰性加载会抛
RuntimeError 导致整个验证崩溃。修复后应降级为纯规则层结论。
"""
from __future__ import annotations

import pytest

from src import claim_verifier
from src.claim_verifier import ClaimVerifier


CLAIM = "绿的谐波2024年谐波减速器销量24.65万台，同比增长16.56%"
SOURCE = "国信证券研报：2024年谐波减速器及金属部件收入3.25亿元，销量24.65万台"


@pytest.fixture
def no_prism(monkeypatch):
    """模拟 Prism 配置缺失。"""
    def _raise():
        raise RuntimeError("找不到 Prism 配置")
    monkeypatch.setattr(claim_verifier, "load_prism_config", _raise)
    return ClaimVerifier()


def test_verify_without_llm_config_does_not_crash(no_prism):
    out = no_prism.verify(CLAIM, SOURCE)
    assert out.verdict_source == "rule_only_fallback"
    assert out.verdict in {"refuted", "partially_supported", "definition_mismatch",
                           "low_confidence", "abstain"}


def test_verify_fallback_marks_llm_skipped(no_prism):
    out = no_prism.verify(CLAIM, SOURCE)
    assert "配置缺失" in out.reasoning
    assert out.llm_verdict is None
    assert out.elapsed_ms >= 0


def test_verify_fallback_keeps_rule_flags(no_prism):
    out = no_prism.verify(CLAIM, SOURCE)
    assert isinstance(out.rule_flags, list)
    assert out.rule_result is not None
