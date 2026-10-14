"""
标准99点测试网格 —— 基于ZEISS Humphrey视野计「驾驶员视野检测」程序。
坐标系统：以固视点为原点(0,0)，x轴向右为正（鼻侧），y轴向上为正。
每个点用(x_deg, y_deg)表示，单位为度数。

左眼(OS)：x负=颞侧，x正=鼻侧；最左侧(-90°附近)=颞侧90°，最右侧(+60°附近)=鼻侧60°
右眼(OD)：x负=鼻侧，x正=颞侧；最左侧(-60°附近)=鼻侧60°，最右侧(+90°附近)=颞侧90°
"""

import json
from pathlib import Path

# ============================================================
# 标准测试点坐标（OS/左眼的视角）
# 共 99 个点，按行从上到下、每行内从左到右排列。
# 注意：坐标是从真实 ZEISS Humphrey「驾驶员视野检测」PDF 报告反演得到的，
# 该模式并非均匀 10° 网格（例如行 0° 仅颞侧(-90,0)一个点，列距为不规则 15° 等）。
# ============================================================
CANONICAL_POINTS_OS = [
    # Row +20°
    (-60, 20), (-45, 20), (-30, 20), (-15, 20), (-3, 20), (3, 20), (15, 20), (30, 20), (45, 20),
    # Row +9°
    (-75, 9), (-60, 9), (-45, 9), (-30, 9), (-21, 9), (-15, 9), (-9, 9), (-3, 9),
    (3, 9), (9, 9), (15, 9), (21, 9), (30, 9), (45, 9), (60, 9),
    # Row +3°
    (-81, 3), (-75, 3), (-60, 3), (-45, 3), (-30, 3), (-21, 3), (-15, 3), (-9, 3), (-3, 3),
    (3, 3), (9, 3), (15, 3), (21, 3), (30, 3), (45, 3), (60, 3),
    # Row 0° (仅颞侧极端点)
    (-90, 0),
    # Row -3°
    (-81, -3), (-75, -3), (-60, -3), (-45, -3), (-30, -3), (-21, -3), (-15, -3), (-9, -3), (-3, -3),
    (3, -3), (9, -3), (15, -3), (21, -3), (30, -3), (45, -3), (60, -3),
    # Row -9°
    (-81, -9), (-75, -9), (-60, -9), (-45, -9), (-30, -9), (-21, -9), (-15, -9), (-9, -9), (-3, -9),
    (3, -9), (9, -9), (15, -9), (21, -9), (30, -9), (45, -9), (60, -9),
    # Row -15°
    (-75, -15), (-60, -15), (-45, -15), (-30, -15), (-21, -15), (-15, -15), (-9, -15), (-3, -15),
    (3, -15), (9, -15), (15, -15), (21, -15), (30, -15), (45, -15),
    # Row -21°
    (-60, -21), (-45, -21), (-30, -21), (-21, -21), (-15, -21), (-9, -21), (-3, -21),
    (3, -21), (9, -21), (15, -21), (21, -21), (30, -21),
]

# 验证点数
assert len(CANONICAL_POINTS_OS) == 99, f"Expected 99 points, got {len(CANONICAL_POINTS_OS)}"


def get_points_for_eye(eye):
    """
    获取指定眼睛的标准测试点坐标列表。
    eye: 'OS'(左眼) 或 'OD'(右眼)
    返回: [(x, y), ...] 每个元素为(x_deg, y_deg)
    对于OD(右眼)，x坐标取反(镜像翻转)
    """
    if eye.upper() == 'OS':
        return list(CANONICAL_POINTS_OS)
    elif eye.upper() == 'OD':
        return [(-x, y) for x, y in CANONICAL_POINTS_OS]
    else:
        raise ValueError(f"Invalid eye: {eye}. Must be 'OS' or 'OD'")


def get_temporal_outer_point(eye):
    """返回颞侧90°外侧测试点的索引（在get_points_for_eye返回的列表中）"""
    pts = get_points_for_eye(eye)
    if eye.upper() == 'OS':
        # 左眼：颞侧在最左边（x最小），即(-90, 0)
        for i, (x, y) in enumerate(pts):
            if abs(x - (-90)) < 2 and abs(y) < 2:
                return i
        return min(range(len(pts)), key=lambda i: pts[i][0])
    else:
        # 右眼：颞侧在最右边（x最大），即(+90, 0)
        for i, (x, y) in enumerate(pts):
            if abs(x - 90) < 2 and abs(y) < 2:
                return i
        return max(range(len(pts)), key=lambda i: pts[i][0])


def get_nasal_edge_indices(eye):
    """
    返回鼻侧60°边缘的4个测试点的索引列表。
    取「最靠鼻侧」(OS: x 最大; OD: x 最小) 的4个点。
    """
    pts = get_points_for_eye(eye)
    if eye.upper() == 'OS':
        edge_pts = sorted(range(len(pts)), key=lambda i: (-pts[i][0], -pts[i][1]))
    else:
        edge_pts = sorted(range(len(pts)), key=lambda i: (pts[i][0], -pts[i][1]))
    return edge_pts[:4]


def get_horizontal_band_indices(eye, band_deg=10.0):
    """
    返回距离水平线±band_deg范围内的所有测试点索引。
    这些是规则4需要检查的点（不能有连续3+错误）。
    """
    pts = get_points_for_eye(eye)
    indices = []
    for i, (x, y) in enumerate(pts):
        if abs(y) <= band_deg:
            indices.append(i)
    return sorted(indices, key=lambda i: (-pts[i][1], pts[i][0]))


if __name__ == "__main__":
    print("=== 标准测试点网格 ===")
    print(f"总点数: {len(CANONICAL_POINTS_OS)}")
    
    for eye in ['OS', 'OD']:
        pts = get_points_for_eye(eye)
        print(f"\n--- {eye} ({'左眼' if eye=='OS' else '右眼'}) ---")
        print(f"颞侧外点索引: {get_temporal_outer_point(eye)}")
        print(f"鼻侧边缘点索引: {get_nasal_edge_indices(eye)}")
        
        band = get_horizontal_band_indices(eye)
        print(f"水平±10°带内点数: {len(band)}")
        
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        print(f"X范围: [{min(xs)}, {max(xs)}]")
        print(f"Y范围: [{min(ys)}, {max(ys)}]")
