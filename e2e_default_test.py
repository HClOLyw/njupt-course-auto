# -*- coding: utf-8 -*-
"""测试：课程/考试 ID 留空时的自动行为。"""
import sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
import njupt_api
from njupt_api import NJUPTApi, DEFAULT_COURSE_ID, DEFAULT_EXAM_ID

class _FR:
    def __init__(s, d):
        s._d = json.dumps(d, ensure_ascii=False).encode("utf-8")
    def __enter__(s): return s
    def __exit__(s, *a): return False
    def read(s): return s._d

checks = []
def check(name, cond): checks.append((name, bool(cond)))

# ---------- 场景1：课程信息含 examId，考试自动使用该 ID ----------
calls = []
def fake1(req, context=None, timeout=None):
    calls.append(req.full_url)
    if "course/info" in req.full_url:
        return _FR({"success": True, "result": {
            "name": "安全教育课", "examId": "EXAM_FROM_COURSE",
            "sectionList": []}})
    if "loadExamDetailList" in req.full_url:
        return _FR({"success": True, "result": {
            "erId": "E", "status": 0, "questionList": []}})
    return _FR({"success": True})

njupt_api.urllib.request.urlopen = fake1
api = NJUPTApi(token="T", course_id="")
api.run_exam(None)
check("考试自动使用课程examId", any("examId=EXAM_FROM_COURSE" in u for u in calls))

# ---------- 场景2：课程无 examId，回退默认考试 ----------
calls.clear()
def fake2(req, context=None, timeout=None):
    calls.append(req.full_url)
    if "course/info" in req.full_url:
        return _FR({"success": True, "result": {
            "name": "安全教育课", "sectionList": []}})
    if "loadExamDetailList" in req.full_url:
        return _FR({"success": True, "result": {
            "erId": "E", "status": 0, "questionList": []}})
    return _FR({"success": True})

njupt_api.urllib.request.urlopen = fake2
api.run_exam(None)
check("无examId回退默认考试", any("examId=" + DEFAULT_EXAM_ID in u for u in calls))

# ---------- 场景3：课程 ID 留空回退默认 ----------
api2 = NJUPTApi(token="T", course_id="")
check("课程ID留空回退默认", api2.course_id == DEFAULT_COURSE_ID)

ok = all(c for _, c in checks)
print("=" * 40)
for n, c in checks:
    print(("PASS " if c else "FAIL ") + n)
print("=" * 40)
print("ALL PASS" if ok else "SOME FAILED")
sys.exit(0 if ok else 1)
