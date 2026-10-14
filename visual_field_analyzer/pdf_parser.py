"""
PDF 报告解析模块
功能：
1. 从 ZEISS Humphrey 视野检测 PDF 中提取文本信息（眼别、固视丢失、假阳性等）
2. 渲染视野图页面为 PIL Image 供 GUI 显示
3. 尝试自动识别每个测试点的 seen/unseen 状态
"""
import fitz  # pymupdf
import re
import os
from dataclasses import dataclass
from typing import Optional, List, Tuple
from PIL import Image
import numpy as np

# 兼容：PyInstaller 打包后用绝对导入，开发环境(脚本直接运行)用相对导入
try:
    from point_grid import get_points_for_eye
except ImportError:
    from .point_grid import get_points_for_eye


@dataclass
class ParsedReport:
    """解析后的报告数据"""
    file_path: str = ""
    patient_name: str = ""
    gender: str = ""                 # 性别
    birth_date: str = ""             # 出生日期
    patient_id: str = ""             # 患者 ID
    exam_date: str = ""              # 检查日期
    eye: str = ""                    # "OS" 或 "OD"
    fixation_loss: int = 0           # 固视丢失次数 (凝视点丢失分子)
    false_positive: int = 0          # 假阳性错识次数 (假阳性率分子)
    false_negative: int = 0          # 假阴性错识次数 (假阴性率分子)
    fl_total: int = 0                # 固视丢失分母
    fp_total: int = 0                # 假阳性分母
    fn_total: int = 0                # 假阴性分母
    seen_count: int = -1             # 已见点数
    unseen_count: int = -1           # 未见点数
    total_points: int = 99
    page_image: Optional[Image.Image] = None  # 视野图页面的渲染图像
    raw_text: str = ""               # 原始提取文本
    point_states: List[int] = None   # 自动检测的99点状态列表（1=已见,0=未见,-1=未知）


def _extract_reliability(full_text: str):
    """
    从报告全文提取可靠性三项指标（固视丢失 / 假阳性 / 假阴性）的分子与分母。

    ZEISS Humphrey 报告的两种常见排版：
      A) 数值紧跟标签： 凝视点丢失：2/3
      B) 标签独占一行，数值分组出现在「中央」之后：
           中央
           0/0
           6/7 XX
           0/7
         此时三个分数按 凝视点丢失 / 假阳性率 / 假阴性率 的顺序排列。

    返回 (fl_num, fp_num, fn_num, fl_den, fp_den, fn_den)，缺失项为 None。
    """
    fl = fp = fn = fl_t = fp_t = fn_t = None

    # 主策略：在「中央」之后取前三个 分子/分母 分数
    m = re.search(r'中央', full_text)
    if m:
        window = full_text[m.end(): m.end() + 200]
        fracs = re.findall(r'(\d+)\s*/\s*(\d+)', window)
        if len(fracs) >= 3:
            fl, fl_t = int(fracs[0][0]), int(fracs[0][1])
            fp, fp_t = int(fracs[1][0]), int(fracs[1][1])
            fn, fn_t = int(fracs[2][0]), int(fracs[2][1])

    # 兜底策略：数值紧跟各标签（部分生成版本会内联）
    if fl is None:
        flm = re.search(r'凝视点丢失[：:\s]*(\d+)\s*/\s*(\d+)', full_text)
        if flm:
            fl, fl_t = int(flm.group(1)), int(flm.group(2))
    if fp is None:
        fpm = re.search(r'假阳性率[：:\s]*(\d+)\s*/\s*(\d+)', full_text)
        if fpm:
            fp, fp_t = int(fpm.group(1)), int(fpm.group(2))
    if fn is None:
        fnm = re.search(r'假阴性率[：:\s]*(\d+)\s*/\s*(\d+)', full_text)
        if fnm:
            fn, fn_t = int(fnm.group(1)), int(fnm.group(2))

    return fl, fp, fn, fl_t, fp_t, fn_t


