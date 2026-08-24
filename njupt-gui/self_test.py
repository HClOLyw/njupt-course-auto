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

# 恢复默认（course_id 留空 = 使用默认安全教育课）
app._reset_default()
check("恢复默认course_id留空", app.entries["course_id"].get() == "")
check("恢复默认exam_id留空", app.entries["exam_id"].get() == "")
# 应用配置时回退到默认课程
app._apply_config_to_api()
check("留空时API回退默认课程", app.api.course_id == "2077931772737286146")
check("留空时API回退默认考试", app.api.run_exam is not None)
# 考试页留空时 _start_exam 不应因缺 ID 提前返回（走后台任务路径）
app.exam_id_entry.delete(0, "end")
app.exam_id_entry.insert(0, "")
app._busy = False
started = []
orig_run_task = app._run_task
def fake_run_task(fn):
    started.append(fn)
app._run_task = fake_run_task
app._start_exam()
app._run_task = orig_run_task
check("考试ID留空可启动(不弹窗)", len(started) == 1)

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
