# -*- coding: utf-8 -*-
"""实验室平台核心逻辑端到端测试：mock HTTP 层，验证刷课 / 题库收集 / 考试。"""
import sys, io, json, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
import njupt_lab_api
from njupt_lab_api import LabApi

log = []
api = LabApi(token="fake-token", interval_between=0,
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
        try:
            data = json.loads(req.data.decode("utf-8"))
        except Exception:
            data = "<binary %d bytes>" % len(req.data)
    request_calls.append((req.get_method(), url, data))
    for prefix, resp in mock_responses.items():
        if prefix in url:
            return FakeResp(resp)
    return FakeResp({"success": True})


njupt_lab_api.urllib.request.urlopen = fake_urlopen

checks = []
def check(name, cond):
    checks.append((name, bool(cond)))


def courses_resp():
    return {"success": True, "result": {"records": [
        {"id": "C1", "name": "危化品安全", "watchDuration": 30, "donum": 1, "total": 2,
         "unCorrectNum": 0, "isFinish": 0},
        {"id": "C2", "name": "用电安全", "watchDuration": 100, "donum": 2, "total": 2,
         "unCorrectNum": 0, "isFinish": 1},
    ]}}


mock_responses["/jcedutec/courseSource/myCourseList"] = courses_resp()
mock_responses["/students/queryMyInfo"] = {"success": True, "result": {
    "name": "测试", "commitmentPath": "temp/commitment.jpg"}}
mock_responses["/jcedutec/courseSource/queryById"] = {"success": True, "result": {
    "id": "C1", "name": "危化品安全", "url": "video/c1.mp4", "remark": "简介", "duration": 120}}
mock_responses["/jcedutec/courseSource/queryCourseQuestionRelaByMainId"] = {
    "success": True, "result": [
        {"id": "Q1", "stem": "浓硫酸稀释时应该？", "kind": "2", "optiona": "A1", "optionb": "B1",
         "optionc": "C1", "optiond": "D1", "ejectTime": 20},
        {"id": "Q2", "stem": "灭火器使用步骤（多选）", "kind": "3", "optiona": "A2", "optionb": "B2",
         "optionc": "C2", "optiond": "D2", "ejectTime": 40},
    ]}
mock_responses["/jcedutec/courseSource/updateVisits"] = {"success": True}
mock_responses["/jcedutec/courseSource/finishRate"] = {"success": True}
mock_responses["/jcedutec/courseSource/submitAnswer"] = {"success": True}
mock_responses["/jcedutec/courseSource/finish"] = {"success": True}
mock_responses["/jcedutec/questionType/queryCountList"] = {"success": True, "result": [
    {"id": 1, "name": "单选", "count": 2},
    {"id": 3, "name": "多选", "count": 1},
]}
mock_responses["/questions/queryListByType"] = {"success": True, "result": [
    {"id": "Q1", "stem": "浓硫酸稀释时应该？", "kind": "2", "correctAnswer": "C"},
    {"id": "Q2", "stem": "灭火器使用步骤（多选）", "kind": "3", "correctAnswer": "A,B,C"},
    {"id": "Q3", "stem": "实验室通风", "kind": "1", "correctAnswer": "对"},
]}

# ---------- 1. 题库答案收集 ----------
n = api.harvest_answer_bank()
check("收集答案-数量", len(api.answer_bank) == 3)
check("收集答案-单选C", api.answer_bank.get("Q1") == "C")
check("收集答案-多选列表", api.answer_bank.get("Q2") == ["A", "B", "C"])
check("题干索引", api._stem_index.get("实验室通风") == "对")

# ---------- 2. 刷课（learn_all 应只刷未完成 C1） ----------
done, total, failed = api.learn_all()
check("刷课-只刷未完成1门", total == 1)
check("刷课-完成数", done == 1)
check("刷课-无失败", len(failed) == 0)

starts = [c for c in request_calls if "finishRate" in c[1]]
check("刷课-上报进度多次", len(starts) >= 5)
check("刷课-上报含id和时长", all(isinstance(c[2], dict) and c[2].get("id") == "C1" for c in starts))
finish_calls = [c for c in request_calls if "courseSource/finish" in c[1] and "finishRate" not in c[1]]
check("刷课-调用finish", len(finish_calls) == 1)

answers = [c for c in request_calls if "submitAnswer" in c[1]]
check("弹题-答2题", len(answers) == 2)
ans0 = answers[0][2]
ans1 = answers[1][2]
check("弹题-单选答C", ans0["option"] == "C" and ans0["questionId"] == "Q1")
check("弹题-多选答案", sorted(ans1["option"]) == ["A", "B", "C"])

# ---------- 3. 自动考试 ----------
request_calls.clear()
mock_responses["/jcedutec/exam/myExamList"] = {"success": True, "result": {"records": [
    {"id": "E1", "examName": "实验室安全考试", "qualifiedScore": "90", "score": 0}]}}
mock_responses["/jcedutec/exam/startExam"] = {"success": True, "result": {
    "id": "R1", "examTime": 30, "startTime": "2026-01-01 00:00:00",
    "records": [
        {"id": "Q1", "kind": "2", "stem": "浓硫酸稀释时应该？", "optiona": "A", "optionb": "B",
         "optionc": "C", "optiond": "D"},
        {"id": "Q2", "kind": "3", "stem": "灭火器使用步骤（多选）", "optiona": "A", "optionb": "B",
         "optionc": "C", "optiond": "D"},
    ]}}
mock_responses["/jcedutec/exam/submitExam/R1"] = {"success": True}
res = api.run_exam("E1")
check("考试-提交成功", res["submitted"] is True)
check("考试-填2题", res["filled"] == 2)
sub = [c for c in request_calls if "submitExam" in c[1]]
check("考试-发送提交", len(sub) == 1)
if sub:
    check("考试-单选C", sub[0][2].get("Q1") == "C")
    check("考试-多选列表", sorted(sub[0][2].get("Q2")) == ["A", "B", "C"])

# ---------- 4. 题库外题目中止 ----------
request_calls.clear()
mock_responses["/jcedutec/exam/startExam"] = {"success": True, "result": {
    "id": "R2", "examTime": 30,
    "records": [
        {"id": "QX", "kind": "2", "stem": "未知题目", "optiona": "A", "optionb": "B"},
    ]}}
res2 = api.run_exam("E1")
check("考试-未知名题中止", res2["submitted"] is False and len(res2["unanswered"]) == 1)
sub2 = [c for c in request_calls if "submitExam" in c[1]]
check("考试-未知名题不提交", len(sub2) == 0)

# ---------- 5. 配置读写 ----------
tmp = njupt_lab_api.CONFIG_PATH
try:
    njupt_lab_api.CONFIG_PATH = os.path.join(os.path.dirname(__file__), "_cfg_lab_test.json")
    LabApi.save_config({"token": "T", "lab_token": "LT", "lab_base": "http://x", "interval_between": 6})
    loaded = LabApi.load_config()
    check("配置读写-lab_token", loaded.get("lab_token") == "LT")
finally:
    p = os.path.join(os.path.dirname(__file__), "_cfg_lab_test.json")
    if os.path.exists(p):
        os.remove(p)
    njupt_lab_api.CONFIG_PATH = tmp

# ---------- 6. 缺 token 报错 ----------
api2 = LabApi(token="")
try:
    api2.my_courses()
    check("缺token应报错", False)
except njupt_lab_api.LabApiError:
    check("缺token应报错", True)

# ---------- 7. 承诺书流程 ----------
mock_responses["/sys/common/upload"] = {"success": True, "result": {"path": "temp/signed.jpg"}}
mock_responses["/students/updateMyInfo"] = {"success": True}
import tempfile
tmpf = os.path.join(tempfile.gettempdir(), "_commit_test.jpg")
with open(tmpf, "wb") as f:
    f.write(b"\xff\xd8fakejpg")
ok_up = api.upload_commitment(tmpf)
check("承诺书-上传成功", ok_up is True)
up_calls = [c for c in request_calls if "sys/common/upload" in c[1]]
check("承诺书-multipart上传", len(up_calls) == 1 and up_calls[0][0] == "POST")
info_calls = [c for c in request_calls if "updateMyInfo" in c[1]]
check("承诺书-绑定commitmentPath", len(info_calls) == 1 and info_calls[0][2].get("commitmentPath") == "temp/signed.jpg")
os.remove(tmpf)

# ---------- 8. 无承诺书时禁止考试 ----------
mock_responses["/students/queryMyInfo"] = {"success": True, "result": {"name": "测试", "commitmentPath": None}}
api3 = LabApi(token="T", interval_between=0)
try:
    api3.run_exam("E1")
    check("无承诺书禁止考试", False)
except njupt_lab_api.LabApiError as e:
    check("无承诺书禁止考试", "承诺书" in str(e))
mock_responses["/students/queryMyInfo"] = {"success": True, "result": {
    "name": "测试", "commitmentPath": "temp/commitment.jpg"}}

ok = all(c for _, c in checks)
print("=" * 46)
for name, c in checks:
    print(("PASS " if c else "FAIL ") + name)
print("=" * 46)
print("ALL PASS" if ok else "SOME FAILED")
sys.exit(0 if ok else 1)