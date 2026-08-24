# -*- coding: utf-8 -*-
"""
njupt_api.py —— 南邮在线课堂核心接口封装
========================================
将 njupt-course-auto 仓库的三大功能（刷课 / 查进度 / 考试）封装为可复用类，
供 GUI 界面调用。仅依赖 Python 标准库。

⚠️ 仅供本人账号自主学习使用，请自行评估平台风险。
"""
import json
import math
import os
import ssl
import time
import urllib.parse
import urllib.request

API_BASE = "https://study.njupt.edu.cn/service-api"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(SCRIPT_DIR, "config.json")

# 默认值
DEFAULT_TENANT = "0"
DEFAULT_COURSE_ID = "2077931772737286146"
DEFAULT_EXAM_ID = "2078031452989038593"
DEFAULT_INTERVAL = 6

# 忽略 SSL 校验（平台证书自签/链不完整）
_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE


class ApiError(Exception):
    """API 业务错误（带用户可读的中文提示）。"""
    pass


class NJUPTApi:
    def __init__(self, token="", tenant_id=DEFAULT_TENANT,
                 course_id=DEFAULT_COURSE_ID, interval_between=DEFAULT_INTERVAL,
                 log_callback=None):
        self.token = (token or "").strip()
        self.tenant_id = tenant_id or DEFAULT_TENANT
        self.course_id = course_id or DEFAULT_COURSE_ID
        self.interval_between = int(interval_between or DEFAULT_INTERVAL)
        self.fast = False
        # 回调：接收 (level, text) 用于 GUI 日志输出，level 为 info/warn/error/success
        self._log_cb = log_callback

    # ------------ 日志 ------------
    def log(self, msg, level="info"):
        if self._log_cb:
            self._log_cb(level, str(msg))
        else:
            print(msg)

    def set_fast(self, fast):
        self.fast = bool(fast)

    # ------------ 配置加载/保存 ------------
    @classmethod
    def load_config(cls):
        cfg = {
            "token": "",
            "tenant_id": DEFAULT_TENANT,
            "course_id": DEFAULT_COURSE_ID,
            "interval_between": DEFAULT_INTERVAL,
        }
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, encoding="utf-8") as f:
                    data = json.load(f)
                cfg.update({k: v for k, v in data.items() if k in cfg})
            except Exception:
                pass
        return cfg

    @staticmethod
    def save_config(cfg):
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump({k: cfg.get(k) for k in (
                "token", "tenant_id", "course_id", "interval_between")},
                f, ensure_ascii=False, indent=2)

    # ------------ HTTP 封装 ------------
    def _headers(self):
        for name, val in (("X-Access-Token", self.token),
                          ("tenant_id", self.tenant_id)):
            if isinstance(val, str) and any(ord(c) > 127 for c in val):
                raise ApiError(
                    "请求头 %s 包含非 ASCII 字符，请检查是否把说明文字填成了凭证" % name)
        return {
            "X-Access-Token": self.token,
            "tenant_id": str(self.tenant_id),
            "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                           "AppleWebKit/537.36 (KHTML, like Gecko) "
                           "Chrome/120.0.0.0 Safari/537.36"),
            "Accept": "application/json, text/plain, */*",
        }

    def _request(self, method, path, params=None, data=None):
        if not self.token:
            raise ApiError("未提供 Access-Token，请先在【设置】中填写。")
        url = API_BASE + path
        if params:
            url = url + "?" + urllib.parse.urlencode(params)
        body = None
        headers = self._headers()
        if data is not None:
            body = json.dumps(data, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        with urllib.request.urlopen(req, context=_SSL_CTX, timeout=20) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
        return json.loads(raw)

    def api_get(self, path, params=None):
        return self._request("GET", path, params=params or {})

    def api_post(self, path, data=None):
        return self._request("POST", path, data=data)

    # ------------ 查进度 ------------
    def get_course(self, course_id=None):
        cid = course_id or self.course_id or DEFAULT_COURSE_ID
        res = self.api_get("/app/study/course/info", {"id": cid})
        if not res.get("success"):
            raise ApiError("获取课程失败: %s" % res.get("message", res.get("code", res)))
        return res.get("result")

    def query_status(self):
        """查询所有知识点进度，返回 (summary, rows)。"""
        course = self.get_course()
        rows = []
        done = 0
        total = 0
        sections = course.get("sectionList") or []
        for sec in sections:
            sec_name = sec.get("name", "")
            for kn in sec.get("knowList") or []:
                total += 1
                fs = kn.get("finishStatus")
                if fs == 1:
                    done += 1
                rows.append({
                    "section": sec_name,
                    "name": kn.get("knowName", ""),
                    "fs": fs,
                    "finishBfb": kn.get("finishBfb"),
                    "finishHour": kn.get("finishHour"),
                    "knowHour": kn.get("knowHour"),
                    "knowType": kn.get("knowType"),
                })
        summary = {
            "name": course.get("name"),
            "source": course.get("courseSource"),
            "courseType": course.get("courseType"),
            "course_id": self.course_id,
            "learnStatus": course.get("learnStatus"),
            "done": done,
            "total": total,
            "percent": (done * 100.0 / total) if total else 0,
        }
        return summary, rows

    # ------------ 刷课 ------------
    def _target_seconds(self, know):
        for key in ("knowHour", "finishHour"):
            v = know.get(key)
            try:
                v = float(v) if v not in (None, "", "null") else 0
            except (TypeError, ValueError):
                v = 0
            if v and v > 0:
                return v
        return 60

    def _is_multi_window(self, res):
        if not isinstance(res, dict):
            return False
        msg = str(res.get("message", ""))
        return ("多窗口" in msg) or ("多端" in msg) or ("重复" in msg)

    def report_progress(self, know, section_id, play_time, end_flag, interval_time,
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
        res = self.api_post("/app/study/my/course/start", data)
        if res.get("success"):
            return res
        if self._is_multi_window(res) and retries > 0:
            wait = 10 + (3 - retries) * 10
            self.log("    触发多窗口风控，等待 %d 秒后重试..." % wait, "warn")
            time.sleep(wait)
            return self.report_progress(know, section_id, play_time, end_flag,
                                        interval_time, current_page, total_page,
                                        retries - 1)
        self.log("    上报失败: %s" % res.get("message", res.get("code", res)), "error")
        return res

    def learn_video(self, course, section, know):
        know_id = know["id"]
        target = int(self._target_seconds(know))
        section_id = know.get("courseSectionId") or section["id"]
        name = know.get("knowName") or know_id
        self.log("  [视频] %s (knowId=%s) 目标秒数=%s" % (name, know_id, target))
        if self.fast:
            res = self.report_progress(know, section_id, target, True, 5)
            return bool(res.get("success"))
        n = max(2, int(math.ceil(target / 60)))
        step = target / n
        cur = 0
        i = 0
        ok = True
        while cur < target:
            i += 1
            cur = min(target, int(round(i * step)))
            end_flag = cur >= target
            res = self.report_progress(know, section_id, cur, end_flag, 5)
            ok = bool(res.get("success")) and ok
            time.sleep(0.3)
        return ok

    def learn_pdf(self, course, section, know):
        know_id = know["id"]
        target = int(self._target_seconds(know))
        section_id = know.get("courseSectionId") or section["id"]
        total = know.get("pageTotal") or know.get("totalPage") or 1
        try:
            total = int(total)
        except (TypeError, ValueError):
            total = 1
        name = know.get("knowName") or know_id
        self.log("  [PDF] %s (knowId=%s) 目标=%s 总页=%s" % (name, know_id, target, total))
        if self.fast:
            res = self.report_progress(know, section_id, target, True, 8,
                                       current_page=total, total_page=total)
            return bool(res.get("success"))
        n = max(2, int(math.ceil(target / 60)))
        step = target / n
        cur = 0
        i = 0
        ok = True
        while cur < target:
            i += 1
            cur = min(target, int(round(i * step)))
            end_flag = cur >= target
            res = self.report_progress(know, section_id, cur, end_flag, 8,
                                       current_page=1, total_page=total)
            ok = bool(res.get("success")) and ok
            time.sleep(0.3)
        return ok

    def learn_course(self, course_id=None, fast=False):
        cid = course_id or self.course_id or DEFAULT_COURSE_ID
        self.fast = fast
        self.log("=" * 60)
        self.log("课程ID: %s" % cid)
        course = self.get_course(cid)
        self.log("课程名称: %s" % course.get("name"))
        self.log("课程来源: %s | 分类: %s" % (course.get("courseSource"), course.get("courseType")))
        if course.get("learnStatus") == 1:
            self.log("(!) 该课程已标记为可通过，仍会继续补录。", "warn")
        sections = course.get("sectionList") or []
        if not sections:
            raise ApiError("未找到章节/知识点。可能 token 无效或课程无内容。")

        done = 0
        total_know = 0
        for sec in sections:
            self.log("")
            self.log("-- 章节: %s (sectionId=%s)" % (sec.get("name", ""), sec.get("id")))
            for know in sec.get("knowList") or []:
                total_know += 1
                know["courseId"] = cid
                if know.get("finishStatus") == 1:
                    self.log("  [跳过] %s 已完成" % (know.get("knowName") or know["id"]))
                    done += 1
                    continue
                kt = str(know.get("knowType"))
                try:
                    if kt == "1":
                        ok = self.learn_video(course, sec, know)
                    elif kt == "2":
                        ok = self.learn_pdf(course, sec, know)
                    else:
                        self.log("  [未知类型] knowType=%s，跳过" % kt, "warn")
                        continue
                    if ok:
                        done += 1
                        self.log("    [成功] 已上报完成", "success")
                    else:
                        self.log("    [失败] 上报异常", "error")
                except Exception as e:
                    self.log("    [异常] %s" % e, "error")
                gap = self.interval_between
                if gap and gap > 0:
                    time.sleep(gap)
        self.log("")
        self.log("=" * 60)
        self.log("处理完成：%d/%d 个知识点" % (done, total_know), "success")
        return done, total_know

    # ------------ 考试 ------------
    # 答案映射（questionsId -> 答案）
    ANSWERS = {
        "2077977470535077890": "C",
        "2077977470539272200": "B",
        "2077977470539272197": "D",
        "2077977470539272198": "C",
        "2077977470535077888": "D",
        "2077977470539272199": "C",
        "2077977470539272192": "D",
        "2077977470535077889": "C",
        "2077977470539272202": "D",
        "2077977470539272193": "C",
        "2077977470539272194": "C",
        "2077977470539272201": "B",
        "2077977470539272195": "B",
        "2077977470539272203": "C",
        "2077977470539272196": "B",
        "2077977470543466499": ["A", "C"],
        "2077977470543466496": ["A", "B", "C", "D"],
        "2077977470543466502": ["A", "B", "D"],
        "2077977470543466498": ["A", "C", "D"],
        "2077977470543466497": ["A", "C", "D"],
        "2077977470539272206": ["A", "B", "C"],
        "2077977470543466500": ["A", "B", "C", "D"],
        "2077977470543466501": ["A", "B", "D"],
        "2077977470539272205": ["A", "B", "C", "D"],
        "2077977470539272204": ["A", "B", "C", "D"],
    }
    DEFAULT_EXAM_ID = "2078031452989038593"

    def run_exam(self, exam_id=None):
        """自动考试作答并提交。返回结果字典。若遇到题库外题目则中止。"""
        eid = exam_id or self.DEFAULT_EXAM_ID
        self.log("=" * 60)
        self.log("开始自动考试 (examId=%s)" % eid)
        res = self.api_get("/exam/app/examDetail/loadExamDetailList",
                           {"examId": eid})
        result = res.get("result") or {}
        er_id = result.get("erId")
        status = result.get("status")
        ql = result.get("questionList") or []
        self.log("erId=%s | status=%s | 题目总数=%d" % (er_id, status, len(ql)))

        filled = 0
        unanswered = []
        for q in ql:
            qid = q.get("questionsId")
            if qid in self.ANSWERS:
                q["userAnswer"] = self.ANSWERS[qid]
                filled += 1
            else:
                unanswered.append(q)

        self.log("已填答案题数: %d / %d" % (filled, len(ql)))

        if unanswered:
            self.log("")
            self.log("=" * 60, "warn")
            self.log("[!] 有 %d 道题【不在题库内】，无法自动作答：" % len(unanswered), "warn")
            for i, q in enumerate(unanswered, 1):
                t = q.get("type")
                label = "多选" if str(t) == "2" else ("单选" if str(t) == "1" else "题型%s" % t)
                opts = " | ".join("%s.%s" % (o.get("optionAlias"), o.get("optionDesc"))
                                  for o in (q.get("optionsList") or []))
                self.log("  【%d】【%s】 %s" % (i, label, q.get("title")), "warn")
                self.log("     选项: %s" % opts, "warn")
                self.log("     questionsId: %s" % q.get("questionsId"), "warn")
            self.log("", "warn")
            self.log("[提示] 以上题目不在题库内，为避免答错丢分，本次【不提交】。", "warn")
            return {"submitted": False, "filled": filled, "total": len(ql),
                    "unanswered": unanswered}

        self.log("")
        self.log("全部题目均在题库内，开始提交...")
        resp = self.api_post("/exam/app/examDetail/saverecords", result)
        self.log("提交响应: %s" % json.dumps(resp, ensure_ascii=False)[:600])
        return {"submitted": True, "filled": filled, "total": len(ql),
                "response": resp}
