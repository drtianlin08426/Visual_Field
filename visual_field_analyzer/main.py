"""
驾驶员视野检查自动分析工具 —— 主程序（tkinter GUI）
面向无电脑基础用户的离线分析软件。
支持中文 / English 双语界面（默认中文；顶部可切换，供投稿与审稿人阅读）。
"""
import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, font
from PIL import Image, ImageTk, ImageDraw
import math

# 将当前目录加入路径以支持模块导入
if getattr(sys, 'frozen', False):
    # PyInstaller 打包后的路径
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(BASE_DIR))

# 兼容：PyInstaller打包后用绝对导入，开发环境用相对导入
try:
    from point_grid import (
        get_points_for_eye,
        CANONICAL_POINTS_OS,
        get_nasal_edge_indices,
        get_temporal_outer_point,
        get_horizontal_band_indices,
    )
    from engine import analyze, AnalysisResult
    from pdf_parser import parse_pdf
    from report_generator import generate_a4_report
except ImportError:
    from .point_grid import (
        get_points_for_eye,
        CANONICAL_POINTS_OS,
        get_nasal_edge_indices,
        get_temporal_outer_point,
        get_horizontal_band_indices,
    )
    from .engine import analyze, AnalysisResult
    from .pdf_parser import parse_pdf
    from .report_generator import generate_a4_report


