# 南邮新生安全教育自动化脚本

本仓库包含一套针对 **南京邮电大学在线培训平台**（`https://study.njupt.edu.cn`）
的自动化脚本：自动刷完课程的 **视频 / PDF 学习进度**，并自动作答课程的 **在线考试**。

> ⚠️ **仅供本人账号自主学习 / 补课使用。**
> 脚本通过调用平台真实接口模拟学习与答题，属于绕过平台"防挂机 / 防作弊"限制的行为，
> 可能被平台判定为异常，存在账号风险。请自行评估，切勿用于批量处理他人账号或违反学校规定。
> 本项目仅用于技术学习与交流，作者不承担任何因使用不当导致的后果。

---

## 特性

- **仅依赖 Python 标准库**，无需 pip 安装任何第三方包。
- **自动刷课**：遍历课程全部知识点，模拟"完整观看视频 / 阅读 PDF"，逐个完成到 `100%`。
- **自动考试**：读取试卷、逐题作答并提交，已实测 **满分 100 / 100**（合格线 90）。
- **进度查询**：随时查看各知识点的真实完成状态。
- **内置风控规避**：处理完一个知识点自动间隔，遇到「多窗口」风控自动等待重试。

---

## 目录结构

| 文件 | 作用 |
|------|------|
| `njupt_skip.py` | 主脚本：刷课（自动完成所有视频 / PDF 知识点） |
| `exam_submit.py` | 自动作答考试并提交 |
| `query_status.py` | 查询课程各知识点的完成进度 |
| `exam_questions.json` | 考试题目原文 + 选项 + 答案（存档，供核对） |
| `config.example.json` | 配置文件模板（复制为 `config.json` 后填写凭证） |
| `config.json` | 你的本机配置（**已被 .gitignore 忽略，绝不提交**） |
| `main.py` / `main_login.py` / `utils.py` | 上游「江苏省校园安全通」历史脚本（与本平台无关，可忽略） |

---

## 环境要求

- Python 3.7+（Windows / macOS / Linux 均可）
- 无需安装第三方库（全部使用标准库 `urllib` / `json` / `ssl`）

---

## 快速开始

### 第 1 步：登录并获取 Access-Token

1. 用你自己的账号登录 `https://study.njupt.edu.cn`。
2. 按 `F12` 打开开发者工具 → 顶部选 **Application / 应用** → 左侧 **Local Storage / 本地存储**
   → 点开 `https://study.njupt.edu.cn`。
3. 找到键名为 **`Access-Token`** 的项，复制它的**值**（一段很长的字符串）。
   （也可以在任意接口请求的 **Headers** 里看到 `X-Access-Token` 字段，值相同。）

> Access-Token 会过期（约 7 天）。失效后重新复制即可。

### 第 2 步：配置凭证

复制模板并填入 token（也可不用文件，见下文命令行 / 环境变量方式）：

```bash
cp config.example.json config.json     # Linux/macOS
copy config.example.json config.json   # Windows
```

编辑 `config.json`：

```json
{
  "token": "粘贴你复制到的 Access-Token",
  "tenant_id": "0",
  "course_id": "2077931772737286146",
  "interval_between": 6
}
```

- `course_id`：课程 ID，即课程播放页 URL 里 `?id=` 的值。
- `interval_between`：每学完一个知识点后等待的秒数（用于规避「多窗口」风控）。

### 第 3 步：刷课

```bash
python njupt_skip.py
```

脚本会列出每个知识点，逐个上报学习进度到 `100%`。默认模式为“分段递增上报”，更稳妥；
如果想一次到位（较快但仍可能被风控），加 `--fast`。

### 第 4 步（可选）：查看进度

```bash
python query_status.py
```

输出每个知识点的 `finishStatus / finishBfb / finishHour / knowHour`，确认服务端真实完成情况。

### 第 5 步：考试

先把 `exam_questions.json` 里的答案核对一遍（也可自行修改答案），然后：

```bash
python exam_submit.py
```

脚本会取卷、填答案、经 `saverecords` 提交，再用 `getExamResultDetail` 核对成绩。
本仓库考试答案为 **满分（100 / 100）**，合格线 90 分。

---

## 命令行 / 环境变量方式（不想写 config.json 时）

```bash
# 命令行传参
python njupt_skip.py --token=你的token --course=2077931772737286146
python njupt_skip.py --fast

# 环境变量
set NJUPT_TOKEN=你的token        # Windows
export NJUPT_TOKEN=你的token     # macOS / Linux
```

---

## 工作原理（调用平台真实接口）

### 课程 / 学习进度

| 用途 | 方法 | 接口 |
|------|------|------|
| 获取课程详情（含全部知识点） | GET | `/service-api/app/study/course/info?id={courseId}` |
| 上报学习进度 | POST | `/service-api/app/study/my/course/start` |

`/course/start` 请求体：`courseId, sectionId, knowId, playTime, end, intervalTime, currentPage, totalPage`。

完成判定：服务端累计该知识点的已学时长 `finishHour`，当 `finishHour >= knowHour`（视频总秒数）
时标记完成。所以脚本会让 `playTime` 分段递增到 `knowHour`，最后一次 `end=1`。

### 考试

| 用途 | 方法 | 接口 |
|------|------|------|
| 取出试卷与题目 | GET | `/service-api/exam/app/examDetail/loadExamDetailList?examId=…` |
| 提交答案 | POST | `/service-api/exam/app/examDetail/saverecords` |
| 查询成绩 | GET | `/service-api/exam/app/examDetail/getExamResultDetail?erId=…` |

答案格式：单选 `userAnswer = "B"`；多选 `userAnswer = ["A","C"]`。

### 认证

所有请求带请求头：`X-Access-Token: <你的Access-Token>` 与 `tenant_id: 0`。

---

## 注意事项与免责声明

1. 请**只用于你本人的账号**，用于日常学习、补课。
2. 自动化刷课/答题属于**绕过平台学习与考试要求**的行为，存在被平台标记、封禁的风险。
3. `config.json` 含你的登录凭证，已被 `.gitignore` 忽略，**请勿将其提交或上传到任何仓库**。
4. 不同课程的题库 / 知识点可能不同，若换课请重新取题核对答案。
5. 本项目仅供学习交流，请遵守学校与平台的有关规定。
