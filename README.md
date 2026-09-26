# 实验室样品检测管理平台

面向第三方检测实验室样品接收、任务分配、检测分析、结果复核、报告签发与标物管理的检测业务管理后台。

这是一个前后端分离的管理平台：前端 Vue 3 + Vite + TypeScript，后端 FastAPI（Python）。
两边各自独立启动，前端 dev server 已关掉自动打开页面，启动后按终端打印的地址手工打开。

## 目录结构

```text
.
├── backend/                  FastAPI（Python） 后端
│   ├── app/routers/          每个业务模块一组接口
│   ├── app/services/         业务规则与状态流转
│   ├── app/seed.py           内存示例数据（启动自动灌入）
│   ├── app/store.py          内存数据仓库
│   ├── requirements.lock     全量依赖版本锁定
│   ├── run.sh                单独启动后端
│   └── scripts/check_ability.py  能力验证接口自检脚本
├── frontend/                 Vue 3 + Vite + TypeScript 前端
│   ├── src/views/            每个业务模块一个页面
│   ├── src/api/              统一请求封装
│   ├── src/stores/           会话与筛选状态
│   ├── package-lock.json     依赖版本锁定（npm ci 使用）
│   └── vite.config.ts        dev/preview server 配置（open: false）
├── scripts/dev.sh            一键开发链路（构建+启动+自检）
├── Makefile                  make up / dev / check 入口
├── .env.example              环境变量模板（零配置也能跑）
└── docker-compose.yml
```

## 本地开发（从零到能用）

### 前置要求

| 工具 | 版本 | 说明 |
| --- | --- | --- |
| Python | 3.10+ | 代码使用 `X | Y` 类型语法；Debian/Ubuntu 精简系统需有 `python3-venv`（脚本也提供了无 venv 时的自动引导） |
| Node.js | 18+（建议 20） | |
| npm | 随 Node 安装 | 依赖按 `package-lock.json` 精确锁定 |
| curl | 任意版本 | 就绪探测与自检使用 |

无需任何数据库；数据是内存仓库，每次启动自动灌入示例数据。

### 一条命令搞定

```bash
make          # 等价于 scripts/dev.sh：装依赖(锁版本) → 构建前端 → 起前后端 → 能力验证自检
```

脚本会依次完成：

1. **依赖预检**：缺 python3/node/npm/curl 时直接报「属于【依赖缺失】」并列出缺什么；
2. **环境变量预检**：读取 `.env`（没有则用默认值），`APP_PORT` 等取值非法时报「属于【环境变量配置错误】」；
3. **按锁文件安装**：后端 `requirements.lock`、前端 `npm ci`，跨机器残留的损坏 `.venv` 会自动重建；
4. **构建并启动**：前端 `vue-tsc` 类型检查 + `vite build` 后起 preview，后端起 uvicorn；
5. **就绪自检**：自动跑能力验证登记/报名/上报/评定全链路，全部通过后打印访问地址。

其他常用命令：

```bash
make dev      # 前端热更新模式（vite dev，跳过生产构建）
make check    # 服务已在运行时，单独重跑能力验证接口自检
make install  # 只安装依赖
make backend  # 只起后端（:8000）
make frontend # 只起前端 dev server（:5173）
```

启动成功后终端会打印：

```text
平台首页     : http://127.0.0.1:5173/
能力验证页面 : http://127.0.0.1:5173/ability
后端健康检查 : http://127.0.0.1:8000/api/health
能力验证自检 : http://127.0.0.1:8000/api/health/ability
接口文档     : http://127.0.0.1:8000/docs
```

### 环境变量

本地零配置即可运行；需要自定义时：

```bash
cp .env.example .env
```

| 变量 | 默认值 | 作用 |
| --- | --- | --- |
| `APP_ENV` | `local` | 运行环境标识 |
| `APP_HOST` | `127.0.0.1` | 后端监听地址 |
| `APP_PORT` | `8000` | 后端端口；改了需同步前端代理 `VITE_PROXY_TARGET` |
| `CORS_ORIGINS` | 本地两个 5173 来源 | 允许跨域来源，逗号分隔 |
| `SEED_DEMO_DATA` | `1` | 启动时是否灌入示例数据 |
| `VITE_PROXY_TARGET` | `http://127.0.0.1:8000` | 前端 `/api` 代理目标（见 `frontend/.env.development`） |

启动失败时的判定口径：脚本输出会明确标注是 **【依赖缺失】**（基础工具/venv/pip/npm 安装失败）
还是 **【环境变量配置错误】**（`.env` 取值非法、端口被占用），并给出修复动作。

### 验证能力验证模块

启动后自带 4 条覆盖完整生命周期的示例数据：

| 验证编号 | 组织方 | 状态 |
| --- | --- | --- |
| ABIL-2026-001 | CNAS | 待参加 |
| ABIL-2026-002 | 国家环境监测能力验证技术委员会 | 待评定（已上报结果） |
| ABIL-2026-003 | 中国食品药品检定研究院 | 已通过（评定合格） |
| ABIL-2026-004 | 省级检验检测机构能力验证中心 | 未通过（评定不合格） |

- 浏览器打开 http://127.0.0.1:5173/ability 可看列表、按状态筛选、执行动作；
- `make check`（或 `python backend/scripts/check_ability.py`）会真实调用接口：
  新建记录 → 报名参加（待参加→待评定）→ 上报结果 → 接收评定（合格→已通过 / 不合格→未通过）
  → 验证终态动作被拦截，任一步失败即以非零码退出。

能力验证状态机：

```text
待参加 ──报名参加──> 待评定 ──接收评定(合格)──> 已通过
                       └────接收评定(不合格)──> 未通过
```

「上报结果」是待评定阶段的信息补录（填写上报日期），不改变状态；跨状态跳转会被服务端拒绝。

### 手动分步启动（不走一键脚本时）

```bash
# 后端
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.lock   # 注意是 .lock，锁定全部传递依赖
./run.sh

# 前端
cd frontend
npm ci          # 必须用 ci，严格按 package-lock.json 安装；不要用 npm install 改写锁文件
npm run build   # 类型检查 + 生产构建
npm run dev     # 或直接起 dev server
```

健康检查：`curl http://127.0.0.1:8000/api/health`

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
- 列表接口统一返回 `{ items, total, page, size }`，动作接口统一返回 `{ ok, message }`。
- 状态流转只允许在 `app/services` 里改，路由层不做业务判断。
