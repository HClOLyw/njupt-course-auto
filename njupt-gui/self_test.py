# -*- coding: utf-8 -*-
"""快速自检：实例化 GUI，校验关键控件存在且能正常构建/切换页面。"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import tkinter as tk
import njupt_gui
from njupt_gui import NJUPTApp

app = NJUPTApp()
app.update_idletasks()

checks = []
def check(name, cond):
    checks.append((name, bool(cond)))

# 关键控件
check("窗口标题", "南邮在线课堂" in app.title())
check("导航按钮数", len(app.nav_buttons) == 6)
check("页面数", len(app.pages) == 6)
check("刷课按钮", hasattr(app, "learn_btn"))
check("进度按钮", hasattr(app, "status_btn"))
check("考试按钮", hasattr(app, "exam_btn"))
check("设置输入框", len(app.entries) == 5)
check("日志框", hasattr(app, "log_text"))

# 页面切换遍历
for key in ("dashboard","learn","status","exam","settings","about"):
    app._show_page(key)
    app.update_idletasks()
check("页面切换遍历", app._current_page in ("dashboard","learn","status","exam","settings","about"))

# 配置读取/保存
import os, json
cfg = app.config_data
app._update_dashboard_info()
check("仪表盘配置显示", app.dash_info.cget("text") != "")

# 恢复默认
app._reset_default()
check("恢复默认course_id", app.entries["course_id"].get() == "2077931772737286146")

# API 缺 token 时报错（正确行为）
from njupt_api import NJUPTApi, ApiError
api = NJUPTApi(token="")
try:
    api.query_status()
    check("缺token应报错", False)
except ApiError:
    check("缺token应报错", True)

app.destroy()

ok = all(c for _, c in checks)
print("="*40)
for name, c in checks:
    print(("PASS " if c else "FAIL ") + name)
print("="*40)
print("ALL PASS" if ok else "SOME FAILED")
sys.exit(0 if ok else 1)
