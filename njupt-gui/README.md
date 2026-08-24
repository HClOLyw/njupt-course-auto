# 南邮在线课堂 · 自动化助手（GUI 版）

> 🚀 **快速使用**：Windows 用户直接双击本目录下的 **`NJUPT课程助手.exe`** 即可打开图形界面，无需安装 Python。
> 输入登录凭证后，通过按钮即可完成 **自动刷课 / 进度查询 / 自动考试**。

> 基于开源项目 [njupt-course-auto](https://github.com/HClOLyw/njupt-course-auto) 二次开发的
> **图形界面**版本，把刷课 / 查进度 / 考试三大功能封装成按钮，开箱即用。

> ⚠️ **仅供本人账号自主学习 / 补课使用。**
> 自动操作为绕过平台"防挂机 / 防作弊"限制的行为，可能被平台判定为异常、存在账号风险。
> 请自行评估，切勿用于批量处理他人账号或违反学校规定。本项目仅用于技术学习与交流。

---

## ✨ 功能

| 按钮 | 说明 |
|------|------|
| ▶ 自动刷课 | 遍历课程全部知识点，模拟"完整观看视频 / 阅读 PDF"，逐个完成到 100% |
| 📈 进度查询 | 查看每个知识点的真实完成状态、百分比（表格展示） |
| ✍ 自动考试 | 读取试卷、逐题作答并提交（内置题库已实测 100/100，合格线 90） |
| ⚙ 参数设置 | 填写 Access-Token、课程 ID、考试 ID、间隔秒数 |
| ℹ 关于说明 | 功能原理与免责声明 |

界面特性：深色侧边导航 + 卡片式首页 + 圆角按钮 + 彩色运行日志（成功/警告/错误分色）+ 实时进度条。

---

## 🚀 快速开始（直接运行源码）

### 1. 安装 Python

- 官网下载 <https://www.python.org/downloads/>，安装时 **务必勾选 Add python to PATH**（3.8 以上均可）。
- 验证：命令行输入 python --version 能看到版本号。

### 2. 获取 Access-Token

1. 用你自己的账号登录 <https://study.njupt.edu.cn>。
2. 按 F12 打开开发者工具 → Application（应用）→ 左侧 Local Storage。
3. 找到 https://study.njupt.edu.cn 下的键 Access-Token，复制它的值。
   （也可以在任意接口请求的 Headers 里看到 X-Access-Token，值相同。）
4. Token 约 7 天过期，失效后重新登录再复制即可。

### 3. 启动程序

cd njupt-gui
python njupt_gui.py

在 **参数设置** 页粘贴 Token，核对课程 ID / 考试 ID（设置页与考试页都可改），
点击 **保存配置**，然后回到对应功能页点按钮即可。

---

## 📦 打包成独立 EXE（无需装 Python 运行）

1. 安装 Python。
2. 双击运行 **build.bat**（会自动安装 PyInstaller 并打包）。
3. 打包完成后，双击 **dist 目录里的 NJUPT课程助手.exe** 即可使用。

也可以手动打包：

pip install pyinstaller
pyinstaller -F -w -n "NJUPT课程助手" --icon app_icon.ico --add-data "config.json;." --add-data "exam_questions.json;." --add-data "njupt_api.py;." --add-data "app_icon.ico;." njupt_gui.py

> 说明：config.json 会打包进 exe 内，运行时会自动读取/创建于 exe 同目录（代码里
> 使用 os.path.dirname(os.path.abspath(__file__))），便于你修改 token。

---

## ⚙ 配置说明

| 字段 | 含义 |
|------|------|
| token | 登录平台后复制的 Access-Token（需要填的就是这一个） |
| tenant_id | 租户号，一般保持 "0" |
| course_id | 课程 ID，即播放页 URL 里 ?id= 的值 |
| exam_id | 考试 ID，默认内置在脚本 ANSWERS 映射中 |
| interval_between | 每学完一个知识点后等待的秒数（越大越不易触发风控，默认 6） |

---

## 🗂 文件说明

| 文件 | 作用 |
|------|------|
| njupt_gui.py | GUI 主程序（双击运行 / 打包入口） |
| njupt_api.py | 核心逻辑封装（刷课/查进度/考试 + HTTP + 题库） |
| config.json | 你的配置（登录凭证、课程 ID 等） |
| exam_questions.json | 考试题目原文 + 选项 + 答案存档 |
| app_icon.ico | 程序图标 |
| build.bat | Windows 一键打包脚本（PyInstaller） |
| self_test.py / e2e_test.py | 自动化测试（验证界面与核心逻辑） |

---

## 🔧 工作原理

- 学习进度：GET /app/study/course/info 获取全部知识点 → POST /app/study/my/course/start 分段上报进度。
- 考试：GET /exam/app/examDetail/loadExamDetailList 取卷 → 填写答案 → POST /exam/app/examDetail/saverecords 提交。
- 认证：请求头 X-Access-Token + tenant_id。
- 题库容错：若考试题目不在内置题库内，会列出题目并**中止提交**，避免答错丢分。

---

## ⚠️ 免责声明

1. 请**只用于你本人的账号**，用于日常学习、补课。
2. 自动化刷课 / 答题属于**绕过平台学习与考试要求**的行为，可能存在账号风险，请谨慎评估。
3. config.json 里的 token 是敏感凭证，**请勿把填写了真实 token 的文件提交或上传到任何仓库**。
4. 平台题目**可能变化**；换题后请用 AI 搜索答案补充到题库再重试。
5. 本项目仅供学习交流，请遵守学校与平台的有关规定。

---

## 🙏 致谢

- 上游项目：HClOLyw/njupt-course-auto (https://github.com/HClOLyw/njupt-course-auto)
- 上游上游：Scwizard/jiangsu-safety-platform-skip (https://github.com/Scwizard/jiangsu-safety-platform-skip)
- 许可证：Apache License 2.0