# ============================================================
# 双语文字表（默认中文；en 用于投稿 / 审稿人阅读）
# ============================================================
I18N = {
    "zh": {
        "app_title": "🚗 驾驶员视野检查自动分析工具",
        "import_pdf": "📂 导入PDF报告",
        "reset": "🔄 重置数据",
        "img_placeholder": "📋 请导入PDF报告\n或手动输入数据",
        "params": " 🔧 检测参数 ",
        "eye_label": "检测眼睛:",
        "os": "左眼(OS)", "od": "右眼(OD)",
        "fl": "固视丢失:", "fp": "假阳性错识:", "fn": "假阴性错识:",
        "auto_note": "※ 以上三项由报告自动读取，一般无需修改",
        "all_seen": "✅ 全部设为已见",
        "all_unseen": "❌ 全部设为未见",
        "stats": "已设置: 0/99 点",
        "report_ref": "报告标注: 已见 - / 未见 -",
        "grid_title": " 👁 视野测试点（点击切换状态） ",
        "analyze": "🔍 开始分析判定",
        "report": "🖨 生成A4报告",
        "result": " 📊 分析结果 ",
        "legend": " 📖 符号说明 ",
        "lg_seen": "已见 (空心圆)",
        "lg_unseen": "未见 (实心方块)",
        "lg_unset": "未设置 (?)",
        "lg_temporal": "颞侧外点 (规则3)",
        "lg_nasal": "鼻侧边缘 (规则5/6)",
        # 对话框 / 提示
        "dlg_pdf_title": "选择视野检测报告(PDF)",
        "dlg_pdf_all": "所有文件",
        "err_parse": "无法解析该PDF文件。\n请确保是 ZEISS Humphrey 视野检测报告。",
        "confirm_reset": "确定要清除所有输入的数据吗？",
        "warn_unset": "还有 {n}/99 个测试点未设置。\n是否继续分析？（未设置的点将被视为「已见」）",
        "hint_import_first": "请先导入一份视野检测 PDF 报告，\n再生成 A4 报告。",
        "err_import": "错误", "err_analysis": "分析错误", "err_gen": "生成失败",
        "note": "提示",
        "msg_auto_done": "📋 自动分析完成 — {status}",
        "msg_partial": "⚠️ 部分自动识别",
        "msg_report_done": "🖨 A4报告已生成",
        "msg_report_body": ("报告已生成并打开：\n{fn}\n\n"
                            "判定结果：{status}\n\n"
                            "在浏览器中点击「打印 / 另存为 PDF（A4）」即可输出到 A4 纸。"),
        # 结果区
        "result_pass_hdr": "═" * 46 + "\n  ✅ 判定结果：【 合 格 】通过 \n" + "═" * 46 + "\n\n",
        "result_fail_hdr": "═" * 46 + "\n  ❌ 判定结果：【 不合格 】不通过 \n" + "═" * 46 + "\n\n",
        "result_info_hdr": "📋 基本信息:\n",
        "result_eye": "检测眼",
        "result_fl": "固视丢失",
        "result_fp": "假阳性错识",
        "result_pts": "测试点",
        "result_rules_hdr": "📊 逐项判定:\n",
        "result_done_pass": "✅ 分析完成 — 合格",
        "result_done_fail": "⚠️ 分析完成 — 不合格",
        # PDF 解析后自动提示
        "auto_patient": "患者",
        "auto_eye": "检测眼",
        "auto_fl_fp": "固视丢失",
        "auto_recog": "自动识别",
        "auto_verdict": "━━━ 判定结果 ━━━",
        "auto_hint": "(网格中可点击任意点手动修正后重新点「🔍 开始分析」)",
        "partial_basic": "已读取基本信息：",
        "partial_fail": "但测试点符号自动识别未成功。\n请手动标记测试点后点击「🔍 分析」。",
        "partial_eye": "检测眼",
        "partial_fl": "固视丢失",
    },
    "en": {
        "app_title": "🚗 Driver's-License Visual Field Analyzer",
        "import_pdf": "📂 Import PDF report",
        "reset": "🔄 Reset data",
        "img_placeholder": "📋 Import a PDF report\nor enter data manually",
        "params": " 🔧 Test parameters ",
        "eye_label": "Eye tested:",
        "os": "Left (OS)", "od": "Right (OD)",
        "fl": "Fixation loss:", "fp": "False positive:", "fn": "False negative:",
        "auto_note": "※ The three items above are read automatically from the report; usually no editing needed",
        "all_seen": "✅ Set all seen",
        "all_unseen": "❌ Set all unseen",
        "stats": "Set: 0/99 points",
        "report_ref": "Report annotation: seen - / unseen -",
        "grid_title": " 👁 Visual field test points (click to toggle) ",
        "analyze": "🔍 Run analysis",
        "report": "🖨 Generate A4 report",
        "result": " 📊 Analysis result ",
        "legend": " 📖 Legend ",
        "lg_seen": "Seen (open circle)",
        "lg_unseen": "Unseen (solid square)",
        "lg_unset": "Unset (?)",
        "lg_temporal": "Temporal outer point (Rule 3)",
        "lg_nasal": "Nasal edge (Rules 5/6)",
        # Dialogs / hints
        "dlg_pdf_title": "Select visual field report (PDF)",
        "dlg_pdf_all": "All files",
        "err_parse": "Could not parse this PDF file.\nPlease ensure it is a ZEISS Humphrey visual field report.",
        "confirm_reset": "Clear all entered data?",
        "warn_unset": "Still {n}/99 test points unset.\nContinue analysis? (Unset points will be treated as 'seen'.)",
        "hint_import_first": "Import a visual field PDF report first,\nthen generate the A4 report.",
        "err_import": "Error", "err_analysis": "Analysis error", "err_gen": "Generation failed",
        "note": "Note",
        "msg_auto_done": "📋 Auto-analysis complete — {status}",
        "msg_partial": "⚠️ Partial auto-recognition",
        "msg_report_done": "🖨 A4 report generated",
        "msg_report_body": ("Report generated and opened:\n{fn}\n\n"
                            "Verdict: {status}\n\n"
                            "In the browser, click 'Print / Save as PDF (A4)' to output to A4 paper."),
        # Result area
        "result_pass_hdr": "═" * 46 + "\n  ✅ VERDICT: PASS \n" + "═" * 46 + "\n\n",
        "result_fail_hdr": "═" * 46 + "\n  ❌ VERDICT: FAIL \n" + "═" * 46 + "\n\n",
        "result_info_hdr": "📋 Basic information:\n",
        "result_eye": "Eye tested",
        "result_fl": "Fixation loss",
        "result_fp": "False positive",
        "result_pts": "Test points",
        "result_rules_hdr": "📊 Per-rule verdict:\n",
        "result_done_pass": "✅ Analysis complete — PASS",
        "result_done_fail": "⚠️ Analysis complete — FAIL",
        # Auto-recognition message box
        "auto_patient": "Patient",
        "auto_eye": "Eye",
        "auto_fl_fp": "Fixation loss",
        "auto_recog": "Auto-recognition",
        "auto_verdict": "----- Verdict -----",
        "auto_hint": "(Click any point on the grid to correct it manually, then click 'Run analysis' again.)",
        "partial_basic": "Basic information read:",
        "partial_fail": "But automatic symbol recognition of test points failed.\nPlease mark the test points manually, then click 'Run analysis'.",
        "partial_eye": "Eye",
        "partial_fl": "Fixation loss",
    },
}


class VisualFieldAnalyzerApp(tk.Tk):
    """主应用程序窗口"""

    # 颜色方案（深色主题友好）
    COLORS = {
        "bg": "#f5f6fa",
        "canvas_bg": "#ffffff",
        "grid_line": "#e0e0e0",
        "axis": "#999999",
        "seen": "#27ae60",         # 已见 - 绿色
        "unseen": "#c0392b",       # 未见 - 红色
        "unset": "#bdc3c7",        # 未设置 - 灰色
        "temporal": "#2980b9",     # 颞侧外点 - 蓝色
        "nasal": "#8e44ad",        # 鼻侧边缘点 - 紫色
        "band": "#f39c12",         # 水平带内点 - 橙色高亮
        "pass_bg": "#d4edda",
        "pass_text": "#155724",
        "fail_bg": "#f8d7da",
        "fail_text": "#721c24",
        "text": "#2c3e50",
        "text_secondary": "#7f8c8d",
        "btn_primary": "#3498db",
        "btn_success": "#27ae60",
        "btn_warning": "#f39c12",
        "btn_danger": "#e74c3c",
    }

    def __init__(self):
        super().__init__()

        # 默认语言：可被环境变量 VF_DEFAULT_LANG 或 exe 同级 vf_lang.txt 覆盖（英文版 exe 用）
        self.lang = self._resolve_default_lang()
        self.title(self._("app_title"))
        self.geometry("1280x800")
        self.minsize(1100, 700)
        self.configure(bg=self.COLORS["bg"])

        self._ui_font = ("Microsoft YaHei UI", 11)

        # 数据状态
        self.current_eye = tk.StringVar(value="OS")  # 默认左 eye
        self.point_states = [-1] * 99  # -1=未设置, 1=已见, 0=未见
        self.fixation_loss = tk.IntVar(value=0)
        self.false_positive = tk.IntVar(value=0)
        self.false_negative = tk.IntVar(value=0)
        self.report_image_tk = None  # 报告显示用的 Tk PhotoImage
        self.report_image_pil = None  # PIL 图像（保持引用）
        self.analysis_result: AnalysisResult = None
        self.report = None            # 当前导入的 ParsedReport（用于生成A4报告）
        self._report_ref = ("-", "-")  # 报告标注 seen/unseen

        # 特殊点的索引集合（用于高亮显示）
        self.special_point_sets = {}
        self._legend_desc_labels = []  # 图例说明标签，便于重翻译

        # 构建界面
        self._setup_ui()
        self._update_special_points()
        self._draw_grid()

    # ---- 翻译辅助 ----
    def _resolve_default_lang(self) -> str:
        """默认语言解析：VF_DEFAULT_LANG 环境变量优先；
        其次读取 exe/脚本同级目录下的 vf_lang.txt；默认中文。"""
        env = (os.environ.get("VF_DEFAULT_LANG") or "").strip().lower()
        if env in ("en", "english"):
            return "en"
        if env in ("zh", "cn", "chinese"):
            return "zh"
        try:
            if getattr(sys, "frozen", False):
                base = os.path.dirname(sys.executable)
            else:
                base = os.path.dirname(os.path.abspath(__file__))
            with open(os.path.join(base, "vf_lang.txt"), "r", encoding="utf-8") as _f:
                v = _f.read().strip().lower()
            if v in ("en", "english"):
                return "en"
            if v in ("zh", "cn", "chinese"):
                return "zh"
        except Exception:
            pass
        return "zh"

    def _(self, key):
        return I18N[self.lang][key]

    def _on_lang_change(self, *args):
        self.lang = "en" if self.lang_var.get() == "English" else "zh"
        self.title(self._("app_title"))
        self._retranslate()

    def _retranslate(self):
        """切换语言后刷新所有界面文字（分析逻辑不变）。"""
        self.title_label.config(text=self._("app_title"))
        self.btn_import.config(text=self._("import_pdf"))
        self.btn_clear.config(text=self._("reset"))
        self.input_frame.config(text=self._("params"))
        self.rb_os.config(text=self._("os"))
        self.rb_od.config(text=self._("od"))
        self.eye_label.config(text=self._("eye_label"))
        self.fl_label.config(text=self._("fl"))
        self.fp_label.config(text=self._("fp"))
        self.fn_label.config(text=self._("fn"))
        self.auto_note.config(text=self._("auto_note"))
        self.all_seen_btn.config(text=self._("all_seen"))
        self.all_unseen_btn.config(text=self._("all_unseen"))
        self.canvas_frame.config(text=self._("grid_title"))
        self.analyze_btn.config(text=self._("analyze"))
        self.report_btn.config(text=self._("report"))
        self.result_frame.config(text=self._("result"))
        self.legend_frame.config(text=self._("legend"))
        for lbl, key in zip(self._legend_desc_labels,
                            ["lg_seen", "lg_unseen", "lg_unset", "lg_temporal", "lg_nasal"]):
            lbl.config(text=f" {self._(key)}")
        # 动态文字
        if self.report_image_tk is None:
            self.img_display.config(text=self._("img_placeholder"))
        self.report_ref_label.config(text=self._report_ref_label_text())
        self._draw_grid()  # 刷新统计行
        if self.analysis_result is not None:
            self._show_result(self.analysis_result)

    def _report_ref_label_text(self):
        seen, unseen = self._report_ref
        if self.lang == "zh":
            return f"报告标注: 已见 {seen} / 未见 {unseen}"
        return f"Report annotation: seen {seen} / unseen {unseen}"

    def _setup_ui(self):
        """构建完整UI布局"""
        # ===== 顶部栏 =====
        top_frame = tk.Frame(self, bg="#2c3e50", height=55)
        top_frame.pack(fill=tk.X)
        top_frame.pack_propagate(False)

        self.title_label = tk.Label(
            top_frame, text=self._("app_title"),
            font=("Microsoft YaHei UI", 16, "bold"),
            fg="white", bg="#2c3e50"
        )
        self.title_label.pack(side=tk.LEFT, padx=20, pady=10)

        # 语言切换
        self.lang_var = tk.StringVar(value="English" if self.lang == "en" else "中文")
        lang_combo = ttk.Combobox(
            top_frame, textvariable=self.lang_var, values=["中文", "English"],
            width=9, state="readonly", font=("Microsoft YaHei UI", 11)
        )
        lang_combo.pack(side=tk.RIGHT, padx=(5, 10), pady=12)
        lang_combo.bind("<<ComboboxSelected>>", self._on_lang_change)

        self.btn_import = tk.Button(
            top_frame, text=self._("import_pdf"), command=self.import_pdf,
            font=("Microsoft YaHei UI", 11),
            fg="white", bg=self.COLORS["btn_primary"],
            activebackground="#2980b9", cursor="hand2",
            relief=tk.FLAT, padx=15, pady=6
        )
        self.btn_import.pack(side=tk.RIGHT, padx=(5, 0), pady=10)

        self.btn_clear = tk.Button(
            top_frame, text=self._("reset"), command=self.reset_data,
            font=("Microsoft YaHei UI", 11),
            fg="white", bg=self.COLORS["btn_warning"],
            activebackground="#d68910", cursor="hand2",
            relief=tk.FLAT, padx=15, pady=6
        )
        self.btn_clear.pack(side=tk.RIGHT, pady=10)

        # ===== 主内容区 =====
        content = tk.Frame(self, bg=self.COLORS["bg"])
        content.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # 左侧：报告图片 + 控制面板
        left_panel = tk.Frame(content, bg=self.COLORS["bg"], width=380)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))
        left_panel.pack_propagate(False)

        # --- 报告图片区域 ---
        self.img_display = tk.Label(
            left_panel, text=self._("img_placeholder"),
            font=("Microsoft YaHei UI", 12), fg=self.COLORS["text_secondary"],
            bg=self.COLORS["bg"], justify=tk.CENTER
        )
        self.img_display.pack(fill=tk.BOTH, expand=True, pady=5)

        # --- 数据输入面板 ---
        self.input_frame = tk.LabelFrame(
            left_panel, text=self._("params"),
            font=("Microsoft YaHei UI", 11, "bold"),
            bg=self.COLORS["bg"], fg=self.COLORS["text"],
            padx=10, pady=8
        )
        self.input_frame.pack(fill=tk.X, pady=5)

        # 眼别选择
        eye_row = tk.Frame(self.input_frame, bg=self.COLORS["bg"])
        eye_row.pack(fill=tk.X, pady=3)
        self.eye_label = tk.Label(eye_row, text=self._("eye_label"),
                                  font=("Microsoft YaHei UI", 11),
                                  bg=self.COLORS["bg"])
        self.eye_label.pack(side=tk.LEFT)
        self.rb_os = ttk.Radiobutton(eye_row, text=self._("os"), variable=self.current_eye,
                                     value="OS", command=self.on_eye_changed)
        self.rb_od = ttk.Radiobutton(eye_row, text=self._("od"), variable=self.current_eye,
                                     value="OD", command=self.on_eye_changed)
        self.rb_os.pack(side=tk.LEFT, padx=(10, 5))
        self.rb_od.pack(side=tk.LEFT)

        # 数值输入行
        def _make_input_row(parent, label, var):
            row = tk.Frame(parent, bg=self.COLORS["bg"])
            row.pack(fill=tk.X, pady=2)
            lab = tk.Label(row, text=label, font=("Microsoft YaHei UI", 10),
                           bg=self.COLORS["bg"], width=14, anchor='w')
            lab.pack(side=tk.LEFT)
            entry = ttk.Spinbox(row, from_=0, to=99, width=6, textvariable=var,
                                font=("Microsoft YaHei UI", 10))
            entry.pack(side=tk.RIGHT)
            return lab

        self.fl_label = _make_input_row(self.input_frame, self._("fl"), self.fixation_loss)
        self.fp_label = _make_input_row(self.input_frame, self._("fp"), self.false_positive)
        self.fn_label = _make_input_row(self.input_frame, self._("fn"), self.false_negative)

        # 自动读取说明
        self.auto_note = tk.Label(
            self.input_frame,
            text=self._("auto_note"),
            font=("Microsoft YaHei UI", 9), fg="#8aa0b6", bg=self.COLORS["bg"])
        self.auto_note.pack(fill=tk.X, pady=(1, 0))

        # 批量操作按钮
        batch_frame = tk.Frame(self.input_frame, bg=self.COLORS["bg"])
        batch_frame.pack(fill=tk.X, pady=(8, 2))
        self.all_seen_btn = tk.Button(batch_frame, text=self._("all_seen"),
                                      command=lambda: self.set_all_points(1),
                                      font=("Microsoft YaHei UI", 9), bg=self.COLORS["seen"],
                                      fg="white", relief=tk.FLAT, cursor="hand2")
        self.all_seen_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=1)
        self.all_unseen_btn = tk.Button(batch_frame, text=self._("all_unseen"),
                                         command=lambda: self.set_all_points(0),
                                         font=("Microsoft YaHei UI", 9), bg=self.COLORS["unseen"],
                                         fg="white", relief=tk.FLAT, cursor="hand2")
        self.all_unseen_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=1)

        # 统计信息
        stats_frame = tk.Frame(self.input_frame, bg=self.COLORS["bg"])
        stats_frame.pack(fill=tk.X, pady=(5, 0))
        self.stats_label = tk.Label(stats_frame, text=self._("stats"),
                                    font=("Microsoft YaHei UI", 10),
                                    bg=self.COLORS["bg"], fg=self.COLORS["text_secondary"])
        self.stats_label.pack(side=tk.LEFT)

        # 报告标注的已见/未见参考数（帮助用户核对需标记几个未见点）
        self.report_ref_label = tk.Label(
            self.input_frame, text=self._("report_ref"),
            font=("Microsoft YaHei UI", 10), bg=self.COLORS["bg"],
            fg=self.COLORS["text_secondary"])
        self.report_ref_label.pack(fill=tk.X, pady=(2, 0))

        # 右侧：交互式网格 + 结果
        right_panel = tk.Frame(content, bg=self.COLORS["bg"])
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # --- 网格画布 ---
        self.canvas_frame = tk.LabelFrame(
            right_panel, text=self._("grid_title"),
            font=("Microsoft YaHei UI", 11, "bold"),
            bg=self.COLORS["bg"], fg=self.COLORS["text"]
        )
        self.canvas_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))

        self.canvas = tk.Canvas(
            self.canvas_frame, bg=self.COLORS["canvas_bg"],
            highlightthickness=1, highlightbackground="#ccc"
        )
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.canvas.bind("<Configure>", self.on_canvas_resize)

        # --- 操作按钮 ---
        btn_frame = tk.Frame(right_panel, bg=self.COLORS["bg"])
        btn_frame.pack(fill=tk.X, pady=5)

        self.analyze_btn = tk.Button(
            btn_frame, text=self._("analyze"), command=self.run_analysis,
            font=("Microsoft YaHei UI", 13, "bold"), fg="white",
            bg=self.COLORS["btn_success"], activebackground="#219a52",
            cursor="hand2", relief=tk.FLAT, padx=30, pady=10
        )
        self.analyze_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

        self.report_btn = tk.Button(
            btn_frame, text=self._("report"), command=self.generate_report,
            font=("Microsoft YaHei UI", 13, "bold"), fg="white",
            bg=self.COLORS["btn_primary"], activebackground="#2980b9",
            cursor="hand2", relief=tk.FLAT, padx=20, pady=10
        )
        self.report_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

        # --- 结果展示区 ---
        self.result_frame = tk.LabelFrame(
            right_panel, text=self._("result"),
            font=("Microsoft YaHei UI", 11, "bold"),
            bg=self.COLORS["bg"], fg=self.COLORS["text"]
        )
        self.result_frame.pack(fill=tk.X)

        self.result_text = tk.Text(
            self.result_frame, height=10, font=("Consolas", 10),
            bg="white", fg=self.COLORS["text"],
            wrap=tk.WORD, state=tk.DISABLED,
            relief=tk.FLAT, padx=10, pady=8
        )
        self.result_text.pack(fill=tk.X, padx=5, pady=5)

        # 图例
        self._create_legend(left_panel)

    def _create_legend(self, parent):
        """创建符号图例"""
        self.legend_frame = tk.LabelFrame(
            parent, text=self._("legend"),
            font=("Microsoft YaHei UI", 10), bg=self.COLORS["bg"],
            fg=self.COLORS["text_secondary"], padx=8, pady=5
        )
        self.legend_frame.pack(fill=tk.X, pady=5)

        legends = [
            ("○", self.COLORS["seen"], "lg_seen"),
            ("■", self.COLORS["unseen"], "lg_unseen"),
            ("●", self.COLORS["unset"], "lg_unset"),
            ("◆", self.COLORS["temporal"], "lg_temporal"),
            ("★", self.COLORS["nasal"], "lg_nasal"),
        ]

        self._legend_desc_labels = []
        for symbol, color, key in legends:
            row = tk.Frame(self.legend_frame, bg=self.COLORS["bg"])
            row.pack(fill=tk.X, pady=1)
            tk.Label(row, text=symbol, font=("Consolas", 12, "bold"),
                     fg=color, bg=self.COLORS["bg"], width=3).pack(side=tk.LEFT)
            lbl = tk.Label(row, text=f" {self._(key)}",
                           font=("Microsoft YaHei UI", 9),
                           fg=self.COLORS["text_secondary"], bg=self.COLORS["bg"])
            lbl.pack(side=tk.LEFT)
            self._legend_desc_labels.append(lbl)

    def _update_special_points(self):
        """更新特殊点索引集合"""
        eye = self.current_eye.get()
        t_idx = get_temporal_outer_point(eye)
        n_idx = get_nasal_edge_indices(eye)
        h_idx = get_horizontal_band_indices(eye, band_deg=10.0)

        self.special_point_sets = {
            "temporal": {t_idx},
            "nasal": set(n_idx),
            "band": set(h_idx),
        }

    def on_eye_changed(self):
        """眼别切换时重绘网格"""
        self._update_special_points()
        self._draw_grid()

    def on_canvas_resize(self, event=None):
        """窗口大小改变时重绘网格"""
        if event and event.width > 100 and event.height > 100:
            self.after(50, self._draw_grid)

    def _draw_grid(self):
        """绘制交互式视野网格"""
        self.canvas.delete("all")
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()

        if w < 50 or h < 50:
            return

        cx, cy = w // 2, h // 2 + 20
        scale = min(w, h) * 0.38  # 半径（像素）

        # 存储每个点的屏幕坐标和半径，用于点击检测
        self.point_screen_coords = []

        eye = self.current_eye.get()
        pts = get_points_for_eye(eye)

        # 画同心圆背景
        max_r_deg = 95  # 最大度数范围
        for r_deg in range(10, max_r_deg + 1, 10):
            r_px = (r_deg / max_r_deg) * scale
            color = "#e8e8e8" if r_deg % 20 == 0 else "#f0f0f0"
            self.canvas.create_oval(
                cx - r_px, cy - r_px, cx + r_px, cy + r_px,
                outline=color, width=1
            )

        # 画坐标轴
        ax_len = scale + 25
        self.canvas.create_line(cx - ax_len, cy, cx + ax_len, cy,
                                fill=self.COLORS["axis"], width=1)
        self.canvas.create_line(cx, cy - ax_len, cx, cy + ax_len + 10,
                                fill=self.COLORS["axis"], width=1)

        # 标注度数
        label_color = self.COLORS["text_secondary"]
        f = font.Font(family="Arial", size=8)
        self.canvas.create_text(cx + ax_len - 5, cy - 12, text="90°",
                                fill=label_color, font=f)
        self.canvas.create_text(cx - ax_len + 5, cy - 12, text="-90°",
                                fill=label_color, font=f)

        # 画测试点
        nasal_set = self.special_point_sets.get("nasal", set())
        temporal_set = self.special_point_sets.get("temporal", set())

        point_radius = max(7, min(w, h) // 75)  # 自适应点大小

        for i, (px_deg, py_deg) in enumerate(pts):
            sx = cx + (px_deg / max_r_deg) * scale
            sy = cy - (py_deg / max_r_deg) * scale

            state = self.point_states[i]

            # 确定颜色
            if i in temporal_set:
                base_color = self.COLORS["temporal"]
            elif i in nasal_set:
                base_color = self.COLORS["nasal"]
            else:
                base_color = None

            if state == 1:  # 已见 → 空心圆
                color = base_color or self.COLORS["seen"]
                item = self.canvas.create_oval(
                    sx - point_radius, sy - point_radius,
                    sx + point_radius, sy + point_radius,
                    outline=color, width=2, fill=""
                )
            elif state == 0:  # 未见 → 实心方块
                half = point_radius * 0.85
                color = base_color or self.COLORS["unseen"]
                item = self.canvas.create_rectangle(
                    sx - half, sy - half, sx + half, sy + half,
                    fill=color, outline=color
                )
            else:  # 未设置 → 灰色小圆
                r_small = point_radius * 0.5
                item = self.canvas.create_oval(
                    sx - r_small, sy - r_small, sx + r_small, sy + r_small,
                    fill=self.COLORS["unset"], outline=""
                )

            self.point_screen_coords.append((sx, sy, point_radius * 1.8, i))

        # 更新统计
        set_count = sum(1 for s in self.point_states if s != -1)
        seen_count = sum(1 for s in self.point_states if s == 1)
        unseen_count = sum(1 for s in self.point_states if s == 0)
        if self.lang == "zh":
            self.stats_label.config(
                text=f"已设置: {set_count}/99 | ✓{seen_count} ✗{unseen_count} ?{99 - set_count}")
        else:
            self.stats_label.config(
                text=f"Set: {set_count}/99 | ✓{seen_count} ✗{unseen_count} ?{99 - set_count}")

    def on_canvas_click(self, event):
        """处理画布点击事件 —— 切换测试点状态"""
        x, y = event.x, event.y

        for sx, sy, radius, idx in self.point_screen_coords:
            dist = math.sqrt((x - sx) ** 2 + (y - sy) ** 2)
            if dist <= radius:
                # 切换状态: -1 → 1 → 0 → -1
                current = self.point_states[idx]
                if current == -1:
                    self.point_states[idx] = 1
                elif current == 1:
                    self.point_states[idx] = 0
                else:
                    self.point_states[idx] = -1

                self._draw_grid()

                # 高亮反馈
                self.canvas.config(highlightbackground="#3498db")
                self.after(300, lambda: self.canvas.config(highlightbackground="#ccc"))
                break

    def import_pdf(self):
        """导入PDF报告文件 —— 自动识别全部内容，一键分析出报告"""
        path = filedialog.askopenfilename(
            title=self._("dlg_pdf_title"),
            filetypes=[("PDF", "*.pdf"), (self._("dlg_pdf_all"), "*.*")]
        )
        if not path:
            return

        report = parse_pdf(path)
        if report is None:
            messagebox.showerror(self._("err_import"), self._("err_parse"))
            return

        # 保存解析结果（供生成A4报告使用）
        self.report = report

        # 填充数据到界面
        self.current_eye.set(report.eye or "OS")
        self.fixation_loss.set(report.fixation_loss)
        self.false_positive.set(report.false_positive)
        self.false_negative.set(report.false_negative)

        # 显示报告图片
        if report.page_image:
            self.display_report_image(report.page_image)

        # 参考标注：报告给出的已见/未见点数
        seen = report.seen_count if report.seen_count >= 0 else "-"
        unseen = report.unseen_count if report.unseen_count >= 0 else "-"
        self._report_ref = (str(seen), str(unseen))
        self.report_ref_label.config(text=self._report_ref_label_text())

        # ---- 核心新功能：自动填充99点状态（矢量图元法）----
        if report.point_states is not None and len(report.point_states) == 99:
            self.point_states = list(report.point_states)
            auto_seen = sum(1 for s in report.point_states if s == 1)
            auto_unseen = sum(1 for s in report.point_states if s == 0)

            # 重绘网格（显示自动识别结果）
            self.on_eye_changed()

            # ---- 自动执行分析判定 ----
            final_states = [s if s != -1 else 1 for s in self.point_states]
            eye = self.current_eye.get()
            fl = self.fixation_loss.get()
            fp = self.false_positive.get()
            fn = self.false_negative.get()

            try:
                result = analyze(eye, final_states, fl, fp, fn, lang=self.lang)
                self.analysis_result = result
                self._show_result(result)

                # 弹出综合提示
                status_word = "✅ 通过" if result.overall_pass else "❌ 不通过"
                eye_name = self._("os") if report.eye == 'OS' else self._("od")
                messagebox.showinfo(
                    self._("msg_auto_done").format(status=status_word),
                    f"{self._('auto_patient')}: {report.patient_name}\n"
                    f"{self._('auto_eye')}: {eye_name}\n"
                    f"{self._('auto_fl_fp')}: {report.fixation_loss}  "
                    f"{self._('result_fp')}: {report.false_positive}\n"
                    f"{self._('auto_recog')}: seen {auto_seen} / unseen {auto_unseen}\n\n"
                    f"{self._('auto_verdict')}\n"
                    f"{result.summary}\n\n"
                    f"{self._('auto_hint')}"
                )
            except Exception as e:
                messagebox.showerror(self._("err_analysis"),
                                     f"{self._('err_analysis')}:\n{e}")
        else:
            # 矢量检测失败，回退到手动模式
            self.on_eye_changed()
            eye_name = self._("os") if report.eye == 'OS' else self._("od")
            messagebox.showwarning(
                self._("msg_partial"),
                f"{self._('partial_basic')}\n"
                f"{self._('auto_patient')}: {report.patient_name}\n"
                f"{self._('partial_eye')}: {eye_name}\n"
                f"{self._('partial_fl')}: {report.fixation_loss}  "
                f"{self._('result_fp')}: {report.false_positive}\n"
                f"\n{self._('partial_fail')}"
            )

    def display_report_image(self, pil_img):
        """在左侧面板显示报告图片"""
        # 缩放到合适大小
        panel_width = 360
        panel_height = 400
        img_ratio = pil_img.width / pil_img.height
        panel_ratio = panel_width / panel_height

        if img_ratio > panel_ratio:
            new_w = panel_width
            new_h = int(panel_width / img_ratio)
        else:
            new_h = panel_height
            new_w = int(panel_height * img_ratio)

        resized = pil_img.resize((new_w, new_h), Image.LANCZOS)
        self.report_image_pil = resized
        self.report_image_tk = ImageTk.PhotoImage(resized)

        self.img_display.config(image=self.report_image_tk, text="")

    def reset_data(self):
        """重置所有数据"""
        if messagebox.askyesno(self._("confirm_reset"), self._("confirm_reset")):
            self.point_states = [-1] * 99
            self.fixation_loss.set(0)
            self.false_positive.set(0)
            self.false_negative.set(0)
            self.report_image_tk = None
            self.report_image_pil = None
            self.img_display.config(
                image="", text=self._("img_placeholder")
            )
            self.analysis_result = None
            self.result_text.config(state=tk.NORMAL)
            self.result_text.delete(1.0, tk.END)
            self.result_text.insert(tk.END, "等待分析..." if self.lang == "zh" else "Awaiting analysis...")
            self.result_text.config(state=tk.DISABLED)
            self._report_ref = ("-", "-")
            self.report_ref_label.config(text=self._report_ref_label_text())
            self._draw_grid()

    def set_all_points(self, state):
        """批量设置所有点的状态"""
        self.point_states = [state] * 99
        self._draw_grid()

    def run_analysis(self):
        """执行分析判定"""
        # 检查是否有足够的数据
        unset_count = sum(1 for s in self.point_states if s == -1)
        if unset_count > 10:
            if not messagebox.askyesno(
                self._("note"),
                self._("warn_unset").format(n=unset_count)
            ):
                return
            # 将未设置视为已见
            final_states = [s if s != -1 else 1 for s in self.point_states]
        else:
            final_states = list(self.point_states)

        # 执行分析
        eye = self.current_eye.get()
        fl = self.fixation_loss.get()
        fp = self.false_positive.get()
        fn = self.false_negative.get()

        try:
            result = analyze(eye, final_states, fl, fp, fn, lang=self.lang)
            self.analysis_result = result
            self._show_result(result)
        except Exception as e:
            messagebox.showerror(self._("err_analysis"), f"{self._('err_analysis')}:\n{e}")

    def generate_report(self):
        """生成可打印的 A4 报告（HTML，可直接打印/另存为PDF）"""
        # 需要先有导入的报告数据
        if self.report is None or self.report.eye not in ("OS", "OD"):
            messagebox.showwarning(self._("note"), self._("hint_import_first"))
            return

        # 用当前界面数据（含自动识别的点状态与可靠性指标）做一次分析
        eye = self.current_eye.get()
        final_states = [s if s != -1 else 1 for s in self.point_states]
        fl = self.fixation_loss.get()
        fp = self.false_positive.get()
        fn = self.false_negative.get()
        try:
            self.analysis_result = analyze(eye, final_states, fl, fp, fn, lang=self.lang)
        except Exception as e:
            messagebox.showerror(self._("err_analysis"),
                                 f"{self._('err_gen')}:\n{e}")
            return

        try:
            out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "生成报告")
            out_path = generate_a4_report(self.report, self.analysis_result, out_dir, lang=self.lang)
        except Exception as e:
            messagebox.showerror(self._("err_gen"), f"{self._('err_gen')}:\n{e}")
            return

        # 打开报告（默认浏览器），用户可打印或另存为 PDF
        try:
            os.startfile(out_path)  # Windows
        except Exception:
            try:
                import webbrowser
                webbrowser.open(out_path)
            except Exception:
                pass

        status_word = "✅ 合格" if self.analysis_result.overall_pass else "❌ 不合格"
        messagebox.showinfo(
            self._("msg_report_done"),
            self._("msg_report_body").format(
                fn=os.path.basename(out_path), status=status_word)
        )

    def _show_result(self, result: AnalysisResult):
        """展示分析结果"""
        self.result_text.config(state=tk.NORMAL)
        self.result_text.delete(1.0, tk.END)

        # 总体结果
        if result.overall_pass:
            header = self._("result_pass_hdr")
        else:
            header = self._("result_fail_hdr")

        self.result_text.insert(tk.END, header)

        # 基本信息
        eye_name = self._("os") if result.eye == "OS" else self._("od")
        info = (f"{self._('result_info_hdr')}"
                f"   {self._('result_eye')}: {eye_name}\n"
                f"   {self._('result_fl')}: {result.fixation_loss}\n"
                f"   {self._('result_fp')}: {result.false_positive}\n"
                f"   {self._('result_pts')}: seen "
                f"{sum(1 for s in result.point_states if s == 1)} / "
                f"unseen {sum(1 for s in result.point_states if s == 0)}\n\n")
        self.result_text.insert(tk.END, info)

        # 各规则详情
        self.result_text.insert(tk.END, self._("result_rules_hdr"))
        for rule in result.rules:
            status_icon = "✅" if rule.passed else "❌"
            line = f"\n  [{status_icon}] Rule {rule.rule_id}: {rule.rule_name}\n"
            self.result_text.insert(tk.END, line)
            self.result_text.insert(tk.END, f"      {rule.detail}\n")

        self.result_text.insert(tk.END, "\n" + result.summary + "\n")

        self.result_text.config(state=tk.DISABLED)

        # 弹出醒目提示框
        if result.overall_pass:
            messagebox.showinfo(self._("result_done_pass"), result.summary)
        else:
            messagebox.showwarning(self._("result_done_fail"), result.summary)


# ==================== 入口 ====================

def main():
    app = VisualFieldAnalyzerApp()
    app.mainloop()


if __name__ == "__main__":
    main()
