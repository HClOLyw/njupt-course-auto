# 南邮课程学习自动化助手（GUI 版）

> 覆盖两个平台：**南邮在线课堂**（新生教育 / study.njupt.edu.cn）与
> **南邮实验室安全数字化教育平台**（实验室安全教育 / 10.22.192.38）。
>
> 基于开源项目 [njupt-course-auto](https://github.com/HClOLyw/njupt-course-auto) 二次开发的
> **图形界面**版本，把刷课 / 查进度 / 考试三大功能封装成按钮，开箱即用。

> ⚠️ **仅供本人账号自主学习 / 补课使用。**
> 自动操作为绕过平台"防挂机 / 防作弊"限制的行为，可能被平台判定为异常、存在账号风险。
> 请自行评估，切勿用于批量处理他人账号或违反学校规定。本项目仅用于技术学习与交流。

---

## ✨ 功能

| 页面 / 按钮 | 说明 |
|------|------|
| 📊 首页概览 | 当前教育类型、双平台 Token / 课程 / 考试配置状态 |
| ▶ 自动刷课 | （在线课堂）遍历课程全部知识点，模拟"完整观看视频 / 阅读 PDF"，逐个完成到 100% |
| 📈 进度查询 | （在线课堂）查看每个知识点的真实完成状态、百分比（表格展示） |
| ✍ 自动考试 | **教育类型可选**：实验室安全教育=按 Token 获取本账号考试并作答提交；新生教育=在线课堂内置题库默认考试（实测满分） |
| 🧪 实验室安全 | 实验室平台刷课 / 查进度 / 自动考试 / 承诺书（下载模板 + 上传已签字件） |
| ⚙ 参数设置 | 教育类型 + 双平台 Token / 课程 ID / 考试 ID / 间隔秒数 |
| ℹ 关于说明 | 功能原理与免责声明 |

界面特性：深色侧边导航 + 卡片式首页 + 圆角按钮 + 彩色运行日志（成功/警告/错误分色）+ 实时进度条。

---

## 🔀 教育类型（新增）

参数设置与考试页均提供「教育类型」下拉选择，两处共用同一设置、即时联动：

| 模式 | 行为 |
|------|------|
| **实验室安全教育** | 输入实验室 Token 后**自动获取本账号的课程 / 考试**（不同账号课程不同也能正确拉取），无需填写课程 / 考试 ID；启动程序默认进入实验室页 |
| **新生教育** | 保持原有行为：在线课堂，课程 / 考试 ID 留空时按默认安全教育课自动设置 |

> 参数设置页会**按所选教育类型只显示对应平台的字段**（同一时刻只出现一个 Access-Token 输入框，
> 标签已标明所属平台），切换教育类型时字段与提示文字自动切换，不会混淆两个平台的凭证。

---

## 🚀 快速开始（直接运行源码）

### 1. 安装 Python

- 官网下载 <https://www.python.org/downloads/>，安装时**务必勾选 Add python to PATH**（3.8 以上均可）。

### 2. 获取 Access-Token（两个平台）

- **在线课堂**：登录 <https://study.njupt.edu.cn> → F12 → Application → Local Storage，复制键 `Access-Token` 的值（Token 约 7 天过期）。
- **实验室平台**：登录 <http://10.22.192.38:9092>（校园内网）→ 同样复制 Local Storage 里的 `Access-Token`。

### 3. 启动程序

```
cd njupt-gui
python njupt_gui.py
```

在 **参数设置** 页选择教育类型、粘贴对应 Token，点击 **保存配置**，然后到对应功能页点击按钮即可。

---

## 📦 打包成独立 EXE（无需装 Python 运行）

1. 双击运行 **build.bat**（自动安装 PyInstaller 并打包），或：
2. 命令行执行：`python -m PyInstaller "NJUPT课程助手.spec" --noconfirm`
3. 打包完成后，**dist 目录里的 NJUPT课程助手.exe** 即为可执行程序。

> 说明：程序以 exe 同目录下的 config.json 读写配置，首次运行请先保存一次配置（会在 exe 目录生成）。

> 📦 本仓库 `dist/` 目录已附带打包好的 `NJUPT课程助手.exe`，可直接下载使用，无需自行编译。

---

## ⚙ 配置说明

| 字段 | 含义 |
|------|------|
| edu_mode | 教育类型：`lab`=实验室安全教育（按 Token 自动获取课程/考试）；`freshman`=新生教育（在线课堂默认 ID） |
| token | 在线课堂 Access-Token（新生教育模式使用） |
| tenant_id | 在线课堂租户号，一般保持 "0" |
| course_id | 在线课堂课程 ID（留空=默认安全教育课） |
| exam_id | 在线课堂考试 ID（留空=默认） |
| interval_between | 每学完一个知识点后等待的秒数（越大越不易触发风控，默认 6） |
| lab_token | 实验室平台 Access-Token（安全教育模式使用，课程随账号自动获取） |
| lab_base / lab_web | 实验室平台 API / Web 地址（留空使用默认 10.22.192.38:9090 / 9092） |

---

## 🧪 实验室安全教育

针对**南邮实验室安全数字化教育平台**（http://10.22.192.38:9092，后端 API 在
http://10.22.192.38:9090/jeecg-boot，JeecgBoot 框架）：

- **开始刷实验室课程**：按 Token 自动获取我的课程（`myCourseList`）→ 分段上报观看进度（`finishRate`）→
  自动作答视频时间点弹出的题目（正确率实测 100%，答案由接口返回）→ 标记完成（`finish`）。课程随账号不同而变化。
- **查询课程进度**：每门课的观看进度 / 已答总题数 / 答错题数 / 完成状态。
- **自动考试**：按 Token 获取考试（`myExamList` → `startExam`）→ 先通过练习接口收集题库正确答案
  （约 3300+ 题）→ 逐题作答 → 提交（`submitExam`）。题库外题目自动中止提交，避免答错丢分。
- **承诺书**：考试前必须上传本人签字的《实验室安全承诺书》（平台强制要求）——一键下载模板、
  打印签字、拍照后上传（`/sys/common/upload` → `updateMyInfo` 绑定）。

---

## 🔧 工作原理

- **在线课堂**：GET `/app/study/course/info` 获取全部知识点 → POST `/app/study/my/course/start`
  分段上报进度；考试 GET `/exam/app/examDetail/loadExamDetailList` → 填写答案 →
  POST `/exam/app/examDetail/saverecords` 提交。认证：请求头 `X-Access-Token` + `tenant_id`。
- **实验室平台**：认证 `X-Access-Token`（JeecgBoot）。课程=视频+时间点弹题，弹题答案直接由
  `queryCourseQuestionRelaByMainId` 返回；进度按视频时长分段上报 `finishRate`，看完调用 `finish`。
  考试答案收集自练习接口 `questions/queryListByType`（含 `correctAnswer`）。
- 两者均仅依赖 Python 标准库（urllib + ssl），无第三方运行时依赖。

---

## 🗂 文件说明

| 文件 | 作用 |
|------|------|
| njupt_gui.py | GUI 主程序（双击运行 / 打包入口） |
| njupt_api.py | 在线课堂核心逻辑封装（刷课/查进度/考试 + HTTP + 题库） |
| njupt_lab_api.py | 实验室安全教育平台核心逻辑封装（刷课/考试/题库答案收集/承诺书） |
| probe_lab.py | 实验室平台联调探针（真实 token 打印各接口返回，用于校准字段） |
| run_lab_learn.py | 实验室全课程后台刷课运行器（python run_lab_learn.py） |
| config.json | 你的配置（登录凭证、课程 ID 等；勿提交含真实 token 的版本） |
| exam_questions.json | 在线课堂考试题目原文 + 选项 + 答案存档 |
| app_icon.ico / app_icon.png | 程序图标 |
| make_icon.py | 图标生成脚本 |
| build.bat / NJUPT课程助手.spec | 打包脚本 / PyInstaller 配置 |
| self_test.py / e2e_test.py / e2e_default_test.py / e2e_lab_test.py | 自动化测试 |

---

## ✅ 测试

```
python self_test.py          # GUI 控件 / 页面切换 / 教育类型切换 / 配置读写
python e2e_test.py           # 在线课堂刷课/查进度/考试（mock HTTP）
python e2e_default_test.py   # 在线课堂 ID 留空自动回退行为
python e2e_lab_test.py       # 实验室刷课/题库收集/考试/承诺书（mock HTTP）
```

测试全部通过（GUI 自检 + 3 个 e2e 套件），均无需真实网络。

---

## ⚠️ 免责声明

1. 请**只用于你本人的账号**，用于日常学习、补课。
2. 自动化刷课 / 答题属于**绕过平台学习与考试要求**的行为，可能存在账号风险，请谨慎评估。
3. 配置文件里的 token 是敏感凭证，**请勿把填写了真实 token 的文件提交或上传到任何仓库**。
4. 平台题目**可能变化**；换题后请补充题库再重试。
5. 本项目仅供学习交流，请遵守学校与平台的有关规定。

---

## 🙏 致谢

- 上游项目：HClOLyw/njupt-course-auto (https://github.com/HClOLyw/njupt-course-auto)
- 上游上游：Scwizard/jiangsu-safety-platform-skip (https://github.com/Scwizard/jiangsu-safety-platform-skip)
- 许可证：Apache License 2.0