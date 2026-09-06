"""
engineering_analyzer.py — Claim2Value 工程参数口径归一化器
===========================================================

这是「技术创新」规则层的第二个模块，与 state_verifier 互补：

问题：
    机器人关节产业链（谐波减速器 / RV 减速器 / 无框力矩电机 / 关节模组）
    的参数对比中，不同厂商 datasheet 混用多种口径：
    1. 额定扭矩 vs 峰值扭矩（量级可差 2-3 倍，见 state_verifier 注册表）
    2. 电机本体参数 vs 含减速器的整个关节模组参数（差一个减速比）
    3. 直接披露 vs 待补充/缺失字段
    直接横向比较会得到系统性错误的"技术领先"结论。

方案：
    把所有扭矩/功率密度声明归一化到统一口径（连续额定工况、N·m/kg、W/kg），
    每个换算系数都是显式 dataclass 字段（带工程依据注释），可审计、可覆盖；
    归一化结果标注每个字段是「实测 / 推算 / 缺失」，并给出可比性等级
    （comparable / approximate / not_comparable），供 economic_mapper 消费。

用法：
    from src.engineering_analyzer import (
        load_and_normalize, normalize_torque, ConversionFactors,
        OperatingPoint, AssemblyScope, Comparability,
    )

    params = load_and_normalize()  # 默认读取 parameter_table_filled.csv
    for p in params:
        print(p.model, p.torque_nm, p.torque_density_nm_kg, p.comparability)

设计原则：
    - 全程无网络、无 LLM、无第三方依赖（仅标准库）
    - 缺失值/单位异常/非数值输入不抛裸异常，返回带 errors 说明的结构化结果
    - 数值统一 4 位有效数字，避免二进制浮点噪声进入下游比较
"""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PARAMETER_CSV = REPO_ROOT / "data" / "processed" / "parameter_table_filled.csv"


# ============================================================
# 口径枚举
# ============================================================

class OperatingPoint(str, Enum):
    """扭矩/功率声明的工况口径"""
    RATED = "rated"            # 额定扭矩 = 可持续连续工作的扭矩
    PEAK = "peak"              # 峰值扭矩 = 允许短时达到的瞬时最大扭矩
    UNKNOWN = "unknown"        # 声明中未标注工况


class AssemblyScope(str, Enum):
    """参数所描述的产品范围（电机 vs 模组口径）"""
    MOTOR_BODY = "motor_body"      # 电机本体（无减速器）
    JOINT_MODULE = "joint_module"  # 含减速器的关节模组/执行器
    GEAR_UNIT = "gear_unit"        # 纯减速器（无电机，如谐波/RV 减速器单体）
    UNKNOWN = "unknown"


class Comparability(str, Enum):
    """归一化结果的可比性等级（供 economic_mapper 决定能否直接进入价值映射）"""
    COMPARABLE = "comparable"          # 口径已统一、关键字段齐全，可直接比较
    APPROXIMATE = "approximate"        # 含推算值/口径修正，可比较但需标注不确定性
    NOT_COMPARABLE = "not_comparable"  # 关键字段缺失或口径无法确定，不可用于量化比较


# ============================================================
# 换算系数注册表：显式、有默认值、可审计
# ============================================================

@dataclass(frozen=True)
class ConversionFactors:
    """
    口径换算系数。每个系数都是一条显式的、可审计的模型假设，
    实例化时可整体或逐字段覆盖（如某厂商 datasheet 明确给出峰值倍数）。

    工程依据：
      peak_to_rated_torque —— 峰值扭矩 → 额定扭矩的折减系数。
          依据 1：state_verifier 定义注册表注明额定/峰值扭矩"量级可差 2-3 倍"，
          取倒数中值 ≈ 0.5 作为缺省。
          依据 2：本仓库 parameter_table_filled.csv 实际披露的 rated/peak 比值
          介于 0.27（CSF-20-100）至 0.56（CSG-32）之间，说明该系数产品间
          离散度大（不确定度高），凡使用此系数的行可比性最高只能评
          approximate。
      gear_efficiency —— 经减速器反推电机本体扭矩时使用的传动效率。
          依据：parameter_table_filled.csv 中谐波减速器效率典型值 80%，
          RV 减速器约 90%；取保守值 0.80。仅在 module→motor 反推时使用，
          不确定度直接随减速比放大，反推行一律评 approximate。
      rated_equals_peak_tolerance —— 「额定==峰值」疑似口径混填的检测阈值：
          peak ≤ rated × (1 + tolerance) 时判定两值实质相同，疑似把同一数值
          重复填入两个口径列（真实峰值扭矩通常显著大于额定），触发数据质量
          警告并把可比性降级为 approximate。
    """
    peak_to_rated_torque: float = 0.5
    gear_efficiency: float = 0.80
    rated_equals_peak_tolerance: float = 0.05