def parse_pdf(file_path: str) -> Optional[ParsedReport]:
    """
    解析一份视野检测报告 PDF。
    
    Args:
        file_path: PDF 文件路径
    
    Returns:
        ParsedReport 对象，解析失败返回 None
    """
    if not os.path.exists(file_path):
        return None
    
    try:
        doc = fitz.open(file_path)
    except Exception as e:
        print(f"[PDF] 无法打开文件: {e}")
        return None
    
    report = ParsedReport(file_path=file_path)
    
    # 提取所有页面文本
    full_text = ""
    for i in range(doc.page_count):
        full_text += doc[i].get_text()
    report.raw_text = full_text
    
    # ---- 提取眼别 OS/OD ----
    lines = full_text.split("\n")
    for line in lines:
        stripped = line.strip()
        if stripped == "OS":
            report.eye = "OS"
            break
        elif stripped == "OD":
            report.eye = "OD"
            break

    # ---- 提取可靠性指标（固视丢失/假阳性/假阴性）----
    # ZEISS 报告里这三个标签常独占一行，真实数值分组出现在「中央」之后，
    # 形如： 中央\n0/0\n6/7 XX\n0/7  （中间可能夹带 XX 等标记）。
    fl, fp, fn, fl_t, fp_t, fn_t = _extract_reliability(full_text)
    if fl is not None:
        report.fixation_loss = fl
    if fp is not None:
        report.false_positive = fp
    if fn is not None:
        report.false_negative = fn
    report.fl_total, report.fp_total, report.fn_total = fl_t, fp_t, fn_t

    # ---- 提取患者基本信息 ----
    name_match = re.search(r'患者[：:\s]*([^\n]+)', full_text)
    if name_match:
        report.patient_name = name_match.group(1).strip()
    gender_match = re.search(r'性别[：:\s]*([^\n]+)', full_text)
    if gender_match:
        report.gender = gender_match.group(1).strip()
    birth_match = re.search(r'出生日期[：:\s]*([^\n]+)', full_text)
    if birth_match:
        report.birth_date = birth_match.group(1).strip()
    id_match = re.search(r'患者\s*ID[：:\s]*([^\n]+)', full_text)
    if id_match:
        report.patient_id = id_match.group(1).strip()
    # 日期：报告里「日期/时间/年龄」三个标签竖向排列，真实日期值(YYYY/M/D)
    # 出现在「年龄：」之后，形如： 日期：\n时间：\n年龄：\n2026/6/16\n16:29\n41
    date_match = re.search(
        r'日期[：:\s]*\n时间[：:\s]*\n年龄[：:\s]*\n\s*(\d{4}/\d{1,2}/\d{1,2})',
        full_text)
    if date_match:
        report.exam_date = date_match.group(1).strip()

    # ---- 已见 / 未见计数 ----
    seen_match = re.search(r'已见\s*(\d+)', full_text)
    unseen_match = re.search(r'未见\s*(\d+)', full_text)
    if seen_match:
        report.seen_count = int(seen_match.group(1))
    if unseen_match:
        report.unseen_count = int(unseen_match.group(1))

    # ---- 渲染第一页为图像 + 矢量检测点状态 ----
    try:
        page = doc[0]

        # 【重要】先做矢量检测（在 get_pixmap 之前），避免渲染影响 drawings 读取
        if report.eye in ("OS", "OD"):
            try:
                pts = get_points_for_eye(report.eye)
                report.point_states = detect_point_states_from_vector(
                    page, report.eye, pts, verbose=False
                )
            except Exception as ve:
                print(f"[PDF] 矢量检测失败: {ve}")
                report.point_states = None

        # 使用较高分辨率渲染，确保符号清晰
        mat = fitz.Matrix(2.5, 2.5)
        pix = page.get_pixmap(matrix=mat)
        img_data = pix.tobytes("png")
        report.page_image = Image.open(__import__("io").BytesIO(img_data))

    except Exception as e:
        print(f"[PDF] 渲染图像失败: {e}")
    
    doc.close()
    return report


def render_page_as_image(pdf_path: str, page_num: int = 0,
                          scale: float = 2.5) -> Optional[Image.Image]:
    """单独将指定页面渲染为PIL Image"""
    try:
        doc = fitz.open(pdf_path)
        page = doc[page_num]
        mat = fitz.Matrix(scale, scale)
        pix = page.get_pixmap(matrix=mat)
        img_data = pix.tobytes("png")
        img = Image.open(__import__("io").BytesIO(img_data))
        doc.close()
        return img
    except Exception:
        return None


# ==================== 自动识别（矢量图元法，主方法） ====================

def _center_of_drawing(d):
    """计算一个 drawing 图元的中心坐标和宽高。"""
    xs, ys = [], []
    for it in d.get("items", []):
        t = it[0]
        if t == "re":
            r = it[1]; xs += [r.x0, r.x1]; ys += [r.y0, r.y1]
        elif t == "l":
            xs += [it[1].x, it[2].x]; ys += [it[1].y, it[2].y]
        elif t == "c":
            for p in it[1:]:
                xs.append(p.x); ys.append(p.y)
    if not xs:
        return None, None, None
    return (min(xs)+max(xs))/2, (min(ys)+max(ys))/2, (max(xs)-min(xs), max(ys)-min(ys))


