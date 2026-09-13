# -*- coding: utf-8 -*-
"""
probe_lab.py —— 实验室平台联调探针
==================================
用真实 token 探查各接口返回的实际 JSON 结构，用于校准 njupt_lab_api.py
中的字段名与请求参数（不提交任何会消耗考试次数的请求，除非 --start-exam）。

用法：
    python probe_lab.py --token <你的Access-Token>
    # 或从 config.json 的 lab_token 读取（建议先保存配置）
    python probe_lab.py
    # 额外探查"开始考试"接口（会消耗一次今日考试次数，谨慎）：
    python probe_lab.py --start-exam
"""
import argparse
import io
import json
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from njupt_lab_api import LabApi, LabApiError  # noqa: E402


def dump(title, data, max_len=800):
    print("")
    print("=" * 70)
    print(title)
    print("=" * 70)
    s = json.dumps(data, ensure_ascii=False, indent=1)
    if len(s) > max_len:
        print(s[:max_len])
        print("... [截断，共 %d 字符]" % len(s))
    else:
        print(s)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--token", default=None, help="Access-Token；缺省读 config.json 的 lab_token")
    ap.add_argument("--base", default=None, help="后端 API 基址，缺省 http://10.22.192.38:9090/jeecg-boot")
    ap.add_argument("--start-exam", action="store_true",
                    help="调用 startExam 接口（会消耗一次今日考试次数）")
    args = ap.parse_args()

    cfg = LabApi.load_config()
    token = args.token or cfg.get("lab_token", "")
    base = args.base or cfg.get("lab_base") or None
    if not token:
        print("!! 未提供 token。请用 --token 传参，或先在【参数设置】保存 lab_token。")
        sys.exit(2)

    api = LabApi(token=token, base=base)
    api.log = lambda msg, level="info": print("[%s] %s" % (level, msg))

    # 1) 课程列表（只取前 3 行，含原始 JSON）
    print("## 1. 我的课程列表")
    try:
        courses = api.my_courses()
        print("共 %d 门" % len(courses))
        for c in courses[:3]:
            dump("row", c)
    except (LabApiError, Exception) as e:  # noqa: BLE001
        print("!! my_courses 失败: %s" % e)
        courses = []

    # 2) 课程详情 + 嵌入式题目
    if courses:
        cid = courses[0].get("id")
        print("## 2. 第一门课详情 id=%s" % cid)
        try:
            dump("course_detail", api.course_detail(cid))
        except Exception as e:  # noqa: BLE001
            print("!! course_detail 失败: %s" % e)
        print("## 3. 嵌入式题目")
        try:
            dump("course_questions", api.course_questions(cid))
        except Exception as e:  # noqa: BLE001
            print("!! course_questions 失败: %s" % e)

    # 4) 题型
    print("## 4. 题型列表")
    try:
        types = api.question_types()
        dump("question_types", types)
    except Exception as e:  # noqa: BLE001
        print("!! question_types 失败: %s" % e)
        types = []

    # 5) 练习题目（含正确答案）
    if types:
        tid = types[0].get("id")
        print("## 5. 第一题型题目（含 correctAnswer）")
        try:
            qs = api.questions_by_type([tid], 1, 5)
            dump("questions_by_type", qs[:2] if qs else qs)
        except Exception as e:  # noqa: BLE001
            print("!! questions_by_type 失败: %s" % e)

    # 6) 错题（课程）
    if courses:
        print("## 6. 课程错题（含 correctAnswer）")
        try:
            dump("uncorrect_by_course", api.uncorrect_by_course(courses[0].get("id")))
        except Exception as e:  # noqa: BLE001
            print("!! uncorrect_by_course 失败: %s" % e)

    # 7) 考试列表
    print("## 7. 我的考试列表")
    try:
        exams = api.my_exams()
        dump("my_exams", exams[:3] if exams else exams)
    except Exception as e:  # noqa: BLE001
        print("!! my_exams 失败: %s" % e)
        exams = []

    # 8) 开始考试（默认不调用）
    if args.start_exam and exams:
        print("## 8. 开始考试（消耗一次次数）")
        try:
            st = api.start_exam(exams[0].get("id"))
            dump("start_exam", {k: (v if k != "records" else v[:2]) for k, v in st.items()})
            dump("question0", st["records"][0])
        except Exception as e:  # noqa: BLE001
            print("!! start_exam 失败: %s" % e)

    # 9) 个人信息
    print("## 9. 个人信息")
    try:
        dump("my_info", api.my_info())
    except Exception as e:  # noqa: BLE001
        print("!! my_info 失败: %s" % e)

    print("")
    print("探针完成。请把以上输出发给开发者以校准字段。")


if __name__ == "__main__":
    main()