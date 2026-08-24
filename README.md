# 南邮在线课堂「刷课 + 考试」自动化脚本

> 本仓库主要针对 **南京邮电大学在线培训平台**（`https://study.njupt.edu.cn`）
> 的自动化脚本：自动完成课程的 **视频 / PDF 学习进度**，并自动作答课程的 **在线考试**。

> ⚠️ **仅供本人账号自主学习 / 补课使用。**
> 脚本通过调用平台真实接口模拟学习与答题，属于绕过平台"防挂机 / 防作弊"限制的行为，可能被平台判定为异常、存在账号风险。请自行评估，切勿用于批量处理他人账号或违反学校规定。本项目仅用于技术学习与交流，作者不承担任何因使用不当导致的后果。

---

## 特性

- **仅依赖 Python 标准库**，无需 `pip install` 任何第三方包。
- **自动刷课**：遍历课程全部知识点，模拟"完整观看视频 / 阅读 PDF"，逐个完成到 `100%`。
- **自动考试**：读取试卷、逐题作答并提交，已实测 **满分 100 / 100**（合格线 90）。
- **进度查询**：随时查看各知识点的真实完成状态。
- **内置风控规避**：处理完一个知识点自动间隔，遇到「多窗口」风控自动等待重试。
- **题库容错**：若考试题目不在内置题库内，会提示无法作答并中止，避免答错丢分。
- **图形界面版**：内置 `njupt-gui/` 子目录，提供美观的 **GUI 客户端**（自动刷课 / 查进度 / 自动考试一键按钮操作），并附已打包的 **`njupt-gui/NJUPT课程助手.exe`**，Windows 双击即可使用，无需安装 Python。

---

## 一、安装需要的东西（新手必看）

这个项目只用到 **Python**，还需要一个能打开"终端/命令行"的工具。

### 1. 安装 Python

1. 打开官网下载页：<https://www.python.org/downloads/> ，下载最新的 Python 3（推荐 3.8 以上）。
2. 运行安装包，**务必勾选底部的 `Add python to PATH`**，再点 `Install Now`。
3. 安装完成后，打开"命令提示符"(cmd) 或 "PowerShell"（按 `Win 键` 输入 `cmd` 或 `PowerShell` 回车），输入：
   ```bash
   python --version
   ```
   能看到 `Python 3.x.x` 就说明装好了。

### 2. 安装 Git（可选，只用 `git clone` 拉代码才需要）

1. 下载安装：<https://git-scm.com/downloads> ，一路下一步即可。
2. 装好后在命令行输入 `git --version` 能看到版本号即可。

> 如果你嫌麻烦，也可以**不装 Git**，直接看下文"方式二：下载 ZIP"。

---

## 二、获取本项目

### 方式一：用 Git 克隆（推荐）

打开命令行，进入你想存放的文件夹（例如 `cd Desktop`），然后执行：

```bash
git clone https://github.com/HClOLyw/njupt-course-auto.git
cd njupt-course-auto
```

### 方式二：下载 ZIP（不装 Git）

1. 打开仓库页面 <https://github.com/HClOLyw/njupt-course-auto> 。
2. 点绿色 **Code** 按钮 → **Download ZIP**。
3. 解压到本地，进入解压后的文件夹。

---

## 三、项目中各文件是干嘛的

| 文件 | 作用 |
|------|------|
| `njupt_skip.py` | **刷课**：自动完成课程里所有视频 / PDF 知识点 |
| `exam_submit.py` | **考试**：读取试卷、填答案、提交 |
| `query_status.py` | **查进度**：查看每个知识点是否已学完 |
| `config.json` | 你的**配置**（登录凭证、课程 ID 等），自带的 token 是空的 |
| `config.example.json` | 配置模板，内容和 `config.json` 一样，参考用 |
| `exam_questions.json` | 考试题目原文 + 选项 + 答案存档 |
| `main.py` / `main_login.py` / `utils.py` | 上游"江苏省校园安全通"的历史脚本，与本平台无关，可忽略 |
| `njupt-gui/` | **图形界面版**：GUI 客户端源码 + 可直接运行的 `NJUPT课程助手.exe`（详见该目录 README） |

---

## 四、使用教程（一步一步来）

### 第 1 步：登录平台，拿到 Access-Token

1. 用你自己的账号登录 <https://study.njupt.edu.cn> 。
2. 在浏览器页面上按 **F12** 打开开发者工具（或右键 → 检查）。
3. 找到顶部标签 **Application**（中文版叫"应用"）。
4. 左侧找 **Local Storage / 本地存储**，点开 `https://study.njupt.edu.cn`。
5. 在右侧列表里找到键名为 **`Access-Token`** 的那一行，复制它的**值**（一长串字符）。
   - 也可以在任意接口请求的 **Headers** 里看到 `X-Access-Token` 字段，值是一样的。

> Token 约 7 天过期。失效后，重新登录再复制一次即可。

### 第 2 步：把 Token 填进 `config.json`

用记事本或任意编辑器打开项目里的 **`config.json`**，把 `token` 改成你的 token：

```json
{
  "token": "粘贴你的 Access-Token",
  "tenant_id": "0",
  "course_id": "2077931772737286146",
  "interval_between": 6
}
```

各字段含义：

| 字段 | 含义 |
|------|------|
| `token` | 第 1 步复制的 Access-Token（**需要填的就是这一个**） |
| `tenant_id` | 租户号，一般保持 `"0"` 不用动 |
| `course_id` | 你课程/考试对应的课程 ID，即播放页 URL 里 `?id=` 的值 |
| `interval_between` | 每学完一个知识点后等待的秒数（越大越不容易触发风控，默认 6） |

