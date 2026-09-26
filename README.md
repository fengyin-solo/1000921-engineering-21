# 实验室样品检测管理平台

面向第三方检测实验室样品接收、任务分配、检测分析、结果复核、报告签发与标物管理的检测业务管理后台。

这是一个前后端分离的管理平台：前端 Vue 3 + Vite + TypeScript，后端 FastAPI（Python）。

## 目录结构

```text
.
├── scripts/
│   ├── dev.sh                 一键本地启动（预检 → 装依赖 → 构建 → 起前后端）
│   ├── check-ability.py       能力验证报名/评定接口自检
│   └── check-ability.sh       make check 入口
├── frontend/                  Vue 3 + Vite + TypeScript 前端
│   ├── src/views/             每个业务模块一个页面
│   ├── src/api/               统一请求封装
│   ├── src/stores/            会话与筛选状态
│   └── package-lock.json      前端依赖锁定文件
├── backend/                   FastAPI（Python）后端
│   ├── app/routers/           每个业务模块一组接口
│   ├── app/services/          业务规则与状态流转
│   ├── app/seed.py            启动即灌入的示例数据
│   └── requirements.txt       后端依赖锁定文件（含传递依赖）
├── .env.example               本地环境变量模板（复制为 .env）
├── Makefile
└── docker-compose.yml
```

## 快速开始（从零到能用）

前置要求：

- Python 3.11+（Debian/Ubuntu 需有 `python3-venv`：`apt install python3-venv`）
- Node.js 18+ 与 npm
- macOS/Linux 的 bash、make

三步：

```bash
# 1. 配置环境变量（至少保留 APP_ENV=local；端口可改）
cp .env.example .env

# 2. 一条命令：预检环境 → 安装锁定依赖 → 前端类型检查与构建 → 同时拉起前后端
make dev

# 3. 另开一个终端，确认能力验证模块的报名与评定接口都能返回
make check
```

`make dev` 成功后终端会打印访问地址：

- 前端页面：<http://127.0.0.1:5173/>（不会自动弹浏览器，手动打开）
- 后端健康检查：<http://127.0.0.1:8000/api/health>
- `/api` 由 vite 代理到后端，无需额外配置

只想分别启动时：`make backend`、`make frontend`；只做依赖准备：`make install`。

## 能力验证模块自检

`make check` 依次验证（只读 + 少量内存写，重启后端即还原）：

1. 后端健康检查通过，示例数据已灌入；
2. 能力验证列表中 `待参加 / 待评定 / 已通过 / 未通过` 四种状态都有数据；
3. 报名链路：登记 → 报名参加（→待评定）→ 上报结果（→已通过）；
4. 评定链路：登记 → 报名参加（→待评定）→ 接收评定（→未通过）；
5. `未通过` 记录可按状态检索；
6. 前端 dev server 在运行时，顺带验证 `/api` 代理已打通。

自检会新增两条 `CHK-` 前缀的临时记录，只存在于内存仓库。全部通过时退出码为 0，
任一接口异常会打印具体失败项并以退出码 1 结束。

## 示例数据

服务一启动，内存仓库就自动灌入示例数据（`backend/app/seed.py`），无需手工造数。
能力验证模块预置 4 条覆盖完整生命周期的真实感数据：

| 验证编号 | 组织方 | 检测项目 | 状态 |
| --- | --- | --- | --- |
| PT-2026-041 | 中国计量科学研究院 | 水中铅、镉含量测定（ICP-MS） | 待参加 |
| PT-2026-017 | 中国合格评定国家认可委员会（CNAS） | 土壤中总石油烃测定 | 待评定 |
| PT-2025-088 | 生态环境部标准样品研究所 | 食品中毒死蜱残留量测定 | 已通过（\|z\|=0.8） |
| PT-2025-102 | 省市场监督管理局 | 环境空气苯系物测定 | 未通过（\|z\|=3.4） |

页面上可直接对任意记录执行「报名参加 / 上报结果 / 接收评定」，状态会真实流转。

## 依赖版本锁定

- 后端：`backend/requirements.txt` 锁定**全部**直接与传递依赖的精确版本
  （如 `fastapi==0.141.1`），不要写 `>=`。更新依赖：

  ```bash
  cd backend && .venv/bin/python -m pip install -U fastapi "uvicorn[standard]" pydantic
  .venv/bin/python -m pip freeze > requirements.txt
  ```

- 前端：`frontend/package-lock.json` 整体锁定，`package.json` 直接依赖也写精确版本。
  必须用 `npm ci` 按锁文件安装（`make install` / `make dev` 都走它）。
  更新依赖后提交更新后的 `package-lock.json`。

- 不要提交 `.venv/`、`node_modules/`（已在 `.gitignore`）。从别的机器拷目录会因
  原生绑定不匹配导致构建失败；启动脚本检测到损坏会自动重建。

## 启动失败排查

`make dev` 的失败信息按原因分两类，开头即可区分：

| 报错开头 | 原因类别 | 处理办法 |
| --- | --- | --- |
| `[启动失败] 依赖缺失：未找到 python3/node/npm` | 依赖缺失 | 安装 Python 3.11+ / Node.js 18+ |
| `[启动失败] 依赖缺失：python3 -m venv 创建失败` | 依赖缺失 | Debian/Ubuntu 执行 `apt install python3-venv` |
| `[启动失败] 依赖缺失：pip install/npm ci 失败` | 依赖缺失 | 检查网络与锁文件，重试即可（失败不会留半成品） |
| `[启动失败] 环境变量未配置：缺少根目录 .env` | 环境变量 | `cp .env.example .env` 后重试 |
| `[启动失败] 环境变量配置错误：APP_ENV=...` | 环境变量 | `APP_ENV` 只能是 `local/dev/test/prod` |
| `[启动失败] 环境变量配置错误：APP_PORT=...` | 环境变量 | 端口必须是 1-65535 的整数 |
| `后端/前端启动失败：端口 ... 被占用` | 端口冲突 | 改 `.env` 里的 `APP_PORT` / `FRONTEND_PORT` |

## 业务模块

| 模块 | 目录 | 业务对象 | 主要字段 |
| --- | --- | --- | --- |
| 样品登记 | `sample` | 检测样品 | 样品编号、样品名称、委托单位 |
| 委托合同 | `contract` | 委托合同 | 合同编号、委托单位、检测项目 |
| 检测任务 | `task` | 检测任务 | 任务编号、关联样品、检测项目 |
| 检测方法 | `method` | 检测方法 | 方法编号、方法名称、标准编号 |
| 仪器设备 | `instrument` | 仪器 | 仪器编号、仪器名称、规格型号 |
| 标准物质 | `standard` | 标准物质 | 标物编号、标物名称、证书编号 |
| 检测结果 | `result` | 检测结果 | 结果编号、关联任务、检测项目 |
| 检测报告 | `report` | 检测报告 | 报告编号、关联任务、编制人 |
| 分包检测 | `boundary` | 分包记录 | 分包编号、分包原因、分包方名称 |
| 不符合项 | `abnormal` | 不符合项 | 不符合编号、发现环节、不符合描述 |
| 环境监控 | `envmonitor` | 环境记录 | 记录编号、监测区域、温度值 |
| 盲样考核 | `blind` | 盲样 | 盲样编号、考核人员、检测项目 |
| 能力验证 | `ability` | 能力验证 | 验证编号、组织方、检测项目 |
| 中间液配制 | `intermediate` | 中间液 | 配制编号、母液编号、目标浓度 |
| 内审检查 | `audit` | 内审记录 | 内审编号、内审日期、内审部门 |
| 认证认可 | `certification` | 资质认定 | 认定编号、认定类型、发证机构 |
| 质控样 | `quality` | 质控样 | 质控样编号、参数名称、标准值 |
| 试剂管理 | `reagent2` | 试剂 | 试剂编号、试剂名称、规格等级 |
| 实验废液 | `waste` | 废液记录 | 废液编号、废液类别、产生环节 |
| 客户反馈 | `opinion` | 反馈记录 | 反馈编号、委托单位、反馈类型 |

## 约定

- 每个模块的前端页面在 `frontend/src/views/<模块>/index.vue`，后端接口在
  `backend/app/routers/<模块>.py`，业务规则在 `backend/app/services/<模块>.py`。
- 列表接口统一返回 `{ items, total, page, size }`，动作接口统一返回 `{ ok, message }`；
  前端调用动作接口时请求体为 `{ "values": { "action": "动作名" } }`。
- 状态流转只允许在 `app/services` 里改，路由层不做业务判断。

## Docker

```bash
docker compose up --build
```

容器内前端监听 5173、后端监听 8000；镜像构建分别使用锁定的 `requirements.txt`
与 `package-lock.json`（`npm ci`）。
