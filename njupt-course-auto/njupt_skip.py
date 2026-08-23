#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
南京邮电大学 在线培训平台 (study.njupt.edu.cn) 刷课脚本
=====================================================

原理（通过对平台前端 JS 逆向得出，调用其真实接口，与浏览器行为一致）：
- 课程详情   GET  /service-api/app/study/course/info?id={courseId}
- 上报学习   POST /service-api/app/study/my/course/start
             参数: courseId, sectionId, knowId, playTime, end, intervalTime,
                   currentPage, totalPage
- 认证       请求头 X-Access-Token = localStorage["Access-Token"]

仅依赖 Python 标准库，无需 pip 安装任何第三方包。

⚠️  仅用于你本人账号，自行学习/补课用途。
    平台可能据此判定异常，请自行评估风险。切莫用于批量他人账号。

使用前：先完成登录，然后把浏览器里的 Access-Token 填入 config.json，
或通过环境变量 NJUPT_TOKEN / 命令行 --token 传入。
"""

import json
import math
import os
import ssl
import sys
import time
import urllib.parse
import urllib.request

# ------------------------- 基础配置 -------------------------
API_BASE = "https://study.njupt.edu.cn/service-api"
DEFAULT_COURSE_ID = "2077931772737286146"   # 用户课程 URL 中的 id
DEFAULT_TENANT = "0"

# 默认上报节奏（参考前端：视频 5s、PDF 8s 一次）
INTERVAL_VIDEO = 5
INTERVAL_PDF = 8
# 模拟观看时，每轮 playTime 递增的秒数（越小越接近真实，请求越多）
SIM_STEP = 60

# 忽略 SSL 校验（平台证书自签/链不完整时避免报错）
_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE


# ------------------------- 凭证 & 配置加载 -------------------------
def load_config():
    cfg = {
        "token": "",
        "tenant_id": DEFAULT_TENANT,
        "course_id": DEFAULT_COURSE_ID,
        "fast": False,
        "interval_between": 6,
    }
    cfg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
    if os.path.exists(cfg_path):
        try:
            with open(cfg_path, encoding="utf-8") as f:
                data = json.load(f)
            cfg.update({k: v for k, v in data.items() if k in cfg})
        except Exception as e:
            print("[warn] 读取 config.json 失败:", e)
    cfg["token"] = os.environ.get("NJUPT_TOKEN", cfg["token"] or "")
    cfg["tenant_id"] = os.environ.get("NJUPT_TENANT", cfg["tenant_id"] or DEFAULT_TENANT)
    return cfg


def parse_args():
    cfg = load_config()
    argv = sys.argv[1:]
    if "--fast" in argv:
        cfg["fast"] = True
        argv = [a for a in argv if a != "--fast"]
    # 支持 --token=xxx --course=xxx --tenant=xxx
    for a in list(argv):
        if a.startswith("--token="):
            cfg["token"] = a.split("=", 1)[1]
        elif a.startswith("--course="):
            cfg["course_id"] = a.split("=", 1)[1]
        elif a.startswith("--tenant="):
            cfg["tenant_id"] = a.split("=", 1)[1]
    if not cfg.get("course_id"):
        cfg["course_id"] = DEFAULT_COURSE_ID
    return cfg


# ------------------------- HTTP 封装(标准库) -------------------------
def _headers(cfg):
    # token/tenant 若含非 ASCII(中文)则 HTTP 头无法编码，提前校验并给出提示
    for name, val in (("X-Access-Token", cfg["token"]), ("tenant_id", cfg["tenant_id"])):
        if isinstance(val, str) and any(ord(c) > 127 for c in val):
            print("[!] 请求头 %s 包含非 ASCII 字符，请检查：是否把说明文字填成了凭证？" % name)
            sys.exit(1)
    return {
        "X-Access-Token": cfg["token"],
        "tenant_id": cfg["tenant_id"],
        "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"),
        "Accept": "application/json, text/plain, */*",
    }


def _request(cfg, method, path, params=None, data=None):
    url = API_BASE + path
    if params:
        url = url + "?" + urllib.parse.urlencode(params)
    body = None
    headers = _headers(cfg)
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    with urllib.request.urlopen(req, context=_SSL_CTX, timeout=20) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
    return json.loads(raw)


def api_get(cfg, path, params):
    return _request(cfg, "GET", path, params=params)


def api_post(cfg, path, data):
    return _request(cfg, "POST", path, data=data)


# ------------------------- 业务逻辑 -------------------------
def get_course(cfg, course_id):
    res = api_get(cfg, "/app/study/course/info", {"id": course_id})
    if not res.get("success"):
        print("获取课程失败:", res.get("message", res.get("code", res)))
        return None
    return res["result"]


def _target_seconds(know):
    """一个知识点需要达到的播放秒数。
    优先用 knowHour(该视频总时长/需学秒数)，回退到 finishHour，最后默认 60。"""
    for key in ("knowHour", "finishHour"):
        v = know.get(key)
        try:
            v = float(v) if v not in (None, "", "null") else 0
        except (TypeError, ValueError):
            v = 0
        if v and v > 0:
            return v
    return 60  # 缺失时默认 60 秒


def _is_multi_window(res):
    """判断响应是否为'多窗口/多端'风控。"""
    if not isinstance(res, dict):
        return False
    msg = str(res.get("message", ""))
    return ("多窗口" in msg) or ("多端" in msg) or ("重复" in msg)


def report_progress(cfg, know, section_id, play_time, end_flag, interval_time,
                    current_page=1, total_page=0, retries=3):
    data = {
        "courseId": know.get("courseId", ""),
        "sectionId": section_id,
        "knowId": know["id"],
        "playTime": int(play_time),
        "end": 1 if end_flag else 0,
        "intervalTime": interval_time,
        "currentPage": current_page,
        "totalPage": total_page,
    }
    res = api_post(cfg, "/app/study/my/course/start", data)
    if res.get("success"):
        return res
    if _is_multi_window(res) and retries > 0:
        wait = 10 + (3 - retries) * 10  # 10,20,30 秒逐次递增
        print("    触发'多窗口'风控，等待 %d 秒后重试..." % wait)
        time.sleep(wait)
        return report_progress(cfg, know, section_id, play_time, end_flag, interval_time,
                               current_page=current_page, total_page=total_page,
                               retries=retries - 1)
    print("    上报失败:", res.get("message", res.get("code", res)))
    return res


def learn_video(cfg, course, section, know):
    know_id = know["id"]
    target = int(_target_seconds(know))
    section_id = know.get("courseSectionId") or section["id"]
    name = know.get("knowName") or know_id
    print("  [视频] %s (knowId=%s) 目标秒数=%s" % (name, know_id, target))
    if cfg.get("fast"):
        res = report_progress(cfg, know, section_id, target, True, INTERVAL_VIDEO)
        return bool(res.get("success"))
    # 分段递增上报：每步不超过 SIM_STEP，且至少 2 步，最后一步 end=1
    n = max(2, int(math.ceil(target / SIM_STEP)))
    step = target / n
    cur = 0
    i = 0
    ok = True
    while cur < target:
        i += 1
        cur = min(target, int(round(i * step)))
        end_flag = cur >= target
        res = report_progress(cfg, know, section_id, cur, end_flag, INTERVAL_VIDEO)
        ok = bool(res.get("success")) and ok
        time.sleep(0.3)  # 轻微间隔，避免请求过密
    return ok


def learn_pdf(cfg, course, section, know):
    know_id = know["id"]
    target = int(_target_seconds(know))
    section_id = know.get("courseSectionId") or section["id"]
    total = know.get("pageTotal") or know.get("totalPage") or 1
    try:
        total = int(total)
    except (TypeError, ValueError):
        total = 1
    name = know.get("knowName") or know_id
    print("  [PDF] %s (knowId=%s) 目标=%s 总页=%s" % (name, know_id, target, total))
    if cfg.get("fast"):
        res = report_progress(cfg, know, section_id, target, True, INTERVAL_PDF,
                              current_page=total, total_page=total)
        return bool(res.get("success"))
    n = max(2, int(math.ceil(target / SIM_STEP)))
    step = target / n
    cur = 0
    i = 0
    ok = True
    while cur < target:
        i += 1
        cur = min(target, int(round(i * step)))
        end_flag = cur >= target
        res = report_progress(cfg, know, section_id, cur, end_flag, INTERVAL_PDF,
                              current_page=1, total_page=total)
        ok = bool(res.get("success")) and ok
        time.sleep(0.3)
    return ok


def learn_course(cfg):
    course_id = cfg["course_id"]
    print("=" * 60)
    print("课程ID:", course_id)
    course = get_course(cfg, course_id)
    if not course:
        return False
    print("课程名称:", course.get("name"))
    print("课程来源:", course.get("courseSource"), "| 分类:", course.get("courseType"))
    if course.get("learnStatus") == 1:
        print("(!) 该课程已标记为可通过，仍会继续补录。")
    sections = course.get("sectionList") or []
    if not sections:
        print("未找到章节/知识点。可能 token 无效或课程无内容。")
        return False

    done = 0
    total_know = 0
    for sec in sections:
        print("\n-- 章节: %s (sectionId=%s)" % (sec.get("name", ""), sec.get("id")))
        for know in sec.get("knowList") or []:
            total_know += 1
            know["courseId"] = course_id
            if know.get("finishStatus") == 1:
                print("  [跳过] %s 已完成" % (know.get("knowName") or know["id"]))
                done += 1
                continue
            kt = str(know.get("knowType"))
            try:
                if kt == "1":
                    ok = learn_video(cfg, course, sec, know)
                elif kt == "2":
                    ok = learn_pdf(cfg, course, sec, know)
                else:
                    print("  [未知类型] knowType=%s，跳过" % kt)
                    continue
                if ok:
                    done += 1
                    print("    [成功] 已上报完成")
                else:
                    print("    [失败] 上报异常")
            except Exception as e:
                print("    [异常] %s" % e)
            # 关键：平台会检测"多窗口同时观看"。处理完一个知识点后必须等待一段时间，
            # 让服务端释放会话，否则紧接着处理下一个会触发风控。
            gap = int(cfg.get("interval_between", 6))
            if gap and gap > 0:
                time.sleep(gap)
    print("\n" + "=" * 60)
    print("处理完成：%d/%d 个知识点" % (done, total_know))
    return True


def main():
    cfg = parse_args()
    if not cfg.get("token") or not str(cfg["token"]).strip():
        print("[!] 未提供 Access-Token。")
        print("    获取方法：登录平台后，浏览器 F12 -> Application/Local Storage，")
        print("    复制键名 Access-Token 的值，即可作为脚本凭证。")
        print("    可写入同目录 config.json 的 token 字段，或用 --token=xxx 传入。")
        return 2
    if cfg.get("fast"):
        print(">>> 快速模式(fast)：每个知识点一次性上报到位。")
    ok = learn_course(cfg)
    print("\n脚本结束。")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
