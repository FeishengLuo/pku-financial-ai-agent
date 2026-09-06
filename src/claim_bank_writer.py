"""
claim_bank_writer.py — Claim Bank 证据写回工具
=============================================

把**人工核验后**的证据记录写回 claim_bank_filled.json 的 evidence_list。

硬门控（TODO P1）：每条证据必须带 来源、页码/定位、摘录、口径、核验人；
核验人为空直接拒绝写入——未人工核验的证据不得进入 Claim Bank。

写入语义：
  - 幂等去重：按 excerpt+source 指纹（sha256 前 16 位，与 evidence_ledger 同方案）
  - 原子写盘：临时文件 + os.replace；首次写盘前备份 .bak（不覆盖已有备份）
  - 审计字段：verifier / verified_at / evidence_level / fingerprint 随证据落盘
  - 返回写回报告：成功条数、跳过条数及原因

CLI：
  python -m src.claim_bank_writer --evidence records.json \
      [--bank data/processed/claim_bank_filled.json] [--dry-run]
"""

from __future__ import annotations
import argparse
import hashlib
import json
import os
import sys
import tempfile
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.evidence_ledger import EvidenceLevel, SOURCE_KEYWORDS

REQUIRED_FIELDS = ("claim_id", "source", "locator", "excerpt", "caliber", "verifier")

SKIP_UNKNOWN_CLAIM = "claim_id 不存在"
SKIP_MISSING_FIELD = "缺少必填字段"
SKIP_EMPTY_VERIFIER = "核验人为空（未经人工核验，拒绝写入）"
SKIP_DUPLICATE = "证据指纹重复（幂等跳过）"


def classify_level(text: str) -> EvidenceLevel:
    """按来源关键词自动分类证据等级（复用 evidence_ledger.SOURCE_KEYWORDS）。"""
    if not text:
        return EvidenceLevel.UNKNOWN
    text_lower = text.lower()
    for keyword, level in SOURCE_KEYWORDS:
        if keyword.lower() in text_lower:
            return level
    return EvidenceLevel.UNKNOWN


def evidence_fingerprint(excerpt: str, source: str) -> str:
    """证据指纹：excerpt+source 的 sha256 前 16 位。"""
    return hashlib.sha256(f"{excerpt}||{source}".encode("utf-8")).hexdigest()[:16]


def load_bank(bank_path: Path) -> List[Dict[str, Any]]:
    with open(bank_path, encoding="utf-8") as f:
        bank = json.load(f)
    if not isinstance(bank, list):
        raise ValueError(f"{bank_path} 应为 claim 列表（JSON array）")
    return bank


def _validate_record(record: Dict[str, Any]) -> Optional[str]:
    """返回跳过原因；None 表示通过校验。"""
    for field in REQUIRED_FIELDS:
        if field not in record or record[field] is None or not str(record[field]).strip():
            if field == "verifier":
                return SKIP_EMPTY_VERIFIER
            return f"{SKIP_MISSING_FIELD}: {field}"
    return None


def writeback(
    records: List[Dict[str, Any]],
    bank_path: Path,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    将核验后的证据记录写回 Claim Bank。

    Args:
        records: 证据记录列表，每条须含 REQUIRED_FIELDS 全部字段
        bank_path: claim_bank_filled.json 路径
        dry_run: True 时只出报告，不改文件（也不做备份）

    Returns:
        {"written": int, "skipped": [{"record": ..., "reason": ...}], "dry_run": bool}
    """
    bank_path = Path(bank_path)
    bank = load_bank(bank_path)
    claims = {c.get("claim_id"): c for c in bank if isinstance(c, dict)}
    today = date.today().isoformat()

    skipped: List[Dict[str, Any]] = []
    staged: List[Dict[str, Any]] = []  # (claim_id, entry) 待写入

    for record in records:
        reason = _validate_record(record)
        if reason:
            skipped.append({"record": record, "reason": reason})
            continue

        claim_id = str(record["claim_id"]).strip()
        claim = claims.get(claim_id)
        if claim is None:
            skipped.append({"record": record, "reason": SKIP_UNKNOWN_CLAIM})
            continue

        excerpt = str(record["excerpt"]).strip()
        source = str(record["source"]).strip()
        fp = evidence_fingerprint(excerpt, source)

        evidence_list = claim.setdefault("evidence_list", [])
        if any(e.get("fingerprint") == fp for e in evidence_list if isinstance(e, dict)):
            skipped.append({"record": record, "reason": SKIP_DUPLICATE})
            continue

        level_str = str(record.get("evidence_level") or "").strip()
        if level_str:
            try:
                level = EvidenceLevel(level_str).value
            except ValueError:
                level = classify_level(f"{source} {excerpt}").value
        else:
            level = classify_level(f"{source} {excerpt}").value

        staged.append((claim_id, {
            "source": source,
            "locator": str(record["locator"]).strip(),
            "excerpt": excerpt,
            "caliber": str(record["caliber"]).strip(),
            "verifier": str(record["verifier"]).strip(),
            "verified_at": str(record.get("verified_at") or today),
            "evidence_level": level,
            "fingerprint": fp,
        }))

    if not dry_run:
        for claim_id, entry in staged:
            claims[claim_id]["evidence_list"].append(entry)

        # 首次写盘前备份原文件（不覆盖已有备份）
        backup = bank_path.with_suffix(bank_path.suffix + ".bak")
        if not backup.exists():
            backup.write_bytes(bank_path.read_bytes())

        # 原子写盘
        fd, tmp_name = tempfile.mkstemp(
            dir=str(bank_path.parent), prefix=bank_path.name, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(bank, f, ensure_ascii=False, indent=2)
                f.write("\n")
            os.replace(tmp_name, bank_path)
        except BaseException:
            os.unlink(tmp_name)
            raise

    return {"written": len(staged), "skipped": skipped, "dry_run": dry_run}


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="将人工核验后的证据写回 Claim Bank（核验人必填，幂等去重）")
    parser.add_argument("--evidence", required=True, help="证据记录 JSON 文件路径")
    parser.add_argument("--bank", default="data/processed/claim_bank_filled.json",
                        help="Claim Bank 路径")
    parser.add_argument("--dry-run", action="store_true", help="只出报告，不改文件")
    args = parser.parse_args(argv)

    with open(args.evidence, encoding="utf-8") as f:
        records = json.load(f)
    if isinstance(records, dict):
        records = [records]

    report = writeback(records, Path(args.bank), dry_run=args.dry_run)
    print(f"写回 {report['written']} 条，跳过 {len(report['skipped'])} 条"
          f"（{'dry-run，未改文件' if report['dry_run'] else '已落盘'}）")
    for item in report["skipped"]:
        print(f"  跳过: {item['reason']} | {json.dumps(item['record'], ensure_ascii=False)[:120]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
