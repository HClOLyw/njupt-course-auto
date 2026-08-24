# -*- coding: utf-8 -*-
"""测试：course_id/exam_id 留空时自动使用默认安全教育课。"""
import sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
import njupt_api
from njupt_api import NJUPTApi, DEFAULT_COURSE_ID, DEFAULT_EXAM_ID

calls = []
class _FR:
    def __init__(s, d):
        s._d = json.dumps(d, ensure_ascii=False).encode("utf-8")
    def __enter__(s): return s
    def __exit__(s, *a): return False
    def read(s): return s._d

def fake_urlopen(req, context=None, timeout=None):
    calls.append(req.full_url)
    if "course/info" in req.full_url:
        return _FR({"success": True, "result": {
            "name": "安全教育课",
            "sectionList": [{"id": "S1", "name": "章节", "knowList": []}]}})
    if "course/start" in req.full_url:
        return _FR({"success": True})
    return _FR({"success": True, "result": {"erId": "E", "status": 0, "questionList": []}})

njupt_api.urllib.request.urlopen = fake_urlopen

checks = []
def check(name, cond): checks.append((name, bool(cond)))

api = NJUPTApi(token="T", course_id="")
check("构造函数course_id回退默认", api.course_id == DEFAULT_COURSE_ID)
check("模块级默认考试ID", DEFAULT_EXAM_ID == "2078031452989038593")

done, total = api.learn_course()
check("刷课使用默认课程ID", any("id=" + DEFAULT_COURSE_ID in u for u in calls))

calls.clear()
ret = api.run_exam()
check("考试使用默认examId", any("examId=" + DEFAULT_EXAM_ID in u for u in calls))

ok = all(c for _, c in checks)
print("=" * 40)
for n, c in checks:
    print(("PASS " if c else "FAIL ") + n)
print("=" * 40)
print("ALL PASS" if ok else "SOME FAILED")
sys.exit(0 if ok else 1)