def detect_point_states_from_vector(page, eye,
                                     canonical_points: List[Tuple[float,float]],
                                     verbose=False) -> List[int]:
    """
    **基于 PDF 矢量图元**的检测点状态自动识别（推荐方法）。

    原理：
      ZEISS Humphrey 报告中的符号是矢量绘制的：
      - ○ 已见 = fill=(1,1,1) 白填充 + color=(0,0,0) 黑描边，4段贝塞尔圆(cccc)
      - ■ 未见 = fill=(0,0,0) 黑填充矩形(re)，尺寸约 4.5pt
      通过灰色同心圆簇定位固视点与比例尺，在视野图半径内筛选符号，
      再将符号中心坐标映射到标准99点网格。

    Args:
        page: fitz.Page（已打开的PDF页面）
        eye: 'OS' 或 'OD'
        canonical_points: 标准99点坐标 [(x_deg,y_deg),...] 来自 point_grid.get_points_for_eye()
        verbose: 是否打印调试信息

    Returns:
        长度99列表：1=已见, 0=未见, -1=无法确定
    """
    drawings = page.get_drawings()
    n = len(canonical_points)
    states = [-1] * n

    # ---- 1) 灰色同心圆 → 固视点(fx,fy) + 比例尺(ppd) ----
    gray_circles = []  # (cx, cy, radius_pt)
    for d in drawings:
        items = d.get("items")
        if not items or items[0][0] != "c":
            continue
        col = d.get("color")
        if col is None or not (0.7 < col[0] < 0.9):
            continue
        if d.get("fill") is not None:
            continue  # 同心圆不填充
        c = _center_of_drawing(d)
        if c[0] is None:
            continue
        gray_circles.append((c[0], c[1], max(c[2]) / 2))

    if len(gray_circles) >= 4:
        pts = np.array([(g[0], g[1]) for g in gray_circles])
        fx = float(np.median(pts[:, 0]))
        fy = float(np.median(pts[:, 1]))
        radii = sorted([g[2] for g in gray_circles])
        R_max = radii[-1]
        diffs = np.diff(radii)
        ppd = float(np.median(diffs)) if len(diffs) > 0 else R_max / 9.0
    else:
        if verbose:
            print("[Vector-Detect] 未找到足够灰色同心圆，使用默认参数")
        fx, fy, R_max, ppd = 307.5, 425.2, 183.8, 20.42

    radius_limit = R_max * 1.15  # 符号搜索范围（稍大于最大环）

    # ---- 2) 收集全部符号（○已见 / ■未见），带类型标记 ----
    # 符号筛选：尺寸 3~7.5pt，且在视野半径内（ Humphrey 每个测试点恰好一个符号）
    symbols = []   # list of (x_pt, y_pt, kind)  kind: 1=○(已见), 0=■(未见)
    for d in drawings:
        items = d.get("items")
        if not items:
            continue
        head = items[0][0]
        cx, cy, wh = _center_of_drawing(d)
        if cx is None:
            continue
        dist = ((cx - fx) ** 2 + (cy - fy) ** 2) ** 0.5
        if dist > radius_limit:
            continue
        if head == "re":
            # ■ 未见：黑色填充矩形
            if d.get("fill") != (0.0, 0.0, 0.0):
                continue
            sz = wh[0] if isinstance(wh, tuple) else wh
            if not (3.0 <= sz <= 7.5):
                continue
            symbols.append((cx, cy, 0))
        elif head == "c" and len(items) == 4 and all(i[0] == "c" for i in items):
            # ○ 已见：白色填充 + 黑色描边 4段贝塞尔圆
            if d.get("fill") != (1.0, 1.0, 1.0) or d.get("color") != (0.0, 0.0, 0.0):
                continue
            sz = wh[0] if isinstance(wh, tuple) else wh
            if not (3.0 <= sz <= 7.5):
                continue
            symbols.append((cx, cy, 1))

    if verbose:
        n_seen = sum(1 for s in symbols if s[2] == 1)
        n_unseen = sum(1 for s in symbols if s[2] == 0)
        print(f"[Vector-Detect] 固视点=({fx:.1f},{fy:.1f}) ppd={ppd:.1f} "
              f"R_max={R_max:.1f}  符号总数={len(symbols)} (○={n_seen} ■={n_unseen})")

    # ---- 3) 坐标变换参数 ----
    # 灰色同心圆(9环=90°)本身即定义了物理比例尺，其圆心=固视点(0,0)，
    # ppd = R_max/9 即为真实的「每10°对应点数」。这是最可靠的基准，
    # 不再用○做最小二乘校准（实测会引入漂移导致匹配错位）。
    cal_fx, cal_fy, cal_ppd = fx, fy, ppd
    if verbose:
        print(f"[Vector-Detect] 变换参数(灰圆): ({cal_fx:.1f},{cal_fy:.1f}) ppd={cal_ppd:.2f}")

    # ---- 4) 以网格点为中心，做「贪心二分匹配」(按距离升序，双方均未用时才分配) ----
    # 这样每个符号只会被分配给距离最近的那个网格点，彻底避免碰撞丢失。
    states = [-1] * n
    cands = []  # (距离, 网格点i, 符号j)
    for i, (gx, gy) in enumerate(canonical_points):
        ax = cal_fx + gx / 10.0 * cal_ppd
        ay = cal_fy - gy / 10.0 * cal_ppd
        for j, (x, y, k) in enumerate(symbols):
            d = ((x - ax) ** 2 + (y - ay) ** 2) ** 0.5
            if d < cal_ppd * 1.5:
                cands.append((d, i, j))
    cands.sort()
    used_i, used_j = set(), set()
    assign = [-1] * n
    for d, i, j in cands:
        if i in used_i or j in used_j:
            continue
        used_i.add(i); used_j.add(j); assign[i] = j
    for i in range(n):
        if assign[i] >= 0:
            states[i] = symbols[assign[i]][2]

    if verbose:
        sc = sum(1 for s in states if s == 1); uc = sum(1 for s in states if s == 0)
        unk = sum(1 for s in states if s == -1)
        print(f"[Vector-Detect] 结果: Seen={sc} Unseen={uc} Unknown={unk}")

    return states


