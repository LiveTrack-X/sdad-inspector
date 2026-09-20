![SDAD Inspector — Read-Only Control Plane for SPEC-Directed AI Development](web/public/sdad-inspector-banner.png)

> **语言：** [English](README.md) | [한국어](README.ko.md) | [日本語](README.ja.md) | **[简体中文](README.zh-CN.md)**

# SDAD Inspector

<!-- inspector-source-version -->Source version: `v3.2.4`<!-- /inspector-source-version -->

**本地源码候选：** Inspector `3.2.4` 与默认内置的 SDAD Protocol `3.2.4` 使用相同版本号。此候选尚未发布。以下下载说明针对已发布的 Inspector `0.0.5`，其中内置 SDAD `3.2.3`。请参阅[版本管理规则](docs/VERSIONING.md)及 [3.2.4 候选说明](docs/releases/v3.2.4.md)。

[![Cross-platform checks](https://github.com/LiveTrack-X/sdad-inspector/actions/workflows/cross-platform.yml/badge.svg)](https://github.com/LiveTrack-X/sdad-inspector/actions/workflows/cross-platform.yml)
[![Latest release](https://img.shields.io/github/v/release/LiveTrack-X/sdad-inspector?label=release)](https://github.com/LiveTrack-X/sdad-inspector/releases/latest)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Sponsor](https://img.shields.io/badge/Sponsor-LiveTrack--X-ea4aaa?logo=githubsponsors)](https://github.com/sponsors/LiveTrack-X)

SDAD Inspector 是一个本地桌面查看器，用来在一个界面中了解 SDAD 仓库的当前
状态。你无需逐个查找控制文件，就能看到规范依据、活动数据包、当前 TODO、发现项
以及每个值的来源。

被检查的仓库保持**只读**。Inspector 不执行项目声明的验证命令，也不修改源码、
SPEC、state、TODO 或 findings。设置、比较元数据及纠正草稿保存在 Inspector 专用
应用数据中，产品更新时也会替换便携式可执行文件。

> **0.0.5 是正式 GitHub Release，但仍未签名。** 它不是安装程序，也没有代码
> 签名或公证。运行前请核对 `SHA256SUMS`。如果组织策略不允许未签名软件，请不要
> 绕过系统保护，应改用源码运行方式。

> **发布版与源码：** `v0.0.5` 可执行文件由同一个 immutable 标签构建。只有
> Windows、macOS 和 Linux 的标签验证全部通过后，才会发布压缩包、校验和与
> attestation。

## 三分钟开始使用

目标电脑无需安装 Python 或 Node.js。每个压缩包只包含一个 **single portable
executable**，其中已经嵌入运行时、UI 和经过认证的 SDAD 3.2.3 引擎。

1. 打开 [`v0.0.5` Release](https://github.com/LiveTrack-X/sdad-inspector/releases/tag/v0.0.5)。
2. 下载适合当前电脑的压缩包和 `SHA256SUMS`。
3. 使用下面的命令验证 SHA-256。
4. 解压并运行其中唯一的可执行文件。
5. 出现提示时，选择包含 `sdad-state.yaml` 的项目根目录。

| 电脑 | 下载文件 | 压缩包内的可执行文件 |
| --- | --- | --- |
| Windows x64 | `SDAD-Inspector-0.0.5-windows-x64.zip` | `SDAD-Inspector.exe` |
| macOS Apple Silicon | `SDAD-Inspector-0.0.5-macos-arm64.tar.gz` | `SDAD-Inspector` |
| Linux x64 | `SDAD-Inspector-0.0.5-linux-x64.tar.gz` | `SDAD-Inspector` |

不要把表格以外的架构（例如 Intel Mac）视为已经通过公开发布验证。源码可能可以
运行，但这不等同于便携式发布资产已经完成构建和冒烟测试。

### 验证 SHA-256

Windows PowerShell：

```powershell
$archive = Get-Item .\SDAD-Inspector-0.0.5-windows-x64.zip
$expected = (Select-String .\SHA256SUMS -Pattern $archive.Name).Line.Split()[0]
$actual = (Get-FileHash $archive -Algorithm SHA256).Hash.ToLower()
$actual -eq $expected
```

最后一行必须显示 `True`。

macOS：

```bash
grep 'macos-arm64' SHA256SUMS | shasum -a 256 -c -
```

Linux：

```bash
grep 'linux-x64' SHA256SUMS | sha256sum -c -
```

如果 macOS/Linux 提示没有执行权限，只为解压出的程序添加权限：

```bash
chmod +x ./SDAD-Inspector
./SDAD-Inspector /path/to/your-project
```

## 启动与选择项目

当前源码会先打开 Inspector 界面，而不是一启动就弹出系统文件夹选择器。如果以前
打开过的最新项目仍然存在，程序会自动加载它。首次运行时，GUI 加载完成后会显示
应用内项目选择窗口；只有点击**浏览**才会打开操作系统的文件夹选择器。之后可随时
使用顶部的文件夹按钮切换项目。

## 如何阅读界面

![SDAD Inspector 界面：左侧仓库导航，中间活动数据包和 TODO，右侧字段来源](docs/assets/sdad-inspector-overview-ko.png)

这张公开截图使用不含个人路径和内部运营文档的合成 SDAD 3.2.3 fixture。右上角
语言菜单可以切换 English、한국어、日本語和简体中文。主题和 UI 缩放比例会保存到
Inspector 自己的用户设置中。

- **命令栏** — 显示项目和引擎，并提供手动/AUTO 15 秒重新检查、在文件夹中显示、
  复制路径、语言、主题和 90–150% UI 缩放。默认 110%，也支持 `Ctrl/Cmd` +
  `+`、`-`、`0`。
- **左侧面板** — 打开 state、Active SPEC、Active Packet、TODO、官方控制循环、
  routed documents 和 findings。
- **中间面板** — 显示数据包目标和状态、当前 TODO、其他未完成/已完成 TODO、Git
  观察信息和 handoff。
- **右侧面板** — 说明所选值的权限依据、观察值、原始路径、检查时间、相关 finding
  和安全的只读操作。
- **证据文档** — 在元数据下方直接显示受大小限制的正文。JSON、YAML 和 Markdown
  不会被执行，并保留原始语言。

官方循环为 `Plan → Route → Implement → Verify → Report`。只有活动数据包中未完成的
TODO 同时带有 `[current]` 和有效 `[phase:…]` 时，界面才突出当前阶段。当前 TODO
单独显示，因此下面的 `0` 表示“其他剩余工作为 0”，并不表示没有检测到当前 TODO。

## 可检查哪些 SDAD 项目

默认目标是 [SDAD Protocol](https://github.com/LiveTrack-X/spec-driven-ai-development)
`v3.2.4`。这是当前源码候选的默认值，已发布的 0.0.5 仍内置 3.2.3。
从源码检查项目时，仍可明确选择受支持的旧引擎。

| 契约 | 3.2.4 源码候选范围 |
| --- | --- |
| 内置运行基准 | Official SDAD Protocol `v3.2.4` |
| 默认适配器 | `official-sdad-3` |
| Doctor fixture | `v3.2.1`, `v3.2.2`, `v3.2.3`, `v3.2.4` |
| state schema | 1, 2 |
| Doctor report schema | 1, 2 |
| Inspector snapshot schema | 2 |

兼容项目需要在根目录提供 `sdad-state.yaml`，并让其中的 `active_spec` 指向可读取的
规范。引擎规则位于 `ProtocolAdapter` 边界中，与 Inspector UI 分离。其他 SDAD
变体可以通过由应用注册的受信任适配器接入；Inspector 不会从被检查的仓库加载代码。

## 自动产品更新

便携式应用会在启动时以及每六小时检查固定的 GitHub Releases。程序只接受比当前
版本更新、已经发布且 immutable 的 Release，并验证精确匹配 OS/架构的资产、GitHub
SHA-256 digest、大小、下载主机以及压缩包内唯一的预期文件，然后才在后台替换自身。

新程序成功启动后，经过认证的 UI 会确认一次成功 handoff，并删除与当前可执行文件
精确匹配的 `.previous` 备份和成功标记。完成通知可以手动关闭，也会自动消失。替换
失败时会尽可能恢复旧文件，并阻止自动重试循环。新可执行文件包含该版本声明的
内置引擎；此功能不会单独下载引擎，也不写入被检查的项目。

## 从源码运行

需要 Python 3.10+ 和 Node.js 22+。发布用 one-file 构建强制使用 CPython 3.12，
并要求认证引擎与产品版本一致。

```bash
python -m venv .venv
python -m pip install -e ".[desktop,build]"
npm --prefix web ci
npm --prefix web run build
sdad-inspector desktop --sdad-checkout .runtime/sdad-v3.2.4
```

省略项目路径时，程序会重新打开最新的有效项目；如果没有历史记录，则在 GUI 中
显示首次运行选择窗口。也可以明确传入路径：

```bash
sdad-inspector desktop /path/to/your-project --sdad-checkout .runtime/sdad-v3.2.4
```

主要验证命令：

```bash
python scripts/validate_public_repository.py
python scripts/validate_release.py
python -m unittest discover -s tests -v
npm --prefix web run typecheck
npm --prefix web test -- --run
npm --prefix web run build
python scripts/validate_browser_contract.py --sdad-checkout .runtime/sdad-v3.2.4
python scripts/validate_native_contract.py --sdad-checkout .runtime/sdad-v3.2.4
```

## 后续发布维护

当前源码以 `sdad_inspector/version.py` 为唯一版本来源。以后获准修改版本时，运行
`python scripts/release_metadata.py --sync` 只更新 Windows 资源及 README 中受管理的
源码版本行，并使用 `--check` 检查一致性。已发布的下载链接和历史说明不会被改写。
共同版本号与各产品独立的发布条件见[版本管理规则](docs/VERSIONING.md)。

下一次获准发布时，标签工作流会选择与标签提交完全一致的 `main` 验证候选，检查
版本和压缩包哈希，并再次执行三个平台的下载后启动检查。程序不会重新构建；
发布内容为三个平台压缩包、`SHA256SUMS` 和记录候选来源的 manifest，共五个资产，
并附有 attestation。已有标签和 Release 不会被替换。候选保存三天，详细流程见
[发布维护说明](docs/RELEASING.md)及[跨平台契约](docs/CROSS_PLATFORM.md)。

发布 3.2.4 候选需要该候选自己的授权托管验证。已发布的 `v0.0.5` 压缩包
及其历史验证结果保持不变。

## 当前限制

- 没有安装程序、代码签名、公证或稳定版支持保证。
- Windows 仍需要 WebView2；Linux 仍需要操作系统提供必要的显示/WebKit 库。
- one-file 启动时会把嵌入的运行时解压到操作系统临时目录。
- CI 结果只证明精确资产和 runner 环境，不能保证每一台实体电脑。
- Inspector 不是 SDAD 编辑器或自主修复工具。

## 许可证与赞助

SDAD Inspector 采用 [MIT License](LICENSE)。如果项目对你有帮助，可以通过
[GitHub Sponsors](https://github.com/sponsors/LiveTrack-X) 支持持续维护。赞助不会
改变许可证、支持范围或发布证据。

报告问题时，请提供 Inspector 版本、OS/架构、SDAD 版本、Doctor exit code 和复现
步骤。请勿附加 `.env`、客户数据、私有仓库内容或其他秘密信息。

[纠正历史与草稿恢复](docs/CORRECTION_HISTORY.md)（英文）说明 0.0.5 已包含的
应用专用归档、恢复及来源位置变化后的草稿恢复。3.2.4 候选改进了 TODO 分组、
对两个选定验证记录的明确比较，以及尚无恢复基准时的说明。