> ⚠️ **重要**：仓库自带的 `config.json` 里 token 是**空的**（这是故意的，避免泄露）。请**只在你自己本地的 `config.json` 里填 token**，千万不要把填了真实 token 的文件提交/上传到任何地方。

### 第 3 步：刷课（自动完成视频 / PDF）

打开命令行，进入项目文件夹，然后运行：

```bash
python njupt_skip.py
```

脚本会列出每个知识点并逐个上报学习进度到 `100%`，全程自动，无需干预。
它默认每学完一个知识点会停几秒（`interval_between`），避开平台的"多窗口"风控。

- 想更快可加 `--fast`：`python njupt_skip.py --fast`（更快但更易触发风控，不推荐）。

### 第 4 步（可选）：查看学习进度

想确认哪些知识点已经完成，运行：

```bash
python query_status.py
```

会显示每个知识点的完成状态、百分比。

### 第 5 步：考试（自动作答并提交）

课程学完后，运行：

```bash
python exam_submit.py
```

脚本会：取试卷 → 逐题填答案 → 提交 → 核对成绩。
本仓库答案已实测 **满分 100 / 100**，合格线 90。
提交前会先检查题目是否都在内置题库里；若发现**不在题库里的题**，会打印题目并中止。

### 第 6 步：如果遇到题不在题库里怎么办

> 平台的题目**可能会变化**。如果 `exam_submit.py` 提示"有题目不在题库内"，说明试卷换题了。此时脚本**不会强行作答**（避免答错丢分）。

**解决办法**：
1. 脚本会把这些题目的**原文和选项**打印出来。
2. 用 **AI agent（比如 Claude Code / DSH / Codex 等）** 自行搜索这些题的答案。
3. 把答案补进 `exam_submit.py` 里的 `ANSWERS` 字典，或更新 `exam_questions.json`。
4. 重新运行 `python exam_submit.py`。

---

## 五、不想改 config.json 时

也可以直接用**命令行参数**或**环境变量**提供 token（二选一即可）：

```bash
python njupt_skip.py --token=你的token --course=2077931772737286146
python njupt_skip.py --fast

# 或用环境变量
set NJUPT_TOKEN=你的token        # Windows
export NJUPT_TOKEN=你的token     # macOS / Linux
```

---

## 六、常见问题（FAQ）

**Q1：`python` 不是内部或外部命令？**
安装 Python 时没勾选 `Add python to PATH`。重新安装并勾选，或手动把 Python 加入环境变量。

**Q2：提示 "未提供 Access-Token"？**
说明 `config.json` 的 token 还是空的（或没填对），参考"第 1、2 步"重新复制、填写。

**Q3：提示 "禁止多窗口同时观看"？**
这是平台风控。脚本已内置等待与重试，一般会自己恢复；也可以把 `interval_between` 调大一点。

**Q4：刷课/考试后没生效？**
用 `python query_status.py` 看服务端真实进度（脚本"上报成功"并不等于一定计入，以平台实际为准）。

**Q5：换了一门课 / 换学校怎么办？**
把 `config.json` 里的 `course_id` 改成新课程的 ID；考试如换题，参考"第 6 步"补充答案。

---

## 七、工作原理（调用平台真实接口，与浏览器行为一致）

### 学习进度

| 用途 | 方法 | 接口 |
|------|------|------|
| 获取课程详情（含全部知识点） | GET | `/service-api/app/study/course/info?id={courseId}` |
| 上报学习进度 | POST | `/service-api/app/study/my/course/start` |

完成判定：服务端累计已学时长 `finishHour`，当 `finishHour >= knowHour`（视频总秒数）时标记完成。
所以脚本让 `playTime` 分段递增到 `knowHour`，最后一次 `end=1`。

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

## 八、来源与致谢

本项目是对开源项目 **[Scwizard/jiangsu-safety-platform-skip](https://github.com/Scwizard/jiangsu-safety-platform-skip)** 的**二次开发**。

- **上游项目**：[Scwizard/jiangsu-safety-platform-skip](https://github.com/Scwizard/jiangsu-safety-platform-skip) ——《“2026 江苏省大学新生安全知识教育”一键完成脚本》
- **原作者**：Scwizard（南京晓庄学院）
- **上游许可证**：[Apache License 2.0](./LICENSE)（本项目保留该许可证）
- **上游用途**：针对**江苏省校园安全通平台**（`wap.xiaoyuananquantong.com`）的刷课/刷题脚本。

本仓库在原项目思路上二次开发为针对**南京邮电大学在线培训平台**（`study.njupt.edu.cn`）的刷课 + 考试脚本，并保留上游 `main.py` / `main_login.py` / `utils.py` 作为历史参考。感谢原作者 **Scwizard** 的开源贡献。

---

## 九、注意事项与免责声明

1. 请**只用于你本人的账号**，用于日常学习、补课。
2. 自动化刷课/答题属于**绕过平台学习与考试要求**的行为，可能存在账号风险，请谨慎评估。
3. `config.json` 里的 token 是敏感凭证，**请勿把填写了真实 token 的文件提交或上传到任何仓库**。
4. 不同课程 / 学校的题库可能不同，换课请重新取题核对答案。
5. 本项目仅供学习交流，请遵守学校与平台的有关规定。