DEFAULT_FACTORS = ConversionFactors()

# 扭矩单位 → N·m 的换算系数（含常见 datasheet 写法）
TORQUE_UNIT_TO_NM: Dict[str, float] = {
    "nm": 1.0, "n·m": 1.0, "n.m": 1.0, "n.m.": 1.0,
    "ncm": 0.01, "n·cm": 0.01, "n.cm": 0.01,
    "kgf·cm": 0.0980665, "kgf.cm": 0.0980665, "kgfcm": 0.0980665,
    "kgf·m": 9.80665, "kgf.m": 9.80665,
}

# 功率密度单位 → W/kg 的换算系数
POWER_DENSITY_UNIT_TO_W_PER_KG: Dict[str, float] = {
    "w/kg": 1.0, "w·kg-1": 1.0, "w/kg": 1.0,
    "kw/kg": 1000.0, "kw·kg-1": 1000.0,
}

# CSV 中的缺失值哨兵
MISSING_SENTINELS = {"", "-", "--", "—", "n/a", "na", "none", "null", "待补充", "暂无", "未披露"}


# ============================================================
# 归一化结果
# ============================================================

@dataclass
class NormalizedParameter:
    """
    一行参数归一化后的结构化结果。

    provenance 字段说明每个输出值的数据来源性质：
      "实测：..."   —— datasheet 直接披露，未做换算
      "推算：..."   —— 由实测值经显式系数换算得到（系数记录在 adjustments）
      "缺失"        —— 原始数据缺失且无法推算
    """
    company: str
    product_series: str
    model: str
    scope: AssemblyScope                        # 电机本体 / 关节模组 / 纯减速器
    torque_nm: Optional[float] = None           # 归一化到连续额定工况的扭矩（N·m）
    torque_density_nm_kg: Optional[float] = None    # 扭矩密度（N·m/kg）
    power_density_w_kg: Optional[float] = None      # 功率密度（W/kg）
    operating_point_raw: OperatingPoint = OperatingPoint.UNKNOWN  # 原始声明工况
    adjustments: List[Dict] = field(default_factory=list)   # 应用的调整系数（含依据）
    provenance: Dict[str, str] = field(default_factory=dict)
    missing_fields: List[str] = field(default_factory=list)
    comparability: Comparability = Comparability.NOT_COMPARABLE
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    source_url: str = ""
    notes: str = ""

    def to_dict(self) -> Dict:
        """序列化为字典，供 economic_mapper / 报告层直接消费。"""
        return {
            "company": self.company,
            "product_series": self.product_series,
            "model": self.model,
            "scope": self.scope.value,
            "torque_nm": self.torque_nm,
            "torque_density_nm_kg": self.torque_density_nm_kg,
            "power_density_w_kg": self.power_density_w_kg,
            "operating_point_raw": self.operating_point_raw.value,
            "adjustments": self.adjustments,
            "provenance": self.provenance,
            "missing_fields": self.missing_fields,
            "comparability": self.comparability.value,
            "errors": self.errors,
            "warnings": self.warnings,
            "source_url": self.source_url,
            "notes": self.notes,
        }


# ============================================================
# 数值工具
# ============================================================

def _round_sig(value: float, sig: int = 4) -> float:
    """四舍五入到 sig 位有效数字，避免二进制浮点噪声进入下游比较。"""
    if value == 0 or not math.isfinite(value):
        return 0.0
    return round(value, -int(math.floor(math.log10(abs(value)))) + (sig - 1))


def parse_numeric(raw: object) -> Optional[float]:
    """
    防御性数值解析。返回 None 表示缺失（含「待补充」等哨兵、非数值、
    非有限值），绝不抛异常。
    """
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        value = float(raw)
        return value if math.isfinite(value) else None
    text = str(raw).strip()
    if text.lower() in MISSING_SENTINELS:
        return None
    # 去掉常见千分位与尾随单位说明（如 "2.5kg"）
    text = text.replace(",", "")
    try:
        value = float(text)
    except ValueError:
        # 尝试提取开头的纯数值（"2.5kg" → 2.5）
        import re
        match = re.match(r"^(-?\d+\.?\d*)", text)
        if not match:
            return None
        try:
            value = float(match.group(1))
        except ValueError:
            return None
    return value if math.isfinite(value) else None


def convert_unit(value: float, unit: str, table: Dict[str, float]) -> Tuple[Optional[float], Optional[str]]:
    """
    单位换算。返回 (换算后值, 错误说明)；单位无法识别时返回 (None, 错误说明)，不抛异常。
    """
    key = unit.strip().lower().replace(" ", "")
    if key in table:
        return value * table[key], None
    return None, f"无法识别的单位「{unit}」，支持：{sorted(table)}"


# ============================================================
# 纯函数：单值口径换算
# ============================================================

def normalize_torque(
    torque_nm: float,
    from_point: OperatingPoint = OperatingPoint.RATED,
    to_point: OperatingPoint = OperatingPoint.RATED,
    factors: ConversionFactors = DEFAULT_FACTORS,
) -> float:
    """
    把扭矩值从一个工况口径换算到另一个口径的纯函数。

    当前支持的换算：
      PEAK → RATED：乘以 factors.peak_to_rated_torque（默认 0.5）
    同口径换算为恒等；不支持的换算方向抛 ValueError（属于编程错误，
    调用方应在入口处确定口径，而不是数据缺陷）。
    """
    if from_point == to_point:
        return torque_nm
    if from_point == OperatingPoint.PEAK and to_point == OperatingPoint.RATED:
        return torque_nm * factors.peak_to_rated_torque
    raise ValueError(f"不支持的扭矩口径换算：{from_point.value} → {to_point.value}")


def torque_conversion_basis(factors: ConversionFactors = DEFAULT_FACTORS) -> str:
    """峰值→额定换算系数的工程依据说明（写入 adjustments 供审计）。"""
    return (
        f"峰值扭矩×{factors.peak_to_rated_torque}→额定扭矩；依据：额定/峰值"
        f"量级差 2-3 倍（state_verifier 定义注册表），CSV 实测比值 0.27-0.56，"
        f"产品间离散度大，使用此系数的比较应视为近似"
    )


def infer_scope(product_series: str, notes: str = "", model: str = "") -> AssemblyScope:
    """
    从产品系列名/备注推断参数范围口径（电机本体 / 关节模组 / 纯减速器）。

    依据产品命名惯例：
      模组/执行器/关节 → 含减速器的关节模组
      FMK/无框/力矩电机/马达 → 电机本体
      谐波/RV/LHS/LCS/CSG/CSF/LHT/SHPR/减速器 → 纯减速器
    无法判断时返回 UNKNOWN（调用方应显式传 scope 参数）。
    """
    text = f"{product_series} {model} {notes}"
    if any(k in text for k in ("模组", "执行器", "关节")):
        return AssemblyScope.JOINT_MODULE
    if any(k in text for k in ("FMK", "无框", "力矩电机", "马达")):
        return AssemblyScope.MOTOR_BODY
    if any(k in text for k in ("谐波", "RV", "LHS", "LCS", "CSG", "CSF", "LHT", "SHPR", "减速器")):
        return AssemblyScope.GEAR_UNIT
    return AssemblyScope.UNKNOWN


def back_calculate_motor_torque(
    module_torque_nm: float,
    reduction_ratio: float,
    factors: ConversionFactors = DEFAULT_FACTORS,
) -> Tuple[Optional[float], Optional[str]]:
    """
    从关节模组（或减速器输出端）扭矩反推电机本体扭矩：
        motor_torque = module_torque / (reduction_ratio × gear_efficiency)

    返回 (反推值, 错误说明)。减速比缺失/非正时返回 (None, 说明)，不抛异常。
    反推结果的不确定度随减速比放大（效率误差 × 减速比），应一律评 approximate。
    """
    ratio = parse_numeric(reduction_ratio)
    if ratio is None or ratio <= 0:
        return None, "缺少有效的减速比，无法从模组扭矩反推电机本体扭矩"
    motor = module_torque_nm / (ratio * factors.gear_efficiency)
    return _round_sig(motor), None


# ============================================================
# 行级归一化
# ============================================================

def normalize_parameter_row(
    row: Dict[str, object],
    factors: ConversionFactors = DEFAULT_FACTORS,
    scope: Optional[AssemblyScope] = None,
    reduction_ratio: Optional[float] = None,
) -> NormalizedParameter:
    """
    把一行参数（dict，键名对齐 parameter_table_filled.csv 列名）归一化到
    连续额定工况。CSV 列名即单位约定（rated_torque_nm 单位是 N·m，
    weight_kg 单位是 kg，torque_density_nm_kg 单位是 N·m/kg），
    若从其他来源读入带自由单位文本的数据，请先用 convert_unit 归一。

    Args:
        row: 参数字典，至少含 company/product_series/model；
             数值键缺失或非数值时按「缺失」处理，不抛异常。
        factors: 换算系数（可覆盖默认值）
        scope: 显式指定口径范围；为 None 时用 infer_scope 推断
        reduction_ratio: 减速比；提供且 scope 推断/指定为电机本体反推场景时，
             用 back_calculate_motor_torque 反推电机本体扭矩

    Returns:
        NormalizedParameter，含 provenance / adjustments / comparability
    """
    company = str(row.get("company", "") or "").strip()
    product_series = str(row.get("product_series", "") or "").strip()
    model = str(row.get("model", "") or "").strip()
    notes = str(row.get("notes", "") or "").strip()

    result = NormalizedParameter(
        company=company,
        product_series=product_series,
        model=model,
        scope=scope if scope is not None else infer_scope(product_series, notes, model),
        source_url=str(row.get("source_url", "") or "").strip(),
        notes=notes,
    )

    rated = parse_numeric(row.get("rated_torque_nm"))
    peak = parse_numeric(row.get("peak_torque_nm"))
    weight = parse_numeric(row.get("weight_kg"))
    density = parse_numeric(row.get("torque_density_nm_kg"))
    power_density = parse_numeric(row.get("power_density_w_kg"))

    # ── 原始数据合法性检查 ──
    for name, value in (("rated_torque_nm", rated), ("peak_torque_nm", peak)):
        if value is not None and value <= 0:
            result.errors.append(f"{name} 为非正值（{value}），疑似单位或量级错误")
    if weight is not None and weight <= 0:
        result.errors.append(f"weight_kg 为非正值（{weight}），疑似单位或量级错误")

    # ── 工况口径归一：优先额定，缺额定时用峰值折减 ──
    if rated is not None and rated > 0:
        result.torque_nm = _round_sig(rated)
        result.operating_point_raw = OperatingPoint.RATED
        result.provenance["torque_nm"] = "实测：datasheet 额定扭矩（连续工况）"
    elif peak is not None and peak > 0:
        converted = normalize_torque(peak, OperatingPoint.PEAK, OperatingPoint.RATED, factors)
        result.torque_nm = _round_sig(converted)
        result.operating_point_raw = OperatingPoint.PEAK
        result.adjustments.append({
            "field": "torque_nm",
            "factor": factors.peak_to_rated_torque,
            "from": OperatingPoint.PEAK.value,
            "to": OperatingPoint.RATED.value,
            "basis": torque_conversion_basis(factors),
        })
        result.provenance["torque_nm"] = (
            f"推算：峰值扭矩 {peak} × {factors.peak_to_rated_torque}（峰值→额定）"
        )
        result.warnings.append("原始数据缺额定扭矩，由峰值扭矩折减，存在口径不确定性")
    else:
        result.provenance["torque_nm"] = "缺失"
        result.missing_fields.append("torque_nm")

    # ── 额定==峰值 疑似口径混填检测 ──
    if (rated is not None and peak is not None and rated > 0
            and peak <= rated * (1 + factors.rated_equals_peak_tolerance)):
        result.warnings.append(
            f"额定扭矩({rated})≈峰值扭矩({peak})，真实峰值扭矩通常显著大于额定，"
            f"疑似两个口径列重复填数，数据质量存疑"
        )

    # ── 电机本体反推（模组→电机）──
    if reduction_ratio is not None and result.torque_nm is not None:
        motor_torque, err = back_calculate_motor_torque(result.torque_nm, reduction_ratio, factors)
        if err:
            result.errors.append(err)
        else:
            result.provenance["motor_torque_nm"] = (
                f"推算：模组扭矩 {result.torque_nm} / (减速比 {reduction_ratio} "
                f"× 效率 {factors.gear_efficiency})"
            )
            result.adjustments.append({
                "field": "motor_torque_nm",
                "factor": _round_sig(1.0 / (reduction_ratio * factors.gear_efficiency)),
                "from": "module_torque",
                "to": "motor_torque",
                "basis": (
                    f"模组→电机本体反推，传动效率取 {factors.gear_efficiency}"
                    f"（CSV 谐波减速器典型效率 80%）；不确定度随减速比放大"
                ),
            })
            result.torque_nm = motor_torque  # 归一目标切换为电机本体口径
            result.warnings.append("扭矩已按减速比反推为电机本体口径，与减速器/模组数据不可直接比较")

    # ── 扭矩密度：优先实测，缺实测时用 扭矩/重量 推算 ──
    if density is not None and density > 0:
        result.torque_density_nm_kg = _round_sig(density)
        result.provenance["torque_density_nm_kg"] = "实测：datasheet/研报直接披露"
    elif result.torque_nm is not None and weight is not None and weight > 0:
        result.torque_density_nm_kg = _round_sig(result.torque_nm / weight)
        result.provenance["torque_density_nm_kg"] = (
            f"推算：归一化扭矩 {result.torque_nm} N·m / 重量 {weight} kg"
        )
        result.adjustments.append({
            "field": "torque_density_nm_kg",
            "factor": _round_sig(1.0 / weight),
            "from": "torque_nm,weight_kg",
            "to": "torque_density_nm_kg",
            "basis": "扭矩密度 = 归一化扭矩 / 重量；重量为实测值",
        })
    else:
        result.provenance["torque_density_nm_kg"] = "缺失"
        if weight is None:
            result.missing_fields.append("weight_kg")
        result.missing_fields.append("torque_density_nm_kg")

    # ── 功率密度（CSV 当前无此列，预留字段）──
    if power_density is not None and power_density > 0:
        result.power_density_w_kg = _round_sig(power_density)
        result.provenance["power_density_w_kg"] = "实测：datasheet 直接披露"
    else:
        result.provenance["power_density_w_kg"] = "缺失"

    # ── 可比性分级 ──
    result.comparability = _grade_comparability(result)
    return result


