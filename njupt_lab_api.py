# -*- coding: utf-8 -*-
"""
njupt_lab_api.py —— 南邮实验室安全数字化教育平台接口封装
========================================================
面向 http://10.22.192.38:9092（后端 API: http://10.22.192.38:9090/jeecg-boot）
的自动化助手核心逻辑，与 njupt_api.py 风格一致，仅依赖 Python 标准库。

功能：
  1) 课程学习：列出我的课程 -> 看详情/嵌入式题目 -> 分段上报观看进度(finishRate)
     -> 时间点弹题作答(submitAnswer) -> 看完标记完成(finish)
  2) 考试：列出我的考试 -> 开始(startExam) -> 按答案作答 -> 提交(submitExam)
  3) 答案收集：通过"练习接口"的题目列表直接读取 correctAnswer，构建题库答案映射；
     课程嵌入式题目优先查题库，查不到则报错/跳过，避免盲目答错。

⚠️ 仅供本人账号自主学习使用，请自行评估平台风险。
"""
import json
import math
import os
import ssl
import sys
import time
import urllib.parse
import urllib.request

LAB_API_BASE = "http://10.22.192.38:9090/jeecg-boot"
LAB_WEB_BASE = "http://10.22.192.38:9092"

if getattr(sys, "frozen", False):
    # PyInstaller onefile：config.json 与 exe 同目录，保证保存能持久化
    SCRIPT_DIR = os.path.dirname(sys.executable)
else:
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(SCRIPT_DIR, "config.json")

# 默认值
DEFAULT_INTERVAL = 6          # 每个知识点之间等待秒数（防风控）
DEFAULT_REPORT_STEP = 10      # 进度上报步长（与网页端每 10 秒一致）

# 忽略 SSL 校验（平台证书自签/链不完整）
_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE


class LabApiError(Exception):
    """实验室平台 API 业务错误（带用户可读的中文提示）。"""
    pass


