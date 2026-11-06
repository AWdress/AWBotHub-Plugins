# AWBotHub 使用手册

AWBotHub 是一个通过网页管理 Telegram Bot、用户账号和插件的系统。这里从安装开始，说明每一步在哪里操作、应该填什么，以及出错后怎么查。

> 本手册功能说明基于 **v2.0.2.7**，核对日期：**2026 年 11 月 3 日**。旧版数据目录、配置或插件不能直接与当前平台混用，迁移前先核对兼容性。截图使用独立演示数据，不含真实账号、密钥或私人记录；示例插件不代表已内置这些业务功能。

> 2026 年 11 月 6 日校正品牌与官方文档地址；产品现名为 AWBotHub，官方仓库使用 `main` 分支。既有镜像、环境变量与数据目录等兼容标识没有因此改名，操作时以部署说明为准。

![AWBotHub 运行概览（演示数据）](https://raw.githubusercontent.com/AWdress/AWBotHub/main/docs/guide/images/status.jpg)

## 第一次使用，从这里开始

按下面的顺序做即可，不需要一次填完所有设置。

1. **安装系统** → [安装部署](Installation.md)：优先使用 Docker 一键安装，确认能打开登录页面。
2. **设置管理员** → [首次使用](First-Run.md)：创建网页登录账号，了解菜单和必要设置。
3. **接入需要的账号或通知** → [账号与通知](Accounts-and-Notifications.md)：先分清 Telegram 用户账号、Bot 和通知渠道。
4. **安装并启用一个插件** → [插件使用](Plugins.md)：安装只是下载，完成配置并开启后才会运行。
5. **查看运行结果** → [更新、备份与维护](Maintenance.md)：在日志和定时任务中确认是否执行成功。

AI、CookieCloud、浏览器仿真和开放 API 都是按需使用的功能。插件没有要求时，可以暂时不配置。

## 已经在使用？先看这些变化

- **找入口更快：** 顶部“快捷打开”可以搜索插件和设置，电脑可按 `Ctrl + K` / `⌘ + K`。操作见[首次使用](First-Run.md)。
- **首页和插件可整理：** 首页右下角图标调整卡片顺序与显示；插件可设为常用、分组或切换紧凑列表。见[首次使用](First-Run.md)和[插件使用](Plugins.md)。
- **系统助手：** 可排查日志、执行插件已注册的操作、准备配置或源码修改；修改需要管理员确认，敏感值不向助手开放。支持 Telegram 和企业微信配对使用。见[系统助手完整教程](System-Assistant.md)。
- **企业微信文件回传：** 适配的插件可把生成的 Excel、CSV 等文件回复给原发送成员。见[账号与通知](Accounts-and-Notifications.md)和[插件开发](Plugin-Development.md)。
- **忘记密码：** 不用重装或删配置，按[密码重置步骤](Troubleshooting.md#3-管理员无法登录或忘记密码)处理。

想先了解主要功能，可观看 [2 分 30 秒系统宣传片](https://github.com/AWdress/AWBotHub#系统宣传片)，无旁白，含配乐。

## 你想做什么？

| 需求 | 对应文档 |
| --- | --- |
| 从零安装、选择网络模式、修改端口、ARM64 部署 | [安装部署](Installation.md) |
| 第一次登录、系统菜单、手机使用 | [首次使用](First-Run.md) |
| 添加用户账号、Bot，配置 Telegram 或企业微信通知 | [账号与通知](Accounts-and-Notifications.md) |
| 安装插件、配置插件、绑定账号、设置定时、查看报错 | [插件使用](Plugins.md) |
| 添加 AI 服务、选择模型、查看调用和 Token 用量 | [AI 服务](AI-Service.md) |
| 用助手排查问题、改配置、调用插件，接入 Telegram / 企业微信 | [系统助手](System-Assistant.md) |
| 配置 CookieCloud、Chromium、CloakBrowser | [Cookie 与浏览器](Cookies-and-Browser.md) |
| 更新镜像、备份、恢复、查看日志、排查内存占用 | [更新、备份与维护](Maintenance.md) |
| 用脚本读取日志、管理插件、调用开放接口 | [开放 API](Open-API.md) |
| 开发插件、配置表单、Vue 页面和系统能力 | [插件开发入门](Plugin-Development.md) |
| 页面打不开、登录失败、插件不运行、AI 报错 | [常见问题与排查](Troubleshooting.md) |

## 先弄清这几个名字

- **管理员账号**：用来登录 AWBotHub 网页，与 Telegram 账号无关。
- **Telegram 用户账号**：平时在手机 Telegram 上使用的个人账号，需要手机号、验证码，以及可能存在的两步验证密码。
- **Telegram Bot**：通过 `@BotFather` 创建的机器人，使用 Bot Token，不用手机号登录。
- **插件**：提供签到、转发、提醒等具体功能的扩展。每个插件需要的账号、权限和参数可能不同。
- **通知渠道**：用于接收运行结果，例如 Telegram、企业微信、Bark 或 Webhook。通知渠道不等于插件运行账号。
- **系统设置**：多插件共用的 AI、Cookie、浏览器和通知配置。插件自身的业务参数仍然在插件配置中填写。

## 第一次配置的最小清单

- [ ] 已为当前平台使用独立的数据目录，并确认数据会持久保存。
- [ ] 已设置管理员账号和密码，不使用演示密码。
- [ ] 如需 Telegram 功能，已填写自己的 `API_ID` / `API_HASH`。
- [ ] 按插件要求添加用户账号或 Bot，不需要的账号类型不必添加。
- [ ] 插件已经完成配置、绑定正确账号并开启。
- [ ] 已查看一次插件日志，确认不是只安装成功、实际任务却未执行。
- [ ] 已知道自己的数据目录在哪里，并准备了备份。

## 安全提醒

1. **不要把管理页面直接裸露到公网。** 需要外网访问时，使用 HTTPS 反向代理，并保留管理员登录保护。
2. **不要把配置文件和会话发到群里或公开仓库。** `data/`、`sessions/`、Cookie、API Key、Bot Token 和备份文件都可能含有敏感信息。
3. **只安装可信插件。** 插件会在系统所在环境运行；查看源码、了解权限，比只看下载量更重要。
4. **更新前先备份。** 网页配置导出与完整目录备份不是一回事，详见[维护文档](Maintenance.md)。
5. **遇到错误先记录原始错误和时间。** 不要反复卸载、重装或删除数据来碰运气，先按[排查顺序](Troubleshooting.md)检查。

## 版本与反馈

- [项目主页与安装说明](https://github.com/AWdress/AWBotHub)
- [当前内置手册对应版本：v2.0.2.7](https://github.com/AWdress/AWBotHub/releases/tag/v2.0.2.7)
- [最新官方使用手册](https://github.com/AWdress/AWBotHub/blob/main/docs/guide/Home.md)
- [更新日志](https://github.com/AWdress/AWBotHub/blob/main/CHANGELOG.md)
- [提交问题](https://github.com/AWdress/AWBotHub/issues)

反馈时提供系统版本、服务器架构、部署方式、插件名称和出错时间。附日志或截图前，先隐藏密钥、手机号、Cookie、聊天内容和服务器私有地址。