def _grade_comparability(result: NormalizedParameter) -> Comparability:
    """
    可比性分级规则（从严到宽）：
      not_comparable —— 归一化扭矩缺失（无锚点）、存在数值合法性错误、
                       或重量与扭矩密度同时缺失；
      approximate   —— 含任何推算值（峰值折减/密度反推/模组→电机反推）、
                       触发口径混填警告、或范围口径无法确定；
      comparable    —— 关键字段均为实测、口径明确。
    """
    if result.torque_nm is None or result.errors:
        return Comparability.NOT_COMPARABLE
    if result.torque_density_nm_kg is None and "weight_kg" in result.missing_fields:
        return Comparability.NOT_COMPARABLE
    if result.adjustments or result.warnings:
        return Comparability.APPROXIMATE
    if result.scope == AssemblyScope.UNKNOWN or result.operating_point_raw == OperatingPoint.UNKNOWN:
        return Comparability.APPROXIMATE
    return Comparability.COMPARABLE


# ============================================================
# CSV 加载
# ============================================================

def load_and_normalize(
    path: Path | str = DEFAULT_PARAMETER_CSV,
    factors: ConversionFactors = DEFAULT_FACTORS,
) -> List[NormalizedParameter]:
    """
    从 parameter_table_filled.csv（或同构 CSV）加载全部行并归一化。

    列名以 CSV 表头为准，数值列容忍「待补充」等缺失哨兵；
    文件缺失/表头为空时抛 ValueError 并附清晰说明（属于输入配置错误）。
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"参数表不存在：{path}")
    results: List[NormalizedParameter] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError(f"参数表为空或缺少表头：{path}")
        for line_no, row in enumerate(reader, start=2):
            normalized = normalize_parameter_row(row, factors)
            if not normalized.company and not normalized.model:
                normalized.errors.append(f"第 {line_no} 行 company/model 均为空，已跳过归一")
            results.append(normalized)
    return results


def filter_comparable(params: List[NormalizedParameter]) -> List[NormalizedParameter]:
    """筛出可比性不低于 approximate 的行（供 economic_mapper 直接消费）。"""
    return [p for p in params if p.comparability != Comparability.NOT_COMPARABLE]


# ============================================================
# 快速自测
# ============================================================

if __name__ == "__main__":
    params = load_and_normalize()
    print(f"共归一化 {len(params)} 行参数\n")
    for p in params:
        print(f"[{p.comparability.value}] {p.company} {p.model} ({p.scope.value})")
        print(f"  扭矩(N·m, 连续额定): {p.torque_nm}  密度(N·m/kg): {p.torque_density_nm_kg}")
        if p.adjustments:
            print(f"  调整: {[a['field'] for a in p.adjustments]}")
        if p.warnings:
            print(f"  警告: {p.warnings}")
        if p.missing_fields:
            print(f"  缺失: {p.missing_fields}")