class LabApi:
    def __init__(self, token="", base=LAB_API_BASE, web=LAB_WEB_BASE,
                 interval_between=DEFAULT_INTERVAL, log_callback=None):
        self.token = (token or "").strip()
        self.base = (base or LAB_API_BASE).rstrip("/")
        self.web = (web or LAB_WEB_BASE).rstrip("/")
        self.interval_between = int(interval_between or DEFAULT_INTERVAL)
        # 答案库：questionsId -> 答案。单选/判断为 "A"，多选为 ["A","C"] 或 "A,C"
        self.answer_bank = {}
        # 题干 -> 答案 索引（题库与课程题目 id 可能不同，用题干兜底匹配）
        self._stem_index = {}
        self.fast = False
        self._log_cb = log_callback

    # ---------------- 日志 ----------------
    def log(self, msg, level="info"):
        if self._log_cb:
            self._log_cb(level, str(msg))
        else:
            print(msg)

    def set_fast(self, fast):
        self.fast = bool(fast)

    # ---------------- 配置加载/保存 ----------------
    @classmethod
    def load_config(cls):
        cfg = {
            "lab_token": "",
            "lab_base": LAB_API_BASE,
            "lab_web": LAB_WEB_BASE,
            "edu_mode": "freshman",
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
                "token", "tenant_id", "course_id", "interval_between",
                "lab_token", "lab_base", "lab_web")},
                f, ensure_ascii=False, indent=2)

    # ---------------- HTTP 封装 ----------------
    def _headers(self, base):
        for name, val in (("X-Access-Token", self.token),):
            if isinstance(val, str) and any(ord(c) > 127 for c in val):
                raise LabApiError(
                    "请求头 %s 包含非 ASCII 字符，请检查是否把说明文字填成了凭证" % name)
        return {
            "X-Access-Token": self.token,
            "Content-Type": "application/json;charset=UTF-8",
            "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                           "AppleWebKit/537.36 (KHTML, like Gecko) "
                           "Chrome/120.0.0.0 Safari/537.36"),
            "Accept": "application/json, text/plain, */*",
        }

    def _request(self, method, path, params=None, data=None, base=None):
        """发送请求并解析 JSON。base 默认走后端 API，也可传 self.web 访问前端静态。
        网络异常自动重试（3 次退避），最终失败抛 LabApiError。"""
        import urllib.error
        if not self.token:
            raise LabApiError("未提供实验室平台 Access-Token，请先在【参数设置】中填写。")
        base = (base or self.base).rstrip("/")
        url = base + path
        if params:
            url = url + "?" + urllib.parse.urlencode(params)
        body = None
        headers = self._headers(base)
        if data is not None:
            body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        last_err = None
        for attempt in range(4):
            try:
                with urllib.request.urlopen(req, context=_SSL_CTX, timeout=30) as resp:
                    raw = resp.read().decode("utf-8", errors="replace")
                try:
                    return json.loads(raw)
                except ValueError:
                    return {"success": True, "raw": raw[:500]}
            except (urllib.error.URLError, TimeoutError, OSError) as e:
                last_err = e
                if attempt < 3:
                    wait = 5 * (attempt + 1)
                    self.log("  网络异常(%s)，%d 秒后重试 (%d/3)..." % (e, wait, attempt + 1), "warn")
                    time.sleep(wait)
        raise LabApiError("网络请求失败（已重试 3 次）: %s" % last_err)

    def api_get(self, path, params=None, base=None):
        return self._request("GET", path, params=params or {}, base=base)

    def api_post(self, path, data=None, base=None):
        return self._request("POST", path, data=data or {}, base=base)

    @staticmethod
    def _check(res, what):
        if not isinstance(res, dict):
            raise LabApiError("%s返回异常: %s" % (what, res))
        if not res.get("success"):
            raise LabApiError("%s失败: %s" % (what, res.get("message", res.get("code", res))))

    @staticmethod
    def _rows(res):
        """兼容 result 为 dict{records...} 或 list 两种返回。"""
        result = res.get("result")
        if isinstance(result, dict):
            return result.get("records") or result.get("rows") or result.get("list") or []
        if isinstance(result, list):
            return result
        return []

    # ---------------- 课程 ----------------
    def my_courses(self, name=None, page=1, page_size=200):
        """列出我的课程。row 字段：id/name/watchDuration%/donum/total/unCorrectNum/isFinish。"""
        params = {"pageNo": page, "pageSize": page_size}
        if name:
            params["name"] = name
        res = self.api_get("/jcedutec/courseSource/myCourseList", params)
        self._check(res, "获取课程列表")
        return self._rows(res)

    def course_detail(self, cid):
        """课程详情（视频地址 url、名称、简介等）。"""
        res = self.api_get("/jcedutec/courseSource/queryById", {"id": cid})
        self._check(res, "获取课程详情")
        return res.get("result") or {}

    def course_questions(self, cid):
        """课程嵌入式题目（弹题）。字段：id/stem/kind/optiona-d/ejectTime/可能含 correctAnswer。"""
        res = self.api_get("/jcedutec/courseSource/queryCourseQuestionRelaByMainId", {"id": cid})
        self._check(res, "获取课程题目")
        return self._rows(res)

    def update_visits(self, cid):
        """记录访问课程。"""
        res = self.api_post("/jcedutec/courseSource/updateVisits", {"id": cid})
        if not res.get("success"):
            self.log("  记录访问失败: %s" % res.get("message", res), "warn")
        return bool(res.get("success"))

    def report_finish_rate(self, cid, watch_duration):
        """上报观看进度（秒）。网页端每 10s 上报一次。"""
        return self.api_post("/jcedutec/courseSource/finishRate",
                             {"id": cid, "watchDuration": int(watch_duration)})

    def submit_answer(self, cid, question_id, option):
        """作答课程弹题。option：单选为 "A"，多选为 ["A","C"]。"""
        return self.api_post("/jcedutec/courseSource/submitAnswer",
                             {"id": cid, "questionId": question_id, "option": option})

    def finish_course(self, cid):
        """标记课程完成。"""
        return self.api_post("/jcedutec/courseSource/finish", {"id": cid})

    def uncorrect_by_course(self, cid):
        """课程错题（含正确答案 correctAnswer / 解析 analysis）。"""
        res = self.api_get("/students/queryUnCorrectByCourseId", {"id": cid})
        self._check(res, "获取课程错题")
        return self._rows(res)

    # ---------------- 题库 / 练习（带正确答案） ----------------
    def question_types(self):
        """题型列表。row 字段：id/name/.../count 或 questionNum。"""
        res = self.api_get("/jcedutec/questionType/queryCountList", {})
        self._check(res, "获取题型")
        return self._rows(res)

    def questions_by_type(self, type_ids, start_num=1, end_num=500):
        """按题型取题目（练习接口，返回含 correctAnswer）。"""
        params = {"ids": ",".join(str(t) for t in type_ids),
                  "startNum": start_num, "endNum": end_num}
        res = self.api_get("/questions/queryListByType", params)
        self._check(res, "获取题库题目")
        return self._rows(res)

    def harvest_answer_bank(self):
        """从练习接口收集全部题目的正确答案 -> self.answer_bank。

        bank: qid -> "A"（或 "A,C" 多选）。收集后返回题目总数。
        """
        self.log("开始收集题库答案（练习接口）...")
        types = self.question_types()
        if not types:
            self.log("练习接口未返回题型，跳过答案收集。", "warn")
            return 0
        bank = {}
        total = 0
        for t in types:
            tid = t.get("id")
            if not tid:
                continue
            tname = t.get("name", tid)
            # 数量字段名做兼容探测
            cnt = t.get("count") or t.get("questionNum") or t.get("num") or 0
            try:
                cnt = int(cnt)
            except (TypeError, ValueError):
                cnt = 0
            # ids 可能是单个 id 的字符串/数字，也可能是逗号分隔列表
            got = self.questions_by_type([tid], 1, cnt if cnt else 500)
            for q in got:
                qid = q.get("id") or q.get("questionsId")
                ans = q.get("correctAnswer")
                if qid and ans:
                    bank[str(qid)] = self._norm_answer(ans)
                    total += 1
                    stem = (q.get("stem") or "").strip()
                    if stem:
                        self._stem_index.setdefault(stem, self._norm_answer(ans))
            self.log("  题型[%s] 收录 %d 题" % (tname, len(got)), "info")
        self.answer_bank.update(bank)
        self.log("题库答案收集完成：共 %d 题。" % len(bank), "success")
        return len(bank)

    @staticmethod
    def _norm_answer(ans):
        """把 correctAnswer 规范成 "A" 或 ["A","C"]；无法判定的原样保留。"""
        if isinstance(ans, list):
            return sorted(str(a).strip() for a in ans if str(a).strip())
        if isinstance(ans, (int, float)):
            return str(ans)
        s = str(ans or "").strip().upper()
        if not s:
            return ""
        # 多选 "A,B,C" / "A B C" -> ["A","C"] 列表
        parts = [p.strip() for p in s.replace("，", ",").replace(" ", ",").split(",") if p.strip()]
        if len(parts) > 1:
            return sorted(parts)
        # 单选/判断：单个字母原样；含标点或无逗号的多选组合也原样
        return s

    def lookup_answer(self, question):
        """查找一题的答案：先按 id 查库，再按题干匹配。找不到返回 None。"""
        qid = str(question.get("id") or question.get("questionsId") or "")
        if qid and qid in self.answer_bank:
            return self.answer_bank[qid]
        stem = (question.get("stem") or "").strip()
        if stem and stem in self._stem_index:
            return self._stem_index[stem]
        return None

    # ---------------- 考试 ----------------
    def my_exams(self):
        """我的考试列表。row 字段：id/examNo/examName/startTime/endTime/examTime/qualifiedScore/score。"""
        res = self.api_get("/jcedutec/exam/myExamList", {})
        self._check(res, "获取考试列表")
        return self._rows(res)

    def start_exam(self, exam_id, exam_type="1"):
        """开始考试。网页端固定传 type="1"（正式考试）。
        返回 {recordId, records:[题目...], examTime, startTime}。"""
        data = {"id": exam_id}
        if exam_type is not None:
            data["type"] = exam_type
        res = self.api_post("/jcedutec/exam/startExam", data)
        self._check(res, "开始考试")
        result = res.get("result") or {}
        return {
            "recordId": result.get("id"),
            "records": result.get("records") or result.get("questionList") or [],
            "examTime": result.get("examTime"),
            "startTime": result.get("startTime"),
        }

    def submit_exam(self, record_id, answers):
        """提交考试。answers: {questionId: "A" 或 ["A","C"]}。"""
        res = self.api_post("/jcedutec/exam/submitExam/%s" % record_id, answers)
        self._check(res, "提交考试")
        return res

    def exam_uncorrect(self, exam_id, exam_type=None):
        """考试错题（含 correctAnswer / analysis）。"""
        params = {"id": exam_id}
        if exam_type is not None:
            params["type"] = exam_type
        res = self.api_get("/jcedutec/exam/unCorrect", params)
        self._check(res, "获取考试错题")
        return self._rows(res)

    # ---------------- 个人信息 / 承诺书 ----------------
    def my_info(self):
        res = self.api_get("/students/queryMyInfo", {})
        self._check(res, "获取个人信息")
        return res.get("result") or {}

    def commitment_ready(self):
        """承诺书是否已上传。"""
        info = self.my_info()
        return bool((info.get("commitmentPath") or "").strip())

    def download_commitment(self, save_path=None):
        """下载实验室安全承诺书模板（doc），返回保存路径。"""
        import urllib.request as u
        url = self.base + "/sys/common/static/temp/commitment.doc"
        path = save_path or os.path.join(SCRIPT_DIR, "实验室安全承诺书.doc")
        req = u.Request(url, headers=self._headers(self.base))
        with u.urlopen(req, context=_SSL_CTX, timeout=20) as resp:
            data = resp.read()
        with open(path, "wb") as f:
            f.write(data)
        return path

    def upload_commitment(self, file_path, field="file"):
        """上传已签字的承诺书照片/扫描件并绑定到账号。

        两步：1) multipart 上传到 /sys/common/upload -> 得到 url；
              2) POST /students/updateMyInfo 写入 commitmentPath。
        """
        import mimetypes
        import uuid
        if not os.path.isfile(file_path):
            raise LabApiError("承诺书文件不存在: %s" % file_path)
        # ---- 1) 上传文件 ----
        boundary = "----DSH" + uuid.uuid4().hex
        with open(file_path, "rb") as f:
            file_data = f.read()
        fname = os.path.basename(file_path)
        ctype = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
        parts = []
        parts.append(("--%s\r\n" % boundary).encode("utf-8"))
        parts.append(('Content-Disposition: form-data; name="%s"; filename="%s"\r\n'
                      % (field, fname.replace('"', ""))).encode("utf-8"))
        parts.append(("Content-Type: %s\r\n\r\n" % ctype).encode("utf-8"))
        parts.append(file_data)
        parts.append(b"\r\n")
        parts.append(("--%s--\r\n" % boundary).encode("utf-8"))
        body = b"".join(parts)
        headers = self._headers(self.base)
        headers["Content-Type"] = "multipart/form-data; boundary=%s" % boundary
        req = urllib.request.Request(self.base + "/sys/common/upload", data=body,
                                     headers=headers, method="POST")
        with urllib.request.urlopen(req, context=_SSL_CTX, timeout=60) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
        try:
            up = json.loads(raw)
        except ValueError:
            raise LabApiError("承诺书上传接口返回异常: %s" % raw[:200])
        if not up.get("success"):
            raise LabApiError("上传承诺书失败: %s" % up.get("message", up))
        r = up.get("result") or {}
        path = r.get("path") or r.get("url")
        if not path:
            raise LabApiError("上传成功但未返回文件路径: %s" % str(r)[:200])
        self.log("  上传成功: %s" % path, "success")
        # ---- 2) 绑定到账号 ----
        res = self.api_post("/students/updateMyInfo", {"commitmentPath": path})
        self._check(res, "绑定承诺书")
        self.log("承诺书已绑定到账号。", "success")
        return True

    # ---------------- 自动刷课 ----------------
    def _target_seconds(self, detail, questions):
        """估算该课程需要上报的观看时长（秒）。

        优先取课程自带 duration 字段；否则用最后一题的 ejectTime 作为下限；
        再回退到默认 60 秒。
        """
        for key in ("duration", "watchDuration", "studyTime", "playTime", "videoDuration"):
            v = detail.get(key)
            try:
                v = float(v) if v not in (None, "", "null") else 0
            except (TypeError, ValueError):
                v = 0
            if v and v > 0:
                return max(int(v), 60)
        last = 0
        for q in questions:
            try:
                last = max(last, int(q.get("ejectTime") or 0))
            except (TypeError, ValueError):
                pass
        if last > 0:
            return last + 60
        return 60

    def _answer_for(self, question):
        """解析一题的答案，找不到返回 None。返回格式："A" 或 ["A","C"]。"""
        # 1) 题目自带正确答案（联调后若返回则直接用）
        raw = question.get("correctAnswer")
        if raw not in (None, ""):
            return self._norm_answer(raw)
        # 2) 题库 id 匹配
        qid = str(question.get("id") or question.get("questionsId") or "")
        if qid and qid in self.answer_bank:
            return self.answer_bank[qid]
        # 3) 题干匹配
        stem = (question.get("stem") or "").strip()
        if stem and stem in self._stem_index:
            return self._stem_index[stem]
        return None

    def learn_one_course(self, cid, course_name=""):
        """刷单个课程：上报进度 + 弹题作答 + 完成标记。"""
        name = course_name or cid
        self.log("")
        self.log("== 课程: %s (id=%s)" % (name, cid))
        self.update_visits(cid)
        try:
            detail = self.course_detail(cid)
            if detail:
                self.log("   名称: %s" % detail.get("name", ""), "info")
        except LabApiError as e:
            self.log("   详情获取失败: %s（继续刷课）" % e, "warn")
            detail = {}
        try:
            questions = self.course_questions(cid)
        except LabApiError as e:
            self.log("   题目获取失败: %s" % e, "warn")
            questions = []

        if questions:
            self.log("   嵌入式题目 %d 道" % len(questions), "info")
            for q in questions:
                ans = self._answer_for(q)
                qid = q.get("id")
                self.log("     [题 %s] %s" % (qid, (q.get("stem") or "")[:50]), "info")
                if ans is None:
                    self.log("       !! 题库中无该题答案，跳过作答（可事后补充）", "warn")
                    continue
                try:
                    r = self.submit_answer(cid, qid, ans)
                    if r.get("success"):
                        self.log("       [答对] 答案=%s" % (ans if isinstance(ans, str) else "".join(ans)), "success")
                    else:
                        self.log("       [作答失败] %s" % r.get("message", r), "error")
                except LabApiError as e:
                    self.log("       [作答异常] %s" % e, "error")

        target = self._target_seconds(detail, questions)
        self.log("   目标观看时长: %d 秒" % target, "info")
        if self.fast:
            r = self.report_finish_rate(cid, target)
            if not r.get("success"):
                self.log("   进度上报失败: %s" % r.get("message", r), "error")
        else:
            step = DEFAULT_REPORT_STEP
            cur = 0
            while cur < target:
                cur = min(target, cur + step)
                try:
                    r = self.report_finish_rate(cid, cur)
                    if not r.get("success"):
                        self.log("   进度上报失败(%ss): %s" % (cur, r.get("message", r)), "warn")
                except LabApiError as e:
                    self.log("   进度上报异常(%ss): %s" % (cur, e), "error")
                time.sleep(0.2)
        try:
            r = self.finish_course(cid)
            if r.get("success"):
                self.log("   [完成] 课程已标记完成", "success")
                return True
            self.log("   完成标记失败: %s" % r.get("message", r), "error")
            return False
        except LabApiError as e:
            self.log("   完成标记异常: %s" % e, "error")
            return False

    def learn_all(self, fast=False):
        """遍历我的课程全部刷完。返回 (完成数, 总数, 未完成列表)。"""
        self.fast = fast
        self.log("=" * 60)
        courses = self.my_courses()
        if not courses:
            self.log("我的课程列表为空（可能 token 无效或未绑定课程）。", "warn")
            return 0, 0, []
        unfinished = [c for c in courses
                      if str(c.get("isFinish")) not in ("1", "true", "True")]
        self.log("共 %d 门课程，未完成 %d 门" % (len(courses), len(unfinished)))
        done = 0
        failed = []
        for idx, c in enumerate(unfinished, 1):
            self.log("")
            self.log("[%d/%d]" % (idx, len(unfinished)))
            try:
                ok = self.learn_one_course(c.get("id"), c.get("name"))
            except Exception as e:  # noqa: BLE001 - 单课失败不中断整体
                self.log("  [异常] 该课处理失败: %s" % e, "error")
                ok = False
            if ok:
                done += 1
            else:
                failed.append(c.get("name"))
            if self.interval_between and self.interval_between > 0 and idx < len(unfinished):
                time.sleep(self.interval_between)
        self.log("")
        self.log("=" * 60)
        self.log("刷课完成：%d / %d 门（其余为已完成课程）" % (done, len(unfinished)), "success")
        if failed:
            self.log("失败课程: %s" % ", ".join(str(x) for x in failed), "warn")
        return done, len(unfinished), failed

    # ---------------- 自动考试 ----------------
    def run_exam(self, exam_id=None, exam_type="1"):
        """自动完成一场考试。返回结果字典。"""
        if not self.commitment_ready():
            raise LabApiError(
                "请先在【实验室安全】页下载并上传已签字的《实验室安全承诺书》，"
                "之后才能开始考试。")
        eid = exam_id
        if not eid:
            exams = self.my_exams()
            if not exams:
                return {"submitted": False, "reason": "无可参加的考试"}
            eid = exams[0].get("id")
            self.log("未指定考试 ID，自动选择第一场: %s" % exams[0].get("examName", eid))
        self.log("开始自动考试 (examId=%s)" % eid)
        st = self.start_exam(eid, exam_type)
        records = st["records"]
        self.log("考试记录 id=%s，题目 %d 道" % (st["recordId"], len(records)))
        if not st["recordId"] or not records:
            return {"submitted": False, "reason": "考试无可提交记录/题目"}

        answers = {}
        missing = []
        for q in records:
            ans = self._answer_for(q)
            qid = q.get("id") or q.get("questionsId")
            if ans is None:
                missing.append(q)
                continue
            answers[str(qid)] = ans
            self.log("  [%s] %s -> %s" % (qid, (q.get("stem") or "")[:40],
                                           ans if isinstance(ans, str) else "".join(ans)))
        if missing:
            self.log("")
            self.log("[!] %d 道题不在题库内，为避免答错丢分，本次【不提交】：" % len(missing), "warn")
            for q in missing:
                self.log("   【%s】%s" % (q.get("kind"), q.get("stem")), "warn")
            return {"submitted": False, "filled": len(answers), "total": len(records),
                    "unanswered": missing}
        resp = self.submit_exam(st["recordId"], answers)
        self.log("提交完成：已答 %d / %d 题" % (len(answers), len(records)), "success")
        return {"submitted": True, "filled": len(answers), "total": len(records),
                "response": resp}

    def run_all_exams(self, exam_type="1"):
        """把我已有的考试全部提交一遍。返回 (成功数, 总数)。"""
        if not self.commitment_ready():
            raise LabApiError(
                "请先下载并上传已签字的《实验室安全承诺书》，之后才能开始考试。")
        exams = self.my_exams()
        if not exams:
            self.log("没有可参加的考试。", "warn")
            return 0, 0
        ok = 0
        for i, ex in enumerate(exams, 1):
            self.log("")
            self.log("[考试 %d/%d] %s (合格分 %s)" % (i, len(exams),
                                                     ex.get("examName"), ex.get("qualifiedScore")))
            try:
                r = self.run_exam(ex.get("id"), exam_type)
                if r.get("submitted"):
                    ok += 1
            except LabApiError as e:
                self.log("  考试失败: %s" % e, "error")
        self.log("考试处理完成：成功 %d / %d" % (ok, len(exams)), "success")
        return ok, len(exams)


def load_config():
    return LabApi.load_config()


if __name__ == "__main__":
    # 只做单元测试验证，见 e2e_lab_test.py
    print("njupt_lab_api loaded OK")