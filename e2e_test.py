# -*- coding: utf-8 -*-
"""端到端逻辑测试：mock HTTP 层，验证刷课/查进度/考试三大功能。"""
import sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import njupt_api
from njupt_api import NJUPTApi

log = []
api = NJUPTApi(token="fake-token", course_id="C1", interval_between=0,
               log_callback=lambda lv, tx: log.append((lv, tx)))

mock_responses = {}
request_calls = []

class FakeResp:
    def __init__(self, data):
        self._d = json.dumps(data, ensure_ascii=False).encode("utf-8")
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def read(self): return self._d

def fake_urlopen(req, context=None, timeout=None):
    url = req.full_url
    data = None
    if req.data:
        data = json.loads(req.data.decode("utf-8"))
    request_calls.append((req.get_method(), url, data))
    for prefix, resp in mock_responses.items():
        if prefix in url:
            return FakeResp(resp)
    return FakeResp({"success": True})

njupt_api.urllib.request.urlopen = fake_urlopen

course = {
    "success": True,
    "result": {
        "name": "测试课程",
        "courseSource": "NJUPT",
        "courseType": "TRAIN",
        "learnStatus": 0,
        "sectionList": [
            {"id": "S1", "name": "章节一",
             "knowList": [
                 {"id": "K1", "knowName": "视频1", "knowType": "1",
                  "knowHour": 120, "courseId": "C1", "courseSectionId": "S1", "finishStatus": 0},
                 {"id": "K2", "knowName": "PDF1", "knowType": "2",
                  "knowHour": 90, "pageTotal": 5, "courseId": "C1",
                  "courseSectionId": "S1", "finishStatus": 0},
                 {"id": "K3", "knowName": "已完成", "knowType": "1",
                  "knowHour": 60, "courseId": "C1", "courseSectionId": "S1", "finishStatus": 1},
             ]}
        ]
    }
}
mock_responses["/app/study/course/info"] = course
mock_responses["/app/study/my/course/start"] = {"success": True}

checks = []
def check(name, cond):
    checks.append((name, bool(cond)))

summary, rows = api.query_status()
check("查进度-课程名", summary["name"] == "测试课程")
check("查进度-总数", summary["total"] == 3)
check("查进度-完成数", summary["done"] == 1)
check("查进度-未完成行", any(r["fs"] == 0 for r in rows))

done, total = api.learn_course("C1")
# K1,K2 成功 + K3 已跳过 -> done=3
check("刷课-成功数(含跳过)", done == 3, )
check("刷课-总数", total == 3)
starts = [c for c in request_calls if "course/start" in c[1]]
check("刷课-发送上报", len(starts) >= 4)
check("刷课-上报含参数", all(isinstance(c[2], dict) for c in starts))
# 最后一条应为 end=1
if starts:
    check("刷课-最终end=1", starts[-1][2].get("end") == 1)

request_calls.clear()
exam_id = api.DEFAULT_EXAM_ID
q1 = {"questionsId": "2077977470535077890", "type": "1", "title": "班级群缴费",
      "optionsList": [{"optionAlias": "A", "optionDesc": "a"},{"optionAlias":"B","optionDesc":"b"},
                       {"optionAlias":"C","optionDesc":"c"},{"optionAlias":"D","optionDesc":"d"}]}
q2 = {"questionsId": "2077977470543466499", "type": "2", "title": "论文代写",
      "optionsList": [{"optionAlias": "A", "optionDesc": "a"},{"optionAlias":"B","optionDesc":"b"},
                       {"optionAlias":"C","optionDesc":"c"}]}
msg = {"success": True, "result": {"erId": "ER1", "status": 0, "questionList": [q1, q2]}}
mock_responses["/exam/app/examDetail/loadExamDetailList"] = msg
mock_responses["/exam/app/examDetail/saverecords"] = {"success": True}
res = api.run_exam(exam_id)
check("考试-提交成功", res["submitted"] is True)
check("考试-填充2题", res["filled"] == 2)
submit_calls = [c for c in request_calls if "saverecords" in c[1]]
check("考试-发送提交", len(submit_calls) == 1)
if submit_calls:
    body = submit_calls[0][2]
    check("考试-单选答案C", body["questionList"][0]["userAnswer"] == "C")
    check("考试-多选答案[A,C]", body["questionList"][1]["userAnswer"] == ["A","C"])

request_calls.clear()
q3 = {"questionsId": "UNKNOWN_QID", "type": "1", "title": "新问题",
      "optionsList": [{"optionAlias": "A", "optionDesc": "a"}]}
msg2 = {"success": True, "result": {"erId": "ER2", "status": 0, "questionList": [q1, q3]}}
mock_responses["/exam/app/examDetail/loadExamDetailList"] = msg2
res2 = api.run_exam(exam_id)
check("考试-题库外中止", res2["submitted"] is False)
check("考试-提示未答1题", len(res2.get("unanswered", [])) == 1)
submit_calls2 = [c for c in request_calls if "saverecords" in c[1]]
check("考试-题库外不提交", len(submit_calls2) == 0)

import os
cfg = {"token": "T", "tenant_id": "0", "course_id": "C1",
       "interval_between": 6, "exam_id": "E1"}
tmp = njupt_api.CONFIG_PATH
try:
    njupt_api.CONFIG_PATH = os.path.join(os.path.dirname(__file__), "_cfg_test.json")
    NJUPTApi.save_config(cfg)
    loaded = NJUPTApi.load_config()
    check("配置读写", loaded.get("course_id") == "C1")
finally:
    try: os.remove(os.path.join(os.path.dirname(__file__), "_cfg_test.json"))
    except: pass
    njupt_api.CONFIG_PATH = tmp

ok = all(c for _, c in checks)
print("="*46)
for name, c in checks:
    print(("PASS " if c else "FAIL ") + name)
print("="*46)
print("ALL PASS" if ok else "SOME FAILED")
sys.exit(0 if ok else 1)