def detect_point_states(file_path: str, eye: str,
                        canonical_points: List[Tuple[float,float]],
                        verbose: bool = False) -> List[int]:
    """
    自动检测入口：优先使用矢量图元法，失败时回退到图像法。
    返回长度99的状态列表。
    """
    try:
        pts = get_points_for_eye(eye) if canonical_points is None else canonical_points
        doc = fitz.open(file_path)
        page = doc[0]
        result = detect_point_states_from_vector(page, eye, pts, verbose)
        doc.close()
        return result
    except Exception as e:
        if verbose:
            print(f"[Detect] 矢量法失败 ({e})，回退图像法")
        img = render_page_as_image(file_path)
        if img is None:
            return [-1] * len(canonical_points)
        return detect_point_states_from_image(img, eye, canonical_points, verbose)


# ==================== 旧版图像识别方法（保留作为fallback） ====================

def detect_point_states_from_image(image: Image.Image, eye: str,
                                    canonical_points: List[Tuple[float, float]],
                                    verbose: bool = False) -> List[int]:
    """
    尝试从视野图中自动识别每个测试点的状态。
    
    Args:
        image: 视野图的 PIL Image（灰度或RGB）
        eye: 'OS' 或 'OD'
        canonical_points: 标准坐标列表 [(x_deg, y_deg), ...]
        verbose: 是否打印调试信息
    
    Returns:
        长度为99的列表，每项为 1(已见), 0(未见), 或 -1(无法确定)
    """
    import cv2
    
    # 转为 OpenCV 格式
    img_array = np.array(image.convert("RGB"))
    gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    h, w = gray.shape
    
    # 找到视野图的中心点和比例尺
    cx, cy, ppd = _find_plot_center(gray)
    
    if ppd < 5 or ppd > 200:
        if verbose:
            print(f"[Auto-Detect] 异常比例尺 {ppd:.1f}，使用默认值")
        # 估算比例尺：假设视野图约占图像宽度的80%，覆盖约150度范围
        plot_diameter = min(w, h) * 0.75
        ppd = plot_diameter / 150.0 * 10.0  # 每10度对应像素数
    
    states = []
    for px_deg, py_deg in canonical_points:
        # 将度数坐标转换为图像像素坐标
        # 注意: 图像y轴向下为正，坐标系y轴向上为正
        img_x = int(cx + px_deg / 10.0 * ppd)
        img_y = int(cy - py_deg / 10.0 * ppd)
        
        # 边界检查
        if not (10 <= img_x < w-10 and 10 <= img_y < h-10):
            states.append(-1)
            continue
        
        # 在该位置判断符号类型
        state = _classify_point(gray, img_x, img_y)
        states.append(state)
    
    if verbose:
        seen = sum(1 for s in states if s == 1)
        unse = sum(1 for s in states if s == 0)
        unk = sum(1 for s in states if s == -1)
        print(f"[Auto-Detect] 结果: Seen={seen}, Unseen={unse}, Unknown={unk}, Total={len(states)}")
    
    return states


