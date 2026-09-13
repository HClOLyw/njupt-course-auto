# -*- coding: utf-8 -*-
"""
run_lab_learn.py —— 实验室安全教育全课程刷课运行器（后台）
=========================================================
读取 config.json 的 lab_token（或环境变量 LAB_TOKEN），
按正常模式（分段上报进度）遍历所有未完成课程刷完。

用法：  python run_lab_learn.py
"""
import io
import os
import sys
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", write_through=True)

from njupt_lab_api import LabApi

token = (os.environ.get("LAB_TOKEN") or "").strip()
if not token:
    token = LabApi.load_config().get("lab_token", "").strip()
if not token:
    print("!! 未找到 token：请设置环境变量 LAB_TOKEN，或在 config.json 配置 lab_token")
    sys.exit(2)

api = LabApi(token=token, interval_between=6,
             log_callback=lambda lv, tx: print("[%s] %s" % (lv, tx), flush=True))

print("开始刷实验室课程（正常模式，间隔 6 秒）...", flush=True)
t0 = time.time()
done, total, failed = api.learn_all(fast=False)
dt = time.time() - t0
print("", flush=True)
print("刷课结束：成功 %d / %d 门，耗时 %d 分 %d 秒"
      % (done, total, dt // 60, dt % 60), flush=True)
if failed:
    print("失败课程: %s" % ", ".join(str(x) for x in failed), flush=True)
print("ALL_DONE", flush=True)