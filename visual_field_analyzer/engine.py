"""
驾驶员视野检查判定规则引擎
实现公安部规定的6条判定标准（单眼受试者申请驾照）
"""
from dataclasses import dataclass, field
from typing import List, Optional
# 兼容：PyInstaller打包后用绝对导入，开发环境用相对导入
try:
    from point_grid import (
        get_points_for_eye,
        get_temporal_outer_point,
        get_nasal_edge_indices,
        get_horizontal_band_indices,
    )
except ImportError:
    from .point_grid import (
        get_points_for_eye,
        get_temporal_outer_point,
        get_nasal_edge_indices,
        get_horizontal_band_indices,
    )


@dataclass
class RuleResult:
    """单条规则的判定结果"""
    rule_id: int           # 规则编号 1-6
    rule_name: str         # 规则名称
    passed: bool           # 是否通过
    detail: str            # 详细说明（中文）
    value: float = 0.0     # 实际测量值
    limit: float = 0.0     # 限制值


@dataclass
class AnalysisResult:
    """完整分析结果"""
    overall_pass: bool             # 总体是否通过
    eye: str                       # 眼别 'OS'/'OD'
    fixation_loss: int = 0         # 固视丢失次数
    false_positive: int = 0        # 假阳性次数
    false_negative: int = 0        # 假阴性次数
    point_states: List[int] = field(default_factory=list)  # 99个点的状态: 1=已见, 0=未见, -1=未设置
    rules: List[RuleResult] = field(default_factory=list)
    summary: str = ""              # 汇总文字


def analyze(eye: str, point_states: List[int],
            fixation_loss: int, false_positive: int,
            false_negative: int = 0, lang: str = "zh") -> AnalysisResult:
    """
    执行完整的6规则判定分析。

    Args:
        eye: 'OS'(左眼) 或 'OD'(右眼)
        point_states: 长度为99的列表，每个元素为 1(已见/seen), 0(未见/unseen), 或 -1(未设置)
        fixation_loss: 固视丢失次数 (凝视点丢失)
        false_positive: 假阳性错识次数 (假阳性率)
        false_negative: 假阴性错识次数
        lang: 结果文字语言，"zh"(默认) 或 "en"

    Returns:
        AnalysisResult 对象
    """
    assert eye.upper() in ('OS', 'OD'), f"Invalid eye: {eye}"
    assert len(point_states) == 99, f"Expected 99 points, got {len(point_states)}"

    results = []

    # ---- 规则1：固视丢失不能超过3次 ----
    r1 = _check_rule_1(fixation_loss, lang)
    results.append(r1)

    # ---- 规则2：假阳性错识不能超过3次 ----
    r2 = _check_rule_2(false_positive, lang)
    results.append(r2)

    # ---- 规则3：颞侧90°外侧测试点必须正确应答 ----
    r3 = _check_rule_3(eye, point_states, lang)
    results.append(r3)

    # ---- 规则4：距水平线上下10°视野范围内不能出现连续3个以上错误应答点 ----
    r4 = _check_rule_4(eye, point_states, lang)
    results.append(r4)

    # ---- 规则5：鼻侧60°边缘的4个测试点必须至少正确应答1个 ----
    r5 = _check_rule_5(eye, point_states, lang)
    results.append(r5)

    # ---- 规则6：如果存在2次固视丢失或2次假阳性错误，
    #          则鼻侧60°边缘的4个测试点必须至少正确应答2个 ----
    r6 = _check_rule_6(eye, point_states, fixation_loss, false_positive, lang)
    results.append(r6)
    
    # 总判定：所有规则都通过才算通过
    overall = all(r.passed for r in results)
    
    # 生成汇总
    failed_rules = [r for r in results if not r.passed]
    if overall:
        summary = "✅ 判定结果：合格（通过）\n所有检测项目均符合要求。" if lang == "zh" else \
                  "PASS — All criteria satisfied."
    else:
        if lang == "zh":
            names = ", ".join([f"规则{r.rule_id}({r.rule_name})" for r in failed_rules])
            summary = f"❌ 判定结果：不合格（不通过）\n违反项：{names}"
        else:
            names = ", ".join([f"R{r.rule_id} ({r.rule_name})" for r in failed_rules])
            summary = f"FAIL — Violated: {names}"
    
    return AnalysisResult(
        overall_pass=overall,
        eye=eye.upper(),
        fixation_loss=fixation_loss,
        false_positive=false_positive,
        false_negative=false_negative,
        point_states=list(point_states),
        rules=results,
        summary=summary,
    )


# ==================== 各规则具体实现 ====================