def _find_plot_center(gray):
    """
    找到视野图中心点和每10度的像素距离（最佳努力）。
    中心 = 固视点(0,0)，通过霍夫变换找视野图十字参考轴的交点定位。
    """
    import cv2
    import numpy as np
    h, w = gray.shape

    gray_inv = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)[1]
    lines = cv2.HoughLinesP(gray_inv, 1, np.pi/180, threshold=120,
                            minLineLength=min(w, h) * 0.3, maxLineGap=30)

    h_centers, v_centers = [], []
    if lines is not None:
        for raw_line in lines:
            line = raw_line.flatten() if hasattr(raw_line, 'flatten') else list(raw_line)
            if len(line) < 4:
                continue
            x1, y1, x2, y2 = int(line[0]), int(line[1]), int(line[2]), int(line[3])
            angle = abs(np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi)
            if angle < 15 or angle > 165:
                h_centers.append((y1 + y2) / 2)
            elif 75 < angle < 105:
                v_centers.append((x1 + x2) / 2)

    if h_centers and v_centers:
        cx = int(np.median(v_centers))
        cy = int(np.median(h_centers))
        # 比例尺估算：从固视点到图像最近边界的距离约对应 90°(颞侧最远)
        r_near = min(cx, w - cx, cy, h - cy)
        ppd = r_near / 9.0  # 约9个10°环 = 90°
        return cx, cy, max(ppd, 20)

    # fallback：视野图大致居中偏上，约占图像75%
    cx = w // 2
    cy = int(h * 0.44)
    plot_radius = min(w, h) * 0.75 / 2.0
    ppd = plot_radius / 9.0
    return cx, cy, max(ppd, 20)


def _classify_point(gray, x, y, win=17):
    """
    判断给定位置的符号类型: 1=seen(空心圆), 0=unseen(实心方块), -1=unknown
    """
    import cv2
    gh, gw = gray.shape
    half = win // 2
    y1, y2 = max(0, y-half), min(gh, y+half+1)
    x1, x2 = max(0, x-half), min(gw, x+half+1)
    
    region = gray[y1:y2, x1:x2].copy()
    if region.size < 40:
        return -1
    
    region = cv2.resize(region, (win, win))
    
    # 内部亮度分析
    inner = region[4:-4, 4:-4]
    border = np.concatenate([region[0,:], region[-1,:], region[:,0], region[:,-1]])
    inner_mean = np.mean(inner)
    border_mean = np.mean(border)
    
    # 空心圆特征：内部亮(~250)、边缘有暗线(~<220)
    # 实心方块特征：整体暗(~<100)
    
    if inner_mean > 210:
        return 1   # 很可能是空心圆（已见）
    elif inner_mean < 120:
        return 0   # 很可能是实心方块（未见）
    elif border_mean < 200 and inner_mean > 170:
        return 1   # 有暗边框 + 亮内部 = 空心圆
    else:
        # 不确定，用填充率进一步判断
        _, bin_inv = cv2.threshold(region, 190, 255, cv2.THRESH_BINARY_INV)
        fill_ratio = np.sum(bin_inv > 0) / bin_inv.size
        if fill_ratio < 0.20:
            return 1
        elif fill_ratio > 0.35:
            return 0
        return -1


if __name__ == "__main__":
    import glob
    base = r"D:/工作空间/视野自动分析/Sample"
    pdfs = sorted(glob.glob(os.path.join(base, "*.pdf")))
    
    for pdf_path in pdfs[:3]:
        print(f"\n{'='*60}")
        print(f"File: {os.path.basename(pdf_path)}")
        result = parse_pdf(pdf_path)
        if result is None:
            print("  [FAIL] 无法解析")
            continue
        
        print(f"  患者: {result.patient_name}")
        print(f"  眼别: {result.eye} ({'左眼' if result.eye=='OS' else '右眼'})")
        print(f"  固视丢失: {result.fixation_loss}")
        print(f"  假阳性: {result.false_positive}")
        print(f"  假阴性: {result.false_negative}")
        print(f"  已见/未见: {result.seen_count}/{result.unseen_count}")
        print(f"  图像: {'有' if result.page_image else '无'} ({result.page_image.size if result.page_image else 'N/A'})")
