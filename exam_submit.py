# -*- coding: utf-8 -*-
"""提交考试答案：POST /exam/app/examDetail/saverecords。

答案按 questionsId 映射；单选=字符串，多选=数组。提交 body 为 loadExamDetailList 的 result。

⚠️  若试卷中存在脚本题库(ANSWERS)里没有的题目，会列出该题目详情并提示无法解答，
    同时【中止提交】（避免答错丢分）。此时建议用 AI agent（如 Claude Code / DSH / Codex）
    自行搜索答案，再补充到 ANSWERS 字典 / exam_questions.json 后重跑。
"""
import json
import ssl
import sys
import os
import urllib.parse
import urllib.request
import urllib.error

API = "https://study.njupt.edu.cn/service-api"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def load_cfg():
    """优先读取脚本同目录 config.json；否则回退到环境变量。"""
    cfg_path = os.path.join(SCRIPT_DIR, "config.json")
    if os.path.exists(cfg_path):
        try:
            with open(cfg_path, encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print("[warn] 读取 config.json 失败:", e)
    return {
        "token": os.environ.get("NJUPT_TOKEN", ""),
        "tenant_id": os.environ.get("NJUPT_TENANT", "0"),
    }


cfg = load_cfg()
token = (cfg.get("token") or "").strip()
if not token:
    print("[!] 未提供 Access-Token。请在脚本同目录 config.json 的 token 字段填写，或用环境变量 NJUPT_TOKEN。")
    sys.exit(2)

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
H = {"X-Access-Token": token, "tenant_id": cfg.get("tenant_id", "0"),
     "User-Agent": "Mozilla/5.0", "Accept": "application/json"}


def get(path, params):
    url = API + path + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=H, method="GET")
    with urllib.request.urlopen(req, context=ctx, timeout=20) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def post(path, data):
    url = API + path
    body = json.dumps(data, ensure_ascii=False).encode("utf-8")
    hh = dict(H)
    hh["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=hh, method="POST")
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=25) as r:
            return json.loads(r.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        return {"_http": e.code, "_body": e.read().decode("utf-8", "replace")[:500]}


# 答案映射（questionsId -> 答案）。题库外的题会在下方被识别并提示，不会强行作答。
ANSWERS = {
    "2077977470535077890": "C",         # 1 班级群缴费
    "2077977470539272200": "B",         # 2 航班改签
    "2077977470539272197": "D",         # 3 投资导师
    "2077977470539272198": "C",         # 4 培训机构退费
    "2077977470535077888": "D",         # 5 游戏账号交易
    "2077977470539272199": "C",         # 6 助学金ATM
    "2077977470539272192": "D",         # 7 订单异常退款
    "2077977470535077889": "C",         # 8 好友QQ借钱
    "2077977470539272202": "D",         # 9 偷窥法律后果
    "2077977470539272193": "C",         # 10 兼职刷单
    "2077977470539272194": "C",         # 11 朋友圈刷单
    "2077977470539272201": "B",         # 12 贷款解冻费
    "2077977470539272195": "B",         # 13 刷单违法
    "2077977470539272203": "C",         # 14 冒充公安
    "2077977470539272196": "B",         # 15 内部票
    "2077977470543466499": ["A", "C"],           # 16 论文代写
    "2077977470543466496": ["A", "B", "C", "D"], # 17 裸聊敲诈
    "2077977470543466502": ["A", "B", "D"],      # 18 校园交通事故
    "2077977470543466498": ["A", "C", "D"],      # 19 二手交易
    "2077977470543466497": ["A", "C", "D"],      # 20 快递理赔(问"错误的有")
    "2077977470539272206": ["A", "B", "C"],      # 21 招聘诈骗
    "2077977470543466500": ["A", "B", "C", "D"], # 22 电诈工具人
    "2077977470543466501": ["A", "B", "D"],      # 23 笑气
    "2077977470539272205": ["A", "B", "C", "D"], # 24 网购诈骗
    "2077977470539272204": ["A", "B", "C", "D"], # 25 游戏虚假交易
}

# 考试 ID：如课程不同，请改为对应课程的 examId（也可从 /app/study/course/info 的 examId 字段自动获取）。
exam_id = "2078031452989038593"

res = get("/exam/app/examDetail/loadExamDetailList", {"examId": exam_id})
result = res["result"]
print("erId=", result.get("erId"), "| status=", result.get("status"))
ql = result["questionList"]
print("题目总数:", len(ql))

filled = 0
unanswered = []
for q in ql:
    qid = q.get("questionsId")
    if qid in ANSWERS:
        q["userAnswer"] = ANSWERS[qid]
        filled += 1
    else:
        unanswered.append(q)

print("已填答案题数: %d / %d" % (filled, len(ql)))

if unanswered:
    print("\n" + "=" * 60)
    print("[!] 有 %d 道题【不在脚本题库内】，无法自动作答：" % len(unanswered))
    for i, q in enumerate(unanswered, 1):
        t = q.get("type")
        label = "多选" if str(t) == "2" else ("单选" if str(t) == "1" else "题型%s" % t)
        opts = " | ".join("%s.%s" % (o["optionAlias"], o["optionDesc"]) for o in q.get("optionsList") or [])
        print("\n  【%d】【%s】 %s" % (i, label, q.get("title")))
        print("   选项: %s" % opts)
        print("   questionsId: %s" % q.get("questionsId"))
    print("\n[提示] 以上题目不在脚本题库内，为避免答错丢分，本次【不提交】。")
    print("      建议使用 AI agent（如 Claude Code / DSH / Codex 等）自行搜索这些题的答案，")
    print("      然后把答案补充到本脚本的 ANSWERS 字典，或更新同目录 exam_questions.json 后重跑。")
    sys.exit(2)

print("\n全部题目均在题库内，开始提交...")
resp = post("/exam/app/examDetail/saverecords", result)
print("\n提交响应:", json.dumps(resp, ensure_ascii=False)[:600])