def _check_rule_1(fl: int, lang: str = "zh") -> RuleResult:
    """规则1：固视丟失不能超过3次"""
    passed = fl <= 3
    if lang == "zh":
        detail = f"固视丢失 {fl} 次（限值 ≤ 3）" + (" ✓ 合格" if passed else " ✗ 不合格")
        name = "固视丢失"
    else:
        detail = f"Fixation loss: {fl} (limit ≤ 3)" + (" — PASS" if passed else " — FAIL")
        name = "Fixation loss"
    return RuleResult(rule_id=1, rule_name=name, passed=passed,
                      value=float(fl), limit=3.0, detail=detail)


def _check_rule_2(fp: int, lang: str = "zh") -> RuleResult:
    """规则2：假阳性错识不能超过3次"""
    passed = fp <= 3
    if lang == "zh":
        detail = f"假阳性错识 {fp} 次（限值 ≤ 3）" + (" ✓ 合格" if passed else " ✗ 不合格")
        name = "假阳性"
    else:
        detail = f"False-positive errors: {fp} (limit ≤ 3)" + (" — PASS" if passed else " — FAIL")
        name = "False positive"
    return RuleResult(rule_id=2, rule_name=name, passed=passed,
                      value=float(fp), limit=3.0, detail=detail)


def _check_rule_3(eye: str, states: List[int], lang: str = "zh") -> RuleResult:
    """规则3：颞侧90°外侧的测试点必须正确应答"""
    idx = get_temporal_outer_point(eye)
    state = states[idx]
    pts = get_points_for_eye(eye)
    x, y = pts[idx]

    passed = state == 1  # 必须是"已见"
    if lang == "zh":
        status_str = "已见✓" if state == 1 else ("未见✗" if state == 0 else "未设置?")
        detail = f"颞侧90°外侧点({x:+g}°,{y:+g}°)：{status_str}" + \
                 (" ✓ 合格" if passed else " ✗ 不合格")
        name = "颞侧外点"
    else:
        status_str = "seen ✓" if state == 1 else ("unseen ✗" if state == 0 else "unset ?")
        detail = f"Temporal 90° outer point ({x:+g}°,{y:+g}°): {status_str}" + \
                 (" — PASS" if passed else " — FAIL")
        name = "Temporal outer point"
    return RuleResult(rule_id=3, rule_name=name, passed=passed,
                      value=float(state), limit=1.0, detail=detail)


def _check_rule_4(eye: str, states: List[int], lang: str = "zh") -> RuleResult:
    """
    规则4：距水平线上下10°视野范围（每列距水平线最近的上两点与下两点）内，
    不能出现连续3个以上的错误应答点。
    错误应答 = 未见(unseen, state=0)。
    "连续" 同时检查：同一行(水平)相邻、同一列(垂直)相邻 的连续未见点，
    取两者最大连续数作为判定依据。
    """
    band_idx = get_horizontal_band_indices(eye, band_deg=10.0)
    pts = get_points_for_eye(eye)
    band_pts = [pts[i] for i in band_idx]
    band_unseen = {pts[i] for i in band_idx if states[i] == 0}

    # 按行(相同 y)检查水平连续
    by_row = {}
    for (x, y) in band_pts:
        by_row.setdefault(y, []).append(x)
    max_h = 0
    for y, xs in by_row.items():
        xs_sorted = sorted(xs)
        run = 0
        for x in xs_sorted:
            if (x, y) in band_unseen:
                run += 1
                max_h = max(max_h, run)
            else:
                run = 0

    # 按列(相同 x)检查垂直连续
    by_col = {}
    for (x, y) in band_pts:
        by_col.setdefault(x, []).append(y)
    max_v = 0
    for x, ys in by_col.items():
        ys_sorted = sorted(ys)
        run = 0
        for y in ys_sorted:
            if (x, y) in band_unseen:
                run += 1
                max_v = max(max_v, run)
            else:
                run = 0

    max_consecutive = max(max_h, max_v)
    passed = max_consecutive < 3
    if lang == "zh":
        status = (f"水平最大连续={max_h}个, 垂直最大连续={max_v}个 "
                  f"（限值均 < 3）")
        detail = status + (" ✓ 合格" if passed else " ✗ 不合格")
        name = "水平带连续错误"
    else:
        status = (f"Max consecutive unseen: horizontal={max_h}, vertical={max_v} "
                  f"(limit < 3)")
        detail = status + (" — PASS" if passed else " — FAIL")
        name = "Horizontal-band consecutive misses"
    if not passed:
        # 列出参与的错误点（最多8个）
        pos_info = "; ".join([f"({x:+g},{y:+g})" for (x, y) in sorted(band_unseen)[:8]])
        detail += (f"\n  错误点位置: {pos_info}" if lang == "zh"
                   else f"\n  Missed points: {pos_info}")

    return RuleResult(rule_id=4, rule_name=name,
                      passed=passed, value=float(max_consecutive),
                      limit=3.0, detail=detail)


def _check_rule_5(eye: str, states: List[int], lang: str = "zh") -> RuleResult:
    """规则5：鼻侧60°边缘的4个测试点必须至少正确应答1个"""
    nasal_idx = get_nasal_edge_indices(eye)
    correct_count = sum(1 for i in nasal_idx if states[i] == 1)

    passed = correct_count >= 1
    if lang == "zh":
        detail = f"鼻侧60°边缘4点中正确应答 {correct_count}/4 个（限值 ≥ 1）" + \
                 (" ✓ 合格" if passed else " ✗ 不合格")
        name = "鼻侧边缘(≥1)"
    else:
        detail = f"Nasal 60° edge: {correct_count}/4 points correctly seen (limit ≥ 1)" + \
                 (" — PASS" if passed else " — FAIL")
        name = "Nasal edge (≥1)"
    return RuleResult(rule_id=5, rule_name=name,
                      passed=passed, value=float(correct_count),
                      limit=1.0, detail=detail)


def _check_rule_6(eye: str, states: List[int],
                  fl: int, fp: int, lang: str = "zh") -> RuleResult:
    """
    规则6：如果存在2次及以上固视丢失或2次及以上假阳性错误，
           则位于鼻侧60°边缘的4个测试点必须至少正确应答2个。
    注意：此规则仅在 FL≥2 或 FP≥2 时触发；若都不满足则自动通过。
    """
    triggered = fl >= 2 or fp >= 2

    if not triggered:
        # 条件未触发，规则自动通过
        if lang == "zh":
            detail = f"固视丢失({fl}<2)且假阳性({fp}<2)，本规则不触发 ✓ 自动通过"
            name = "鼻侧边缘(条件)"
        else:
            detail = (f"Fixation loss ({fl}<2) and false positive ({fp}<2): "
                      f"rule not triggered — auto PASS")
            name = "Nasal edge (conditional)"
        return RuleResult(
            rule_id=6, rule_name=name,
            passed=True, value=0.0, limit=0.0, detail=detail
        )

    nasal_idx = get_nasal_edge_indices(eye)
    correct_count = sum(1 for i in nasal_idx if states[i] == 1)

    required = 2
    passed = correct_count >= required
    reason_parts = []
    if fl >= 2:
        reason_parts.append(f"固视丢失{fl}次" if lang == "zh" else f"FL={fl}")
    if fp >= 2:
        reason_parts.append(f"假阳性{fp}次" if lang == "zh" else f"FP={fp}")
    trigger_reason = "+".join(reason_parts)

    if lang == "zh":
        detail = f"[{trigger_reason}] 鼻侧边缘4点中正确应答 {correct_count}/{required} 个" + \
                 (" ✓ 合格" if passed else " ✗ 不合格")
        name = "鼻侧边缘(条件)"
    else:
        detail = f"[{trigger_reason}] Nasal 60° edge: {correct_count}/{required} points correctly seen" + \
                 (" — PASS" if passed else " — FAIL")
        name = "Nasal edge (conditional)"
    return RuleResult(
        rule_id=6, rule_name=name,
        passed=passed, value=float(correct_count),
        limit=float(required), detail=detail
    )


if __name__ == "__main__":
    # 测试用例
    print("=== 规则引擎测试 ===")
    
    # 全部通过的例子
    all_seen = [1] * 99
    result = analyze("OS", all_seen, fl=0, fp=0)
    print(f"\n全部通过案例: overall={result.overall_pass}")
    for r in result.rules:
        print(f"  规则{r.rule_id}: {'✓' if r.passed else '✗'} {r.detail}")
    
    # 多项不合格的例子
    some_failed = [1] * 99
    some_failed[0] = 0   # 颞侧外点失败
    for i in range(15, 18):  # 水平带内连续3个错误
        some_failed[i] = 0
    nasal = get_nasal_edge_indices("OS")
    for i in nasal[:4]:  # 鼻侧边缘全错
        some_failed[i] = 0
    
    result2 = analyze("OS", some_failed, fl=2, fp=2)
    print(f"\n多项不合格案例: overall={result2.overall_pass}")
    for r in result2.rules:
        print(f"  规则{r.rule_id}: {'✓' if r.passed else '✗'} {r.detail}")
    print(result2.summary)
