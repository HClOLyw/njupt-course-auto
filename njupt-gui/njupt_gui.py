# -*- coding: utf-8 -*-
"""
njupt_gui.py —— 南邮在线课堂自动化 GUI 客户端
=============================================
基于 Tkinter 的美观图形界面，将 njupt-course-auto 的三项功能
（刷课 / 查进度 / 考试）封装为按钮操作。

运行方式：  python njupt_gui.py
打包方式：  pyinstaller -F -w -i icon.ico njupt_gui.py

⚠️ 仅供本人账号自主学习使用，请自行评估平台风险。
"""
import json
import os
import queue
import threading
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext

from njupt_api import NJUPTApi, CONFIG_PATH, ApiError

# ---------------- 配色方案（现代浅色扁平风格） ----------------
COLORS = {
    "bg": "#F5F7FB",
    "card": "#FFFFFF",
    "primary": "#2F6BFF",
    "primary_dark": "#1E4FD6",
    "primary_light": "#EAF1FF",
    "accent": "#00C48C",
    "accent_light": "#E4F8F1",
    "warn": "#FFB020",
    "warn_light": "#FFF4E0",
    "danger": "#FF5A5F",
    "danger_light": "#FFECEC",
    "title": "#1B2559",
    "text": "#3B3F5C",
    "muted": "#8A90A6",
    "border": "#E4E7F0",
    "sidebar": "#1B2559",
    "sidebar_hover": "#27326E",
}


class RoundButton(tk.Canvas):
    """圆角按钮组件。"""
    def __init__(self, master, text, command=None, bg=COLORS["primary"],
                 fg="#FFFFFF", hover_bg=None, font=None, radius=18, height=46,
                 disabled_bg="#D9DEEB"):
        super().__init__(master, bg=COLORS["card"], highlightthickness=0, bd=0)
        self.text = text
        self.command = command
        self.bg = bg
        self.fg = fg
        self.hover_bg = hover_bg or bg
        self.radius = radius
        self.height = height
        self.font = font or ("Microsoft YaHei UI", 11, "bold")
        self.disabled_bg = disabled_bg
        self._hover = False
        self._disabled = False
        self.bind("<Configure>", self._redraw)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)
        self.configure(height=radius * 2 + height - radius)
        self._redraw()

    def _redraw(self, *_):
        import math
        w = self.winfo_width()
        h = self.winfo_height() or self.height
        self.delete("all")
        if w <= 1:
            return
        fill = self.disabled_bg if self._disabled else (
            self.hover_bg if self._hover else self.bg)
        r = self.radius
        self.create_polygon(
            r, 0, w - r, 0,
            w - r, r, w, r, w, h - r, w, h - r, w - r, h, r, h, r, h - r,
            0, h, 0, r, r, r, r, 0,
            smooth=True, fill=fill, outline="")
        self.create_text(w / 2, h / 2, text=self.text, fill=self.fg,
                         font=self.font)

    def _on_enter(self, *_):
        if not self._disabled:
            self._hover = True
            self._redraw()

    def _on_leave(self, *_):
        self._hover = False
        self._redraw()

    def _on_click(self, *_):
        if not self._disabled and self.command:
            self.command()

    def set_disabled(self, disabled):
        self._disabled = disabled
        self._redraw()


class NJUPTApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("南邮在线课堂 · 自动化助手")
        self.geometry("1020x660")
        self.minsize(920, 600)
        self.configure(bg=COLORS["bg"])

        # 尝试设置窗口图标
        _icon = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app_icon.ico")
        try:
            if os.path.exists(_icon):
                self.iconbitmap(_icon)
        except Exception:
            pass

        self._center_window(1020, 660)

        # 日志线程安全队列
        self.log_queue = queue.Queue()
        self._busy = False

        self.config_data = NJUPTApi.load_config()
        self.api = self._build_api()

        self._build_layout()

        # 轮询日志队列
        self.after(100, self._poll_log_queue)

        self._set_busy(False)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _center_window(self, w, h):
        self.update_idletasks()
        x = (self.winfo_screenwidth() - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry("%dx%d+%d+%d" % (w, h, x, y))

    def _build_api(self):
        return NJUPTApi(
            token=self.config_data.get("token", ""),
            tenant_id=self.config_data.get("tenant_id", "0"),
            course_id=self.config_data.get("course_id", ""),
            interval_between=self.config_data.get("interval_between", 6),
            log_callback=self._queue_log,
        )

    def _queue_log(self, level, text):
        self.log_queue.put((level, text))

    def _poll_log_queue(self):
        try:
            while True:
                level, text = self.log_queue.get_nowait()
                self._append_log(level, text)
        except queue.Empty:
            pass
        self.after(100, self._poll_log_queue)

    def _append_log(self, level, text):
        tags = {"info": "log_info", "warn": "log_warn",
                "error": "log_error", "success": "log_success"}.get(
                    level, "log_info")
        self.log_text.configure(state="normal")
        self.log_text.insert("end", text + "\n", (tags,))
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    # ---------------- 布局 ----------------
    def _build_layout(self):
        # 左侧导航
        self.sidebar = tk.Frame(self, bg=COLORS["sidebar"], width=200)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        logo = tk.Label(self.sidebar, text="NJUPT", font=("Segoe UI", 22, "bold"),
                        fg="#FFFFFF", bg=COLORS["sidebar"])
        logo.pack(pady=(30, 2))
        subtitle = tk.Label(self.sidebar, text="在线课堂自动化助手",
                            font=("Microsoft YaHei UI", 11), fg="#9FA8DA",
                            bg=COLORS["sidebar"])
        subtitle.pack(pady=(0, 30))

        nav_items = [
            ("dashboard", "📊  首页概览"),
            ("learn", "▶  自动刷课"),
            ("status", "📈  进度查询"),
            ("exam", "✍  自动考试"),
            ("settings", "⚙  参数设置"),
            ("about", "ℹ  关于说明"),
        ]
        self.nav_frame = tk.Frame(self.sidebar, bg=COLORS["sidebar"])
        self.nav_frame.pack(fill="x", padx=12)
        self.nav_buttons = {}
        self._current_page = None
        for key, label in nav_items:
            btn = tk.Label(self.nav_frame, text=label,
                           font=("Microsoft YaHei UI", 12),
                           fg="#C7CEE8", bg=COLORS["sidebar"], anchor="w",
                           padx=16, pady=12, cursor="hand2")
            btn.pack(fill="x", pady=2)
            btn.bind("<Button-1>", lambda e, k=key: self._show_page(k))
            btn.bind("<Enter>", lambda e, b=btn: b.configure(bg=COLORS["sidebar_hover"]))
            btn.bind("<Leave>", lambda e, b=btn: self._redraw_nav(b))
            self.nav_buttons[key] = btn

        # 底部状态
        self.conn_state = tk.Label(self.sidebar, text="● 空闲",
                                   font=("Microsoft YaHei UI", 10),
                                   fg="#9FA8DA", bg=COLORS["sidebar"])
        self.conn_state.pack(side="bottom", pady=20)

        # 主内容区
        self.main = tk.Frame(self, bg=COLORS["bg"])
        self.main.pack(side="left", fill="both", expand=True)

        self.pages = {}
        self._build_dashboard()
        self._build_learn()
        self._build_status()
        self._build_exam()
        self._build_settings()
        self._build_about()
        self._build_shared_log()

        self._show_page("dashboard")
        self._append_log("info", "欢迎使用南邮在线课堂自动化助手。")
        self._append_log("info", "请先在【参数设置】填写 Access-Token，再选择功能开始操作。")

    def _redraw_nav(self, btn):
        key = self._current_page
        if key and btn is self.nav_buttons.get(key):
            btn.configure(bg=COLORS["primary"], fg="#FFFFFF")
        else:
            btn.configure(bg=COLORS["sidebar"], fg="#C7CEE8")

    def _page_container(self, key):
        page = tk.Frame(self.main, bg=COLORS["bg"])
        self.pages[key] = page
        return page

    def _header(self, parent, title, subtitle=""):
        head = tk.Frame(parent, bg=COLORS["bg"])
        head.pack(fill="x", padx=30, pady=(24, 8))
        tk.Label(head, text=title, font=("Microsoft YaHei UI", 20, "bold"),
                 fg=COLORS["title"], bg=COLORS["bg"]).pack(anchor="w")
        if subtitle:
            tk.Label(head, text=subtitle, font=("Microsoft YaHei UI", 10),
                     fg=COLORS["muted"], bg=COLORS["bg"]).pack(anchor="w", pady=(4, 0))
        return head

    # ---------------- 首页 ----------------
    def _build_dashboard(self):
        page = self._page_container("dashboard")
        self._header(page, "首页概览", "南邮在线课堂自动化助手 · 请从左侧选择功能")

        cards = tk.Frame(page, bg=COLORS["bg"])
        cards.pack(fill="x", padx=30, pady=20)

        defs = [
            ("learn", "▶  自动刷课", "自动遍历课程全部知识点，\n模拟观看视频 / 阅读 PDF 到 100%",
             COLORS["primary"], COLORS["primary_light"]),
            ("status", "📈  进度查询", "查看每个知识点真实的\n完成状态与百分比",
             COLORS["accent"], COLORS["accent_light"]),
            ("exam", "✍  自动考试", "读取试卷、逐题作答并提交，\n内置题库已实测满分",
             COLORS["warn"], COLORS["warn_light"]),
        ]
        for i, (key, title, desc, color, _light) in enumerate(defs):
            card = tk.Frame(cards, bg=COLORS["card"],
                            highlightthickness=1,
                            highlightbackground=COLORS["border"], cursor="hand2")
            card.grid(row=0, column=i, padx=(0, 20) if i < 2 else 0, sticky="nsew")
            cards.grid_columnconfigure(i, weight=1)
            card.bind("<Button-1>", lambda e, k=key: self._show_page(k))
            tk.Label(card, text=title, font=("Microsoft YaHei UI", 14, "bold"),
                     fg=COLORS["title"], bg=COLORS["card"]).pack(
                         anchor="w", padx=18, pady=(18, 6))
            tk.Label(card, text=desc, font=("Microsoft YaHei UI", 10),
                     fg=COLORS["muted"], bg=COLORS["card"], justify="left").pack(
                         anchor="w", padx=18, pady=(0, 18))

        info = tk.Frame(page, bg=COLORS["card"], highlightthickness=1,
                        highlightbackground=COLORS["border"])
        info.pack(fill="x", padx=30, pady=(10, 16))
        tk.Label(info, text="当前配置", font=("Microsoft YaHei UI", 12, "bold"),
                 fg=COLORS["title"], bg=COLORS["card"]).pack(anchor="w", padx=18, pady=(14, 6))
        self.dash_info = tk.Label(info, text="", font=("Microsoft YaHei UI", 10),
                                  fg=COLORS["text"], bg=COLORS["card"], justify="left")
        self.dash_info.pack(anchor="w", padx=18, pady=(0, 14))

        tip = tk.Frame(page, bg=COLORS["primary_light"])
        tip.pack(fill="x", padx=30, pady=(0, 16))
        tk.Label(tip, text="⚠ 使用提示", font=("Microsoft YaHei UI", 11, "bold"),
                 fg=COLORS["primary_dark"], bg=COLORS["primary_light"]).pack(
                     anchor="w", padx=14, pady=(10, 2))
        tk.Label(tip, text=("只需在【参数设置】填写登录 Access-Token 即可开始刷课（课程 / 考试 ID 留空"
                            "时自动使用默认安全教育课）。自动操作可能被平台判定为异常，仅限本人账号学习使用。"),
                 font=("Microsoft YaHei UI", 10), fg=COLORS["primary_dark"],
                 bg=COLORS["primary_light"], justify="left", wraplength=880).pack(
                     anchor="w", padx=14, pady=(0, 10))

    # ---------------- 刷课页 ----------------
    def _build_learn(self):
        page = self._page_container("learn")
        self._header(page, "自动刷课", "自动遍历课程全部知识点，模拟观看视频 / 阅读 PDF 至 100%")

        opt = tk.Frame(page, bg=COLORS["card"], highlightthickness=1,
                       highlightbackground=COLORS["border"])
        opt.pack(fill="x", padx=30, pady=(8, 16))
        self.fast_var = tk.BooleanVar(value=False)
        tk.Checkbutton(opt, text="快速模式（每个知识点一次性上报，更快但更易触发风控）",
                       variable=self.fast_var, font=("Microsoft YaHei UI", 10),
                       fg=COLORS["text"], bg=COLORS["card"],
                       activebackground=COLORS["card"], selectcolor="#FFFFFF").pack(
                           anchor="w", padx=18, pady=14)

        act = tk.Frame(page, bg=COLORS["bg"])
        act.pack(fill="x", padx=30)
        self.learn_btn = RoundButton(act, "开始刷课", command=self._start_learn,
                                     bg=COLORS["primary"], height=46)
        self.learn_btn.pack(side="left")

        self.learn_bar = ttk.Progressbar(page, mode="determinate", maximum=100,
                                         style="TProgressbar")
        self.learn_bar.pack(fill="x", padx=30, pady=(20, 8))
        self.learn_prog = tk.Label(page, text="进度：0 / 0",
                                   font=("Microsoft YaHei UI", 10),
                                   fg=COLORS["muted"], bg=COLORS["bg"])
        self.learn_prog.pack(anchor="w", padx=30)

    # ---------------- 进度查询页 ----------------
    def _build_status(self):
        page = self._page_container("status")
        self._header(page, "进度查询", "查看每个知识点真实的完成状态与百分比")

        act = tk.Frame(page, bg=COLORS["bg"])
        act.pack(fill="x", padx=30, pady=(0, 14))
        self.status_btn = RoundButton(act, "刷新进度", command=self._start_status,
                                      bg=COLORS["primary"], height=44)
        self.status_btn.pack(side="left")

        self.summary_card = tk.Frame(page, bg=COLORS["card"],
                                     highlightthickness=1,
                                     highlightbackground=COLORS["border"])
        self.summary_card.pack(fill="x", padx=30, pady=(0, 14))
        self.summary_fill = tk.Frame(self.summary_card, bg=COLORS["card"])
        self.summary_fill.pack(fill="x", padx=18, pady=12)
        self.summary_label = tk.Label(self.summary_fill,
                                      text="尚未查询，点击上方按钮获取课程进度。",
                                      font=("Microsoft YaHei UI", 11),
                                      fg=COLORS["text"], bg=COLORS["card"], justify="left")
        self.summary_label.pack(anchor="w")

        self.status_table_frame = tk.Frame(page, bg=COLORS["bg"])
        self.status_table_frame.pack(fill="both", expand=True, padx=30, pady=(0, 20))
        self._init_status_table()

    def _init_status_table(self):
        cols = ("section", "name", "fs", "bfb", "hour")
        self.tree = ttk.Treeview(self.status_table_frame, columns=cols, show="headings", height=14)
        headings = {
            "section": ("章节", 60),
            "name": ("知识点", 200),
            "fs": ("状态", 60),
            "bfb": ("完成度", 60),
            "hour": ("已学/需学(秒)", 90),
        }
        for c in cols:
            text, w = headings[c]
            self.tree.heading(c, text=text)
            anchor = "w" if c in ("section", "name") else "center"
            self.tree.column(c, width=w, anchor=anchor)
        style = ttk.Style(self)
        style.configure("Treeview", font=("Microsoft YaHei UI", 10), rowheight=26,
                        background="#FFFFFF", fieldbackground="#FFFFFF",
                        foreground=COLORS["text"])
        style.configure("Treeview.Heading", font=("Microsoft YaHei UI", 10, "bold"),
                        background=COLORS["primary_light"], foreground=COLORS["title"])
        style.map("Treeview", background=[("selected", COLORS["primary_light"])],
                  foreground=[("selected", COLORS["title"])])
        self.tree.pack(fill="both", expand=True)
        self.tree.tag_configure("done", foreground=COLORS["accent"])
        self.tree.tag_configure("todo", foreground=COLORS["text"])

    # ---------------- 考试页 ----------------
    def _build_exam(self):
        page = self._page_container("exam")
        self._header(page, "自动考试", "读取试卷、逐题作答并提交（内置题库已实测满分）")

        opt = tk.Frame(page, bg=COLORS["card"], highlightthickness=1,
                       highlightbackground=COLORS["border"])
        opt.pack(fill="x", padx=30, pady=(8, 16))
        tk.Label(opt, text="考试 ID（examId）：", font=("Microsoft YaHei UI", 10),
                 fg=COLORS["text"], bg=COLORS["card"]).pack(anchor="w", padx=18, pady=(12, 4))
        self.exam_id_entry = tk.Entry(opt, font=("Microsoft YaHei UI", 11),
                                      bd=1, relief="solid", highlightthickness=1,
                                      highlightbackground=COLORS["border"], fg=COLORS["text"])
        self.exam_id_entry.pack(fill="x", padx=18, pady=(0, 6), ipady=5)
        tk.Label(opt, text="若试卷存在题库外的题目，将自动中止提交（避免答错丢分）。",
                 font=("Microsoft YaHei UI", 9), fg=COLORS["muted"],
                 bg=COLORS["card"]).pack(anchor="w", padx=18, pady=(0, 12))

        act = tk.Frame(page, bg=COLORS["bg"])
        act.pack(fill="x", padx=30)
        self.exam_btn = RoundButton(act, "开始考试", command=self._start_exam,
                                    bg=COLORS["warn"], height=46)
        self.exam_btn.pack(side="left")

    # ---------------- 设置页 ----------------
    def _build_settings(self):
        page = self._page_container("settings")
        self._header(page, "参数设置", "填写登录凭证与课程 / 考试参数")

        card = tk.Frame(page, bg=COLORS["card"], highlightthickness=1,
                        highlightbackground=COLORS["border"])
        card.pack(fill="x", padx=30, pady=(8, 16))

        rows = [
            ("token", "Access-Token (登录凭证)", True),
            ("tenant_id", "租户号 tenant_id", False),
            ("course_id", "课程 ID（留空=默认安全教育课）", False),
            ("exam_id", "考试 ID（留空=默认）", False),
            ("interval_between", "知识点间隔秒数", False),
        ]
        self.entries = {}
        for i, (key, label, is_secret) in enumerate(rows):
            r = tk.Frame(card, bg=COLORS["card"])
            r.pack(fill="x", padx=20, pady=(12, 4) if i else (18, 4))
            tk.Label(r, text=label, font=("Microsoft YaHei UI", 10, "bold"),
                     fg=COLORS["text"], bg=COLORS["card"], width=24,
                     anchor="w").pack(side="left")
            self.entries[key] = tk.Entry(r, font=("Consolas", 11),
                                         bd=1, relief="solid",
                                         show="*" if is_secret else "",
                                         highlightthickness=1,
                                         highlightbackground=COLORS["border"],
                                         fg=COLORS["text"])
            self.entries[key].pack(side="left", fill="x", expand=True, ipady=5)

        tk.Label(card, text=("Token 获取：登录平台后按 F12 → Application → Local Storage，"
                             "复制 Access-Token 的值。Token 约 7 天过期。"),
                 font=("Microsoft YaHei UI", 9), fg=COLORS["muted"],
                 bg=COLORS["card"], wraplength=760, justify="left").pack(
                     anchor="w", padx=20, pady=(8, 6))

        act = tk.Frame(page, bg=COLORS["bg"])
        act.pack(fill="x", padx=30)
        self.save_btn = RoundButton(act, "保存配置", command=self._save_config,
                                    bg=COLORS["accent"], height=44)
        self.save_btn.pack(side="left")
        RoundButton(act, "恢复默认", command=self._reset_default,
                    bg="#98A1C0", height=44).pack(side="left", padx=(12, 0))

    # ---------------- 关于页 ----------------
    def _build_about(self):
        page = self._page_container("about")
        self._header(page, "关于说明", "南邮在线课堂自动化助手")

        card = tk.Frame(page, bg=COLORS["card"], highlightthickness=1,
                        highlightbackground=COLORS["border"])
        card.pack(fill="x", padx=30, pady=8)
        text = (
            "南邮在线课堂自动化助手\n"
            "──────────────────────\n"
            "功能：\n"
            "  ▶ 自动刷课 —— 遍历课程全部知识点，模拟观看视频 / PDF 至 100%\n"
            "  ▶ 进度查询 —— 查看每个知识点的真实完成状态\n"
            "  ▶ 自动考试 —— 读取试卷、逐题作答并提交\n\n"
            "原理：\n"
            "  通过调用平台真实接口（study.njupt.edu.cn）模拟学习与答题，\n"
            "  仅依赖 Python 标准库，无需安装任何第三方包。\n\n"
            "来源：\n"
            "  本项目基于开源项目 njupt-course-auto 二次开发。\n\n"
            "⚠ 免责声明：\n"
            "  本工具仅用于本人账号自主学习 / 补课。自动操作为绕过平台\n"
            "  防挂机 / 防作弊限制的行为，可能被判定为异常，存在账号风险。\n"
            "  请自行评估，切勿用于批量处理他人账号，须遵守学校规定。\n"
        )
        tk.Label(card, text=text, font=("Microsoft YaHei UI", 11),
                 fg=COLORS["text"], bg=COLORS["card"], justify="left").pack(
                     anchor="w", padx=20, pady=18)

    # ---------------- 共享日志区 ----------------
    def _build_shared_log(self):
        self.log_frame = tk.Frame(self.main, bg=COLORS["card"],
                                  highlightthickness=1,
                                  highlightbackground=COLORS["border"])
        head = tk.Frame(self.log_frame, bg=COLORS["card"])
        head.pack(fill="x", padx=14, pady=(10, 4))
        tk.Label(head, text="运行日志", font=("Microsoft YaHei UI", 11, "bold"),
                 fg=COLORS["title"], bg=COLORS["card"]).pack(anchor="w")
        clear_btn = tk.Label(head, text="清空", font=("Microsoft YaHei UI", 9),
                             fg=COLORS["primary"], bg=COLORS["card"], cursor="hand2")
        clear_btn.pack(side="right")
        clear_btn.bind("<Button-1>", lambda e: self._clear_log())

        self.log_text = scrolledtext.ScrolledText(
            self.log_frame, wrap="word", height=10,
            font=("Consolas", 10), bg="#FBFCFE", fg=COLORS["text"],
            bd=0, highlightthickness=1, highlightbackground=COLORS["border"])
        self.log_text.pack(fill="both", expand=True, padx=14, pady=(0, 14))
        self.log_text.tag_configure("log_info", foreground="#3B3F5C")
        self.log_text.tag_configure("log_warn", foreground="#B87312")
        self.log_text.tag_configure("log_error", foreground="#D9403F")
        self.log_text.tag_configure("log_success", foreground="#00A876")
        self.log_text.configure(state="disabled")

    def _clear_log(self):
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

    # ---------------- 配置读写 ----------------
    def _sync_exam_entry(self):
        """设置页与考试页的 exam_id 双向同步取当前值。"""
        if hasattr(self, "exam_id_entry"):
            if self.entries and "exam_id" in self.entries:
                val = self.entries["exam_id"].get().strip()
            else:
                val = self.config_data.get("exam_id", "")
            self.exam_id_entry.delete(0, "end")
            self.exam_id_entry.insert(0, val)

    def _load_config_into_form(self):
        mapping = {"token": "token", "tenant_id": "tenant_id",
                   "course_id": "course_id", "exam_id": "exam_id",
                   "interval_between": "interval_between"}
        for form_key, cfg_key in mapping.items():
            if form_key in self.entries:
                val = self.config_data.get(cfg_key, "")
                self.entries[form_key].delete(0, "end")
                self.entries[form_key].insert(0, str(val))
        self._sync_exam_entry()

    def _collect_config_from_form(self):
        self.config_data["token"] = self.entries["token"].get().strip()
        self.config_data["tenant_id"] = self.entries["tenant_id"].get().strip() or "0"
        self.config_data["course_id"] = self.entries["course_id"].get().strip()
        # 设置页与考试页取非空值
        if hasattr(self, "exam_id_entry") and self.exam_id_entry.get().strip():
            self.config_data["exam_id"] = self.exam_id_entry.get().strip()
        else:
            self.config_data["exam_id"] = self.entries["exam_id"].get().strip()
        try:
            self.config_data["interval_between"] = int(
                self.entries["interval_between"].get().strip())
        except ValueError:
            self.config_data["interval_between"] = 6
        return self.config_data

    def _apply_config_to_api(self):
        from njupt_api import DEFAULT_COURSE_ID
        self.api.token = self.config_data.get("token", "")
        self.api.tenant_id = self.config_data.get("tenant_id", "0")
        # 课程 ID 留空 = 默认安全教育课
        self.api.course_id = self.config_data.get("course_id", "") or DEFAULT_COURSE_ID
        self.api.interval_between = int(self.config_data.get("interval_between", 6))

    def _save_config(self, show=True):
        self._collect_config_from_form()
        NJUPTApi.save_config(self.config_data)
        self._apply_config_to_api()
        self._update_dashboard_info()
        self._append_log("success", "配置已保存。")
        if show:
            messagebox.showinfo("保存成功", "配置已保存到 " + os.path.basename(CONFIG_PATH))

    def _reset_default(self):
        self.config_data = {
            "token": "", "tenant_id": "0",
            "course_id": "",
            "interval_between": 6,
            "exam_id": "",
        }
        self._load_config_into_form()
        self._append_log("info", "已恢复默认配置：课程/考试 ID 留空即用默认安全教育课（未保存，请点击保存生效）。")

    def _update_dashboard_info(self):
        if "dash_info" not in self.__dict__:
            return
        from njupt_api import DEFAULT_COURSE_ID, DEFAULT_EXAM_ID
        c = self.config_data
        token_txt = c.get("token") or ""
        if len(token_txt) > 12:
            token_disp = token_txt[:6] + "..." + token_txt[-4:]
        elif token_txt:
            token_disp = "已填写"
        else:
            token_disp = "（空）"
        cid = c.get("course_id", "") or DEFAULT_COURSE_ID
        eid = c.get("exam_id", "") or DEFAULT_EXAM_ID
        cid_txt = ("%s（默认安全教育课，留空即用）" % cid) if not c.get("course_id") else str(cid)
        self.dash_info.configure(text=(
            "课程ID：%s\n考试ID：%s\nToken：%s\n知识点间隔：%s 秒" % (
                cid_txt, eid, token_disp, c.get("interval_between", 6))))

    # ---------------- 页面切换 ----------------
    def _show_page(self, key):
        self._current_page = key
        for p in self.pages.values():
            p.pack_forget()
        self.log_frame.pack_forget()
        page = self.pages[key]
        page.pack(fill="both", expand=True)
        if key in ("learn", "status", "exam"):
            self.log_frame.pack(fill="both", expand=True, padx=30, pady=(0, 20))
        for k, btn in self.nav_buttons.items():
            if k == key:
                btn.configure(bg=COLORS["primary"], fg="#FFFFFF",
                              font=("Microsoft YaHei UI", 12, "bold"))
            else:
                btn.configure(bg=COLORS["sidebar"], fg="#C7CEE8",
                              font=("Microsoft YaHei UI", 12))
        if key == "dashboard":
            self._update_dashboard_info()

    # ---------------- 任务管理 ----------------
    def _set_busy(self, busy):
        self._busy = busy
        self.conn_state.configure(text="● 运行中" if busy else "● 空闲",
                                  fg="#66FFB2" if busy else "#9FA8DA")
        for b in (getattr(self, "learn_btn", None),
                  getattr(self, "status_btn", None),
                  getattr(self, "exam_btn", None)):
            if b is not None:
                b.set_disabled(busy)

    def _run_task(self, fn):
        if self._busy:
            messagebox.showwarning("提示", "已有任务在运行，请先等待完成。")
            return
        self._set_busy(True)
        self._apply_config_to_api()
        t = threading.Thread(target=self._task_wrapper, args=(fn,), daemon=True)
        t.start()

    def _task_wrapper(self, fn):
        try:
            fn()
        except ApiError as e:
            self._queue_log("error", str(e))
            self._show_error("操作失败", str(e))
        except Exception as e:
            self._queue_log("error", "发生异常: %s" % e)
            self._show_error("操作失败", str(e))
        finally:
            self._set_busy(False)

    def _show_error(self, title, msg):
        try:
            messagebox.showerror(title, msg)
        except Exception:
            pass

    # ---------------- 各功能 ----------------
    def _start_learn(self):
        self._save_config(show=False)
        fast = self.fast_var.get()
        self.api.set_fast(fast)
        self._run_task(lambda: self._do_learn(fast))

    def _do_learn(self, fast):
        self._append_log("info", "=" * 50)
        self._append_log("info", "开始自动刷课...")
        done, total = self.api.learn_course(fast=fast)
        self.learn_bar["maximum"] = max(total, 1)
        self.learn_bar["value"] = done
        self.learn_prog.configure(text="进度：%d / %d" % (done, total))
        self._append_log("success", "刷课任务结束（成功 %d / 共 %d）" % (done, total))
        try:
            messagebox.showinfo("完成", "刷课结束：成功 %d / 共 %d 个知识点" % (done, total))
        except Exception:
            pass

    def _start_status(self):
        self._save_config(show=False)
        self._run_task(self._do_status)

    def _do_status(self):
        self._append_log("info", "正在查询课程进度...")
        summary, rows = self.api.query_status()
        self.summary_label.configure(text=(
            "课程：%s   来源：%s   类型：%s\n完成度：%d / %d  (%.1f%%)" % (
                summary["name"], summary["source"] or "—",
                summary["courseType"] or "—",
                summary["done"], summary["total"], summary["percent"])))
        for item in self.tree.get_children():
            self.tree.delete(item)
        for r in rows:
            done = r["fs"] == 1
            self.tree.insert("", "end", values=(
                r["section"], r["name"],
                "已完成" if done else "未完成",
                ("%s%%" % r["finishBfb"]) if r["finishBfb"] is not None else "—",
                "%s / %s" % (r["finishHour"], r["knowHour"])),
                tags=("done" if done else "todo",))
        self._append_log("success", "查询完成：%d / %d" % (summary["done"], summary["total"]))

    def _start_exam(self):
        self._save_config(show=False)
        exam_id = self.exam_id_entry.get().strip() or None
        if not exam_id:
            messagebox.showwarning("提示", "请先在考试页或设置中填写考试 ID。")
            return
        self._run_task(lambda: self._do_exam(exam_id))

    def _do_exam(self, exam_id):
        self._append_log("info", "=" * 50)
        self._append_log("info", "开始自动考试...")
        result = self.api.run_exam(exam_id)
        if result["submitted"]:
            self._append_log("success", "考试提交完成（已答 %d / %d 题）" % (
                result["filled"], result["total"]))
            try:
                messagebox.showinfo("完成", "考试已提交（已答 %d / %d 题）" % (
                    result["filled"], result["total"]))
            except Exception:
                pass
        else:
            self._append_log("warn", "试卷含 %d 道题库外题目，已中止提交。" % len(
                result.get("unanswered", [])))
            try:
                messagebox.showwarning("注意", "试卷含题库外题目，为避免答错丢分，本次未提交。\n请在日志中查看题目，补充答案后重试。")
            except Exception:
                pass

    # ---------------- 关闭 ----------------
    def _on_close(self):
        if self._busy:
            try:
                if not messagebox.askyesno("确认", "有任务仍在运行，确定退出吗？"):
                    return
            except Exception:
                pass
        self.destroy()


def main():
    try:
        app = NJUPTApp()
        app.mainloop()
    except Exception as e:
        try:
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("启动失败", str(e))
            root.destroy()
        except Exception:
            raise


if __name__ == "__main__":
    main()
