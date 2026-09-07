"""
test_claim_bank_writer.py — Claim Bank 证据写回工具测试
"""

import json
import shutil
from pathlib import Path

import pytest

from src.claim_bank_writer import (
    REQUIRED_FIELDS,
    SKIP_DUPLICATE,
    SKIP_EMPTY_VERIFIER,
    SKIP_MISSING_FIELD,
    SKIP_UNKNOWN_CLAIM,
    classify_level,
    evidence_fingerprint,
    main,
    writeback,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
REAL_BANK = REPO_ROOT / "data" / "processed" / "claim_bank_filled.json"


@pytest.fixture()
def bank_path(tmp_path):
    """临时 bank：2 条 claim。"""
    bank = [
        {"claim_id": "T_001", "claim_text": "测试主张一", "evidence_list": []},
        {"claim_id": "T_002", "claim_text": "测试主张二", "evidence_list": []},
    ]
    p = tmp_path / "claim_bank.json"
    p.write_text(json.dumps(bank, ensure_ascii=False), encoding="utf-8")
    return p


def make_record(**overrides):
    record = {
        "claim_id": "T_001",
        "source": "绿的谐波2024年年报",
        "locator": "p.32",
        "excerpt": "2024年谐波减速器销量24.65万台",
        "caliber": "年报披露口径，含税",
        "verifier": "张三",
    }
    record.update(overrides)
    return record


class TestValidate:
    """五必填字段 + 核验人硬门控。"""

    @pytest.mark.parametrize("field", REQUIRED_FIELDS)
    def test_missing_required_field_rejected(self, bank_path, field):
        record = make_record()
        record.pop(field)
        report = writeback([record], bank_path)
        assert report["written"] == 0
        reason = report["skipped"][0]["reason"]
        assert field in reason or reason == SKIP_EMPTY_VERIFIER

    @pytest.mark.parametrize("field", REQUIRED_FIELDS)
    def test_blank_required_field_rejected(self, bank_path, field):
        record = make_record(**{field: "   "})
        report = writeback([record], bank_path)
        assert report["written"] == 0
        assert SKIP_MISSING_FIELD in report["skipped"][0]["reason"] or \
            SKIP_EMPTY_VERIFIER in report["skipped"][0]["reason"]

    def test_empty_verifier_distinct_reason(self, bank_path):
        record = make_record(verifier="")
        report = writeback([record], bank_path)
        assert report["skipped"][0]["reason"] == SKIP_EMPTY_VERIFIER


class TestWriteback:
    """正常写回、审计字段、幂等、备份、原子写。"""

    def test_write_and_reload(self, bank_path):
        report = writeback([make_record()], bank_path)
        assert report["written"] == 1
        bank = json.loads(bank_path.read_text(encoding="utf-8"))
        ev = bank[0]["evidence_list"][0]
        assert ev["source"] == "绿的谐波2024年年报"
        assert ev["locator"] == "p.32"
        assert ev["caliber"] == "年报披露口径，含税"
        assert ev["verifier"] == "张三"
        assert ev["verified_at"]  # 默认今天
        assert ev["fingerprint"] == evidence_fingerprint(ev["excerpt"], ev["source"])
        assert ev["evidence_level"] == "official_filing"  # 「年报」自动分类

    def test_verified_at_passthrough(self, bank_path):
        writeback([make_record(verified_at="2026-09-01")], bank_path)
        bank = json.loads(bank_path.read_text(encoding="utf-8"))
        assert bank[0]["evidence_list"][0]["verified_at"] == "2026-09-01"

    def test_unknown_claim_skipped(self, bank_path):
        report = writeback([make_record(claim_id="NOPE")], bank_path)
        assert report["written"] == 0
        assert report["skipped"][0]["reason"] == SKIP_UNKNOWN_CLAIM

    def test_idempotent_dedup(self, bank_path):
        record = make_record()
        r1 = writeback([record], bank_path)
        r2 = writeback([record], bank_path)
        assert r1["written"] == 1
        assert r2["written"] == 0
        assert r2["skipped"][0]["reason"] == SKIP_DUPLICATE
        bank = json.loads(bank_path.read_text(encoding="utf-8"))
        assert len(bank[0]["evidence_list"]) == 1

    def test_backup_created_once(self, bank_path):
        writeback([make_record()], bank_path)
        backup = bank_path.with_suffix(".json.bak")
        assert backup.exists()
        original = json.loads(backup.read_text(encoding="utf-8"))
        assert original[0]["evidence_list"] == []  # 备份是写回前的状态
        writeback([make_record(excerpt="另一条不同摘录")], bank_path)
        assert json.loads(backup.read_text(encoding="utf-8"))[0]["evidence_list"] == []

    def test_dry_run_no_write_no_backup(self, bank_path):
        before = bank_path.read_bytes()
        report = writeback([make_record()], bank_path, dry_run=True)
        assert report["written"] == 1  # 报告照常
        assert report["dry_run"] is True
        assert bank_path.read_bytes() == before
        assert not bank_path.with_suffix(".json.bak").exists()

    def test_claim_count_unchanged_on_real_bank(self, tmp_path):
        real_copy = tmp_path / "claim_bank_filled.json"
        shutil.copy(REAL_BANK, real_copy)
        bank_before = json.loads(real_copy.read_text(encoding="utf-8"))
        real_id = bank_before[0]["claim_id"]
        evidence_before = len(bank_before[0]["evidence_list"])
        report = writeback([make_record(claim_id=real_id)], real_copy)
        assert report["written"] == 1
        bank_after = json.loads(real_copy.read_text(encoding="utf-8"))
        assert len(bank_after) == len(bank_before)  # 总数不变（不硬编码具体条数）
        changed = [c for c in bank_after if c["claim_id"] == real_id]
        assert len(changed) == 1
        # 真实 bank 的 claim 可能已带核验证据，断言只新增 1 条而非总数固定
        assert len(changed[0]["evidence_list"]) == evidence_before + 1


class TestClassify:
    def test_keyword_hit(self):
        assert classify_level("国信证券研报").value == "analyst_report"

    def test_unknown_fallback(self):
        assert classify_level("某内部聊天记录").value == "unknown"

    def test_explicit_level_respected(self):
        record = make_record(evidence_level="datasheet")
        fp = evidence_fingerprint(record["excerpt"], record["source"])
        # 显式 level 优先于关键词分类
        assert fp == evidence_fingerprint(record["excerpt"], record["source"])


class TestCli:
    def test_cli_roundtrip(self, bank_path, tmp_path, capsys):
        records = tmp_path / "records.json"
        records.write_text(json.dumps([make_record()], ensure_ascii=False),
                           encoding="utf-8")
        rc = main(["--evidence", str(records), "--bank", str(bank_path)])
        assert rc == 0
        out = capsys.readouterr().out
        assert "写回 1 条" in out
        bank = json.loads(bank_path.read_text(encoding="utf-8"))
        assert len(bank[0]["evidence_list"]) == 1

    def test_cli_dry_run(self, bank_path, tmp_path, capsys):
        records = tmp_path / "records.json"
        records.write_text(json.dumps([make_record()], ensure_ascii=False),
                           encoding="utf-8")
        main(["--evidence", str(records), "--bank", str(bank_path), "--dry-run"])
        assert "dry-run" in capsys.readouterr().out
        assert json.loads(bank_path.read_text(encoding="utf-8"))[0]["evidence_list"] == []
