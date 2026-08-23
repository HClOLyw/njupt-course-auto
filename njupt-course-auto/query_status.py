# -*- coding: utf-8 -*-
"""查询当前所有知识点进度，揭示 finishBfb/finishHour 累计机制。"""
import json, ssl, urllib.parse, urllib.request

API = "https://study.njupt.edu.cn/service-api"
cfg = json.load(open(r"D:\part time cx\jiangsu-safety-platform-skip\config.json", encoding="utf-8"))
token = (cfg.get("token") or "").strip(); course_id = cfg.get("course_id")
ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
url = API + "/app/study/course/info?" + urllib.parse.urlencode({"id": course_id})
req = urllib.request.Request(url, headers={
    "X-Access-Token": token, "tenant_id": cfg.get("tenant_id", "0"),
    "User-Agent": "Mozilla/5.0", "Accept": "application/json"})
with urllib.request.urlopen(req, context=ctx, timeout=20) as r:
    res = json.loads(r.read().decode("utf-8", "replace"))
course = res["result"]
print("课程:", course.get("name"), "| 完成度字段: finishBfb / finishHour / knowHour")
done = 0; total = 0
for sec in course["sectionList"]:
    for kn in sec.get("knowList") or []:
        total += 1
        fs = kn.get("finishStatus"); fb = kn.get("finishBfb"); fh = kn.get("finishHour"); kh = kn.get("knowHour")
        if fs == 1:
            done += 1
            flag = "[完成]"
        else:
            flag = "[未完成]"
        print("%s %-28s finishStatus=%s finishBfb=%-6s finishHour=%-8s knowHour=%s" % (
            flag, (kn.get("knowName") or "")[:24], fs, fb, fh, kh))
print("\n完成 %d/%d" % (done, total))
