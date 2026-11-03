# 开放 API

开放 API 用于让自己的脚本、自动化工具或其他服务读取状态、日志，管理插件或发送 Telegram 消息。不写脚本的管理员，可以完全不用开启它。

本页按 **v2.0.2.7** 核对，先给能直接照着操作的示例。每个字段、参数和响应的完整说明，以**自己部署的系统**中的 API 文档为准。

相关页面：[首次使用](First-Run) · [插件管理](Plugins) · [账号与通知](Accounts-and-Notifications) · [安全与维护](Maintenance)

## 1. 在哪里看文档

默认地址：

```text
http://你的服务器IP:18001/docs
```

如果使用域名反向代理，则打开：

```text
https://你的域名/docs
```

端口不是固定必须为 `18001`。安装时改过端口，就使用实际网页访问端口；反向代理后一般使用域名即可。`127.0.0.1` 只代表正在执行请求的那台机器，从手机访问服务器时不能写手机自己的 `127.0.0.1`。

也可从「系统设置 → 开放接口 → 查看 API 文档」进入。

![API 文档界面](https://raw.githubusercontent.com/wiki/AWdress/AWBotNest/images/api-docs.jpg)

*文档按系统、Telegram、插件管理、插件配置、插件数据、账号与日志分类。展开接口即可查看参数、响应和调试入口。*

## 2. 开启或关闭

1. 登录管理网页，打开「系统设置 → 开放接口」。
2. 点击随机生成 API Key，或设置足够长、随机的密钥。
3. 点击「保存设置」。只有保存后才生效。
4. 在自己的工具中使用该密钥。

**关闭方式：清空 API Key 并保存。** 当前没有另一个独立的 API 开关。关闭后，开放 API 返回未配置提示；系统网页仍可正常使用。

![开放接口设置，Webhook 密钥与 REST API Key 分开配置](https://raw.githubusercontent.com/wiki/AWdress/AWBotNest/images/open-api.jpg)

重新生成并保存会使旧密钥失效，记得同时更新自己的自动化脚本。不要把 Key 发给陌生人、写进公开仓库、贴到 issue 或保存在截图中。

## 3. 三种凭据不要混用

| 用途 | 凭据 | 放在哪里 |
| --- | --- | --- |
| 登录管理网页 | 管理员用户名、密码以及网页使用的管理令牌 | 管理网页登录流程；不要拿它充当开放 API Key。 |
| 调用本页的开放 API | 「开放接口」中保存的 API Key | HTTP 请求头 `X-API-Key`；兼容 `Api-Key`。 |
| 接收统一 Webhook 通知 | 「开放接口 → Webhook 入站」中的独立密钥 | 对应 Webhook 地址，规则与开放 API 不同。 |

开放 API 路径以 `/api/v1/` 开头。普通网页管理接口 `/api/...` 不能简单换一个 Key 后照搬使用。

**不要写成 `Authorization: Bearer 你的开放API密钥`。** 当前开放 API 读取的是 `X-API-Key` 或 `Api-Key` 请求头；网页管理员接口使用的 Bearer 鉴权不是同一套。

### Webhook 入站：外部服务发通知

这是一套独立的兼容入口，不使用上面的 `X-API-Key`，也不列在 `/docs` 的 REST 接口列表中。

1. 在「系统设置 → 开放接口 → Webhook 入站」设置独立密钥并保存；清空此密钥并保存即可关闭。
2. 在可信调用工具中配置 `POST /api/v1/webhook`，查询参数 `apikey` 填这个 **Webhook 密钥**，请求头使用 `Content-Type: application/json`。
3. 请求体可使用下面的格式；这是一次真实通知，会交给系统通知服务投递，不是插件动作或助手指令。

```json
{
  "title": "备份结果",
  "text": "今日备份完成",
  "category": "backup"
}
```

`title` 和 `category` 可省略。正文优先读取 `text`，其次 `message`、`content`；JSON 对象没有这些非空字段时，会作为 JSON 文字发送。也接受纯文本请求体，请求体上限为 1 MB。入口同时接受 GET，但不会把查询参数里的 `text` 当成通知正文，发送内容建议使用上面的 POST 格式。

成功返回 `{"ok": true}`。未开启返回 `404`，密钥错误返回 `401`，超出体积返回 `413`；通知服务不可用或投递失败也会返回错误，不能只看 HTTP 请求已发出就认定通知送达。

**插件兼容入口不同：** `/api/v1/plugin/{plugin_id}/webhook` 使用同一个 Webhook 密钥和查询参数，支持 GET/POST、同样限制 1 MB，但把请求交给该插件已注册的第一个 Webhook（没有注册项时尝试 `receive`）。插件必须已启用且存在处理器；正文格式与实际副作用由插件决定，不会自动套用上面的通知格式。开发者应按[插件开发规范](Plugin-Development)处理鉴权及参数校验，管理员只按可信作者提供的说明调用。

这两种兼容入口的密钥都在 URL 查询参数中。**不要把完整调用地址公开、发到群里或贴进 Issue。** 只在受信工具中保存，使用 HTTPS，尽可能限制来源网络，并避免让反向代理或调用工具记录完整查询参数；泄露后立即更换 Webhook 密钥。不要拿开放 API Key 或管理员令牌代替它。

## 4. 先做一次只读测试

下面是 Linux/macOS 的 Bash 示例。`BASE_URL` 是演示变量，按自己的地址修改；密钥在执行时输入，不要写死在脚本中。

```bash
BASE_URL='http://127.0.0.1:18001'
read -rsp '请输入开放 API Key: ' AWBOTNEST_API_KEY
printf '\n'
export AWBOTNEST_API_KEY

curl --fail-with-body --show-error \
  -H "X-API-Key: $AWBOTNEST_API_KEY" \
  "$BASE_URL/api/v1/status"
```

响应示例（数字与在线状态以实际系统为准）：

```json
{
  "version": "2.0.2.7",
  "bot_connected": false,
  "user_accounts_count": 0,
  "total_plugins": 1,
  "enabled_plugins": 1,
  "enabled_plugin_ids": ["hello_demo"]
}
```

没有连接 Telegram 账号时，`bot_connected: false` 本身不表示 API 坏了；独立运行插件不需要 Telegram 账号。

`read -s` 可以避免输入内容直接显示在终端、进入命令历史，但不等于密钥绝对不可见。在不可信的共享主机上不要运行含密钥的调试命令；自动化部署使用服务端的 Secret 管理功能，避免开启会打印请求头的调试日志。

## 5. 读取系统和插件日志

### 系统最近日志

```bash
curl --fail-with-body --show-error \
  -H "X-API-Key: $AWBOTNEST_API_KEY" \
  "$BASE_URL/api/v1/logs?limit=50"
```

### 某个插件的最近日志

先列出插件，找到 `id`；它是英文标识，不是卡片显示的中文名称。

```bash
curl --fail-with-body --show-error \
  -H "X-API-Key: $AWBOTNEST_API_KEY" \
  "$BASE_URL/api/v1/plugins"

PLUGIN_ID='hello_demo'
curl --fail-with-body --show-error \
  -H "X-API-Key: $AWBOTNEST_API_KEY" \
  "$BASE_URL/api/v1/logs/plugins/$PLUGIN_ID?limit=50"
```

系统日志返回 `{"logs": [...]}`；插件日志还包含 `plugin_id`。每条记录包含 `timestamp`、`level`、`source`、`message`。

- `limit` 的有效范围是 1–1000，超出会被限制。
- 返回的是系统保留的最近历史，不是全部磁盘日志，也不是无限翻页查询。
- 插件接口按该插件的日志来源筛选；作者绕过 `ctx.log` 写到其他 logger 的记录，可能不会出现在该插件筛选结果里。
- 空列表可能只是当前保留范围内没有相应记录，不代表插件从未运行。
- 时间戳包含时区信息，第三方工具展示时应正确换算，不能单纯去掉时区后拼接。

这两个 GET 接口都是只读，不会清理日志或触发任务。

## 6. 通过 API 推送插件

适合开发者把自己写好的单文件插件发到系统，也适合在自己的部署流水线中使用。

**上传的是可执行代码，不是普通配置。请只上传自己检查过的插件。API Key 的持有人具备较高管理权限，不应提供给只需要看一条状态的陌生服务。**

假设当前目录有一个符合 V2 规范的 `hello_demo.py`：

```bash
curl --fail-with-body --show-error \
  -H "X-API-Key: $AWBOTNEST_API_KEY" \
  -F 'file=@hello_demo.py' \
  "$BASE_URL/api/v1/plugins/upload"
```

要求：

- 使用 `multipart/form-data`，字段名是 `file`；curl 的 `-F` 会自动设置格式。
- 只支持单个 UTF-8 `.py` 文件，非空，大小不超过 2 MB。
- 文件名和 `__plugin__["id"]` 必须一致，例如 `hello_demo.py` 对应 `hello_demo`。
- 文件名使用安全的字母、数字和下划线，避免空格、中文、路径或特殊符号。
- 不能把 ZIP 包、完整 Git 仓库、任意目录直接提交到这个接口。

成功响应包含 `ok`、`plugin` 和 `enabled`。新安装的插件不会自动启用，也不会在上传阶段保证它的第三方依赖或所有业务逻辑都能运行。

同名上传可能覆盖已有插件文件。更新已有插件前先备份、停用，再上传；不要认为上传成功就已经热更新了旧实例。目录插件或带前端资源的插件，使用[插件市场](Plugins#2-从插件市场安装推荐)更合适。

### 配置好后启用

先回管理网页检查配置和权限。确认无误，再调用：

```bash
curl --fail-with-body --show-error -X POST \
  -H "X-API-Key: $AWBOTNEST_API_KEY" \
  "$BASE_URL/api/v1/plugins/hello_demo/enable"
```

成功示例：

```json
{"ok": true, "message": "插件已启用"}
```

启用失败会返回错误状态及 `detail`，例如缺少依赖、账号未就绪或必填配置未填写。不要写一个遇到任何失败就无限重试启用的脚本。

### 能否直接远程改源码

`GET /api/v1/plugins/{plugin_id}/source` 可以读取入口源码，响应包含 `plugin_id`、`path`、`source`、`is_package`。

`PUT /api/v1/plugins/{plugin_id}/source` **已因安全原因禁用，固定返回 403**。不要照搬旧教程调用它修改代码。需要更新时使用可信文件上传或商店安装流程。

读取源码同样是高权限操作；返回内容可能包含业务逻辑或作者误写进代码的敏感值，不要直接公开保存。

## 7. 其他常用接口

| 接口 | 用途与提醒 |
| --- | --- |
| `GET /api/v1/plugins` | 列出插件及其 ID、版本、状态。 |
| `GET /api/v1/plugins/{plugin_id}` | 查询一个插件的详情。 |
| `POST /api/v1/plugins/{plugin_id}/disable` | 停用，不删除插件。 |
| `POST /api/v1/plugins/{plugin_id}/reload` | 重载；可能打断进行中的任务。 |
| `GET /api/v1/plugins/{plugin_id}/config` | 读取配置，已声明的敏感字段返回掩码。 |
| `PUT /api/v1/plugins/{plugin_id}/config` | 请求体使用 `{"config": {...}}`；可能重载已启用插件。 |
| `GET /api/v1/accounts` | 读取账号状态，不返回 Bot Token 或 Session 文件。 |
| `POST /api/v1/messages/send` | 通过已连接的 Bot 或用户账号发送消息，详细字段见系统内文档。 |
| `/api/v1/plugins/{plugin_id}/kv...` | 插件持久化键值数据；账号实例插件必须指定 `instance`，修改、删除前先备份。 |

读取配置返回的 `********` 可在原字段原样传回，以保留已保存的敏感值。不要拿这个掩码作为新的实际密码，也不要以为开放 API 有一个“返回所有真实密钥”的通用接口。

### 发文件、企业微信与助手是不是也用这些接口

要区分 **HTTP 开放 API** 与 **插件运行时接口**：

- 本页的 `/api/v1/messages/send` 发送 Telegram 文字消息，当前没有对应的开放 REST 文件发送或企微文件发送端点，不要自行拼一个 `/files/send` 地址。
- 已安装的插件可以通过 Telegram 客户端原生 `send_file` 发文件；企业微信插件可以通过系统的统一消息上下文回复 Excel、CSV 等文件，复用已有应用凭据。代码和接入方法见 [插件开发入门](Plugin-Development)，不是把文件传给文字消息接口。
- 企业微信统一回调可接收文字、图片、文件和按钮事件，入口在通知渠道中配置，与开放 API Key 是两套鉴权。见 [账号与通知](Accounts-and-Notifications)。
- 系统助手的会话、配对和确认接口只接受管理员登录权限，不接受本页的 API Key。不能把 API Key 发给 Bot 后要求它获得助手管理权限。

### 只检查服务是否就绪

容器健康检查可读取不要求开放 API Key 的 `GET /healthz` 与 `GET /readyz`：前者检查服务存活，后者在初始化未完成或失败时返回 `503`，就绪后返回 `200`。`GET /api/v1/status` 则需要 API Key，并提供插件、账号等状态。三者用途不同，不要因为网页已打开就忽略就绪状态。

## 8. 文档里的“试一试”怎么用

1. 在 `/docs` 中找到鉴权入口，填入开放 API Key。
2. 先展开 `GET /api/v1/status`，执行一次只读查询。
3. 看 HTTP 状态码和响应正文。
4. 理解接口作用后，再使用会修改数据的接口。

不要为了熟悉界面随意执行停用、重载、发送消息、改配置或删除 KV 的接口。这些不是模拟操作，会作用到当前系统。

文档页面可以打开，不等于 API 已开启；未保存 Key 时实际调用仍会失败。

## 9. 常见错误怎么查

| 现象或状态码 | 常见原因与处理 |
| --- | --- |
| 连接被拒绝、超时 | 服务没有启动、端口不对、防火墙未放行或域名代理配置有误；先确认网页能打开。 |
| 返回 HTML，不是 JSON | 请求到了登录页、反向代理错误页或其他网站；核对 URL、端口和 `/api/v1/` 路径。 |
| `401` | Key 缺失、错误或已被更换；检查 `X-API-Key` 请求头，不要误用管理密码或 Bearer。 |
| `503` 且提示 Key 未配置 | 进入开放接口，填写 Key 并保存；若不打算开启，保持关闭即可。 |
| `404` | 路径或插件 ID 不对，插件尚未安装；先查询插件列表。 |
| `400` / `422` | 字段名、上传格式、文件类型或参数不合要求；按响应中的 `detail` 和文档修正。 |
| `409` | 插件启用、重载或配置应用失败；到插件日志中查看具体原因。 |
| `403`（修改源码） | 此端点已禁用，不是换个 Key 就能使用。 |
| `502` / Telegram 相关错误 | 请求已到系统，但下游服务或发送失败；检查账号状态、目标权限和网络。 |

提交问题时提供：接口路径、HTTP 方法、状态码和去掉敏感值的响应。不要提供请求头里的 Key，也不要直接上传整份配置。

## 10. 用完后的安全检查

- 公网使用 HTTPS；没有必要时只允许内网或 VPN 访问管理端口。
- 当前是共享 API Key，不提供按接口划分的细粒度权限；拿到 Key 的工具应被当作可信管理工具。
- 不在 URL 查询参数里放 API Key，不在公开网页的 JavaScript 中放密钥。
- 密钥泄露后立即重新生成并保存，再更新自己的工具。
- Bash 调试结束后可执行 `unset AWBOTNEST_API_KEY`；不要把终端截图中的真实输出公开。

下一步：[插件开发入门](Plugin-Development) · [常见问题](Troubleshooting)
