![SDAD Inspector — Read-Only Control Plane for SPEC-Directed AI Development](web/public/sdad-inspector-banner.png)

> **言語:** [English](README.md) | [한국어](README.ko.md) | **[日本語](README.ja.md)** | [简体中文](README.zh-CN.md)

# SDAD Inspector

[![Cross-platform checks](https://github.com/LiveTrack-X/sdad-inspector/actions/workflows/cross-platform.yml/badge.svg)](https://github.com/LiveTrack-X/sdad-inspector/actions/workflows/cross-platform.yml)
[![Latest release](https://img.shields.io/github/v/release/LiveTrack-X/sdad-inspector?label=release)](https://github.com/LiveTrack-X/sdad-inspector/releases/latest)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Sponsor](https://img.shields.io/badge/Sponsor-LiveTrack--X-ea4aaa?logo=githubsponsors)](https://github.com/sponsors/LiveTrack-X)

SDAD Inspector は、SDAD リポジトリの「いま」を一つの画面で確認するための
ローカル・デスクトップビューアーです。基準となる SPEC、アクティブなパケット、
現在の TODO、検出事項、証拠の出所を、管理ファイルを一つずつ探さずに読めます。

検査対象のリポジトリは **読み取り専用** です。Inspector は、プロジェクトが
宣言した検証コマンドを実行せず、ソース、SPEC、state、TODO、findings を変更
しません。書き込みは Inspector 自身の設定、更新用データ、更新対象のポータブル
実行ファイルに限定されます。

> **0.0.3 は通常の GitHub Release ですが、未署名です。** インストーラーでは
> なく、コード署名と notarization はありません。実行前に `SHA256SUMS` を確認
> してください。組織のポリシーが未署名ソフトウェアを禁止する場合は、保護を
> 回避せず、ソースから実行してください。

> **リリースとソース:** `v0.0.3` の実行ファイルは同じ immutable タグから
> ビルドされます。Windows、macOS、Linux のタグ検証がすべて成功した後にのみ、
> アーカイブ、チェックサム、attestation を公開します。

## 3 分で始める

配布先のコンピューターに Python や Node.js をインストールする必要はありません。
各アーカイブには、ランタイム、UI、認証済み SDAD 3.2.2 エンジンを含む
**single portable executable** が一つだけ入っています。

1. [`v0.0.3` Release](https://github.com/LiveTrack-X/sdad-inspector/releases/tag/v0.0.3) を開きます。
2. 自分の環境用アーカイブと `SHA256SUMS` をダウンロードします。
3. 下記のコマンドで SHA-256 を確認します。
4. 展開して、唯一の実行ファイルを起動します。
5. 案内が表示されたら、`sdad-state.yaml` を含むプロジェクトルートを選びます。

| 環境 | ダウンロード | アーカイブ内の実行ファイル |
| --- | --- | --- |
| Windows x64 | `SDAD-Inspector-0.0.3-windows-x64.zip` | `SDAD-Inspector.exe` |
| macOS Apple Silicon | `SDAD-Inspector-0.0.3-macos-arm64.tar.gz` | `SDAD-Inspector` |
| Linux x64 | `SDAD-Inspector-0.0.3-linux-x64.tar.gz` | `SDAD-Inspector` |

Intel Mac など表にないアーキテクチャは、公開アセットとして検証済みとは主張
しません。ソース実行が可能でも、配布アセットのビルドとスモークテストの証拠とは
別です。

### SHA-256 の確認

Windows PowerShell:

```powershell
$archive = Get-Item .\SDAD-Inspector-0.0.3-windows-x64.zip
$expected = (Select-String .\SHA256SUMS -Pattern $archive.Name).Line.Split()[0]
$actual = (Get-FileHash $archive -Algorithm SHA256).Hash.ToLower()
$actual -eq $expected
```

最後の値が `True` であることを確認します。

macOS:

```bash
grep 'macos-arm64' SHA256SUMS | shasum -a 256 -c -
```

Linux:

```bash
grep 'linux-x64' SHA256SUMS | sha256sum -c -
```

macOS/Linux で実行権限がない場合は、展開した実行ファイルだけに権限を付けます。

```bash
chmod +x ./SDAD-Inspector
./SDAD-Inspector /path/to/your-project
```

## 起動とプロジェクト選択

現在のソースでは、ネイティブのフォルダー選択画面より先に Inspector の GUI が
開きます。以前開いた有効なプロジェクトがあれば最新のものを自動的に読み込みます。
初回起動では GUI 内のプロジェクト選択画面を表示し、**参照**を押した場合だけ
OS のフォルダー選択画面を開きます。上部のフォルダー操作からいつでも切り替え
られます。

## 画面の見方

![左にリポジトリナビゲーション、中央にアクティブパケットと TODO、右に証拠の出所を表示する SDAD Inspector](docs/assets/sdad-inspector-overview-ko.png)

この公開スクリーンショットは、個人パスや内部運用文書を含まない合成 SDAD 3.2.2
fixture を使用しています。上部の言語メニューでは English、한국어、日本語、
简体中文を選べます。テーマと UI サイズは Inspector 専用のユーザー設定に保存
されます。

- **コマンドバー** — プロジェクトとエンジン、手動/AUTO 15 秒再検査、フォルダー
  表示、パスコピー、言語、テーマ、90–150% UI ズームを操作します。既定は 110%
  で、`Ctrl/Cmd` + `+`、`-`、`0` も使えます。
- **左ペイン** — state、Active SPEC、Active Packet、TODO、公式制御ループ、
  routed documents、findings を開きます。
- **中央ペイン** — パケットの目標と状態、現在の TODO、その他の未完了/完了 TODO、
  Git の観測情報、handoff を表示します。
- **右ペイン** — 選択値の権限根拠、観測値、元パス、検査時刻、関連 finding と
  安全な読み取り操作を示します。
- **証拠文書** — メタデータの下に、サイズ制限された本文を直接表示します。
  JSON、YAML、Markdown は実行されず、元の言語のまま保持されます。

公式ループは `Plan → Route → Implement → Verify → Report` です。現在の段階は、
アクティブパケットの開いた TODO に `[current]` と有効な `[phase:…]` がある場合だけ
強調します。現在の TODO は別枠で表示されるため、その下の `0` は「現在の TODO が
ない」ではなく「その他の残り作業が 0」を意味します。

## 対応する SDAD

標準の対象は [SDAD Protocol](https://github.com/LiveTrack-X/spec-driven-ai-development)
`v3.2.2` です。

| 契約 | 0.0.3 の範囲 |
| --- | --- |
| バンドル実行基準 | Official SDAD Protocol `v3.2.2` |
| 既定アダプター | `official-sdad-3` |
| Doctor fixture | `v3.2.1`, `v3.2.2` |
| state schema | 1, 2 |
| Doctor report schema | 1, 2 |
| Inspector snapshot schema | 2 |

互換プロジェクトには、ルートの `sdad-state.yaml` と、そこから参照される読み取り
可能な `active_spec` が必要です。エンジン規則は `ProtocolAdapter` の境界にあり、
Inspector UI とは分離されています。別の SDAD 派生仕様は、信頼できるアダプターを
アプリ側で登録して対応します。検査対象リポジトリからコードをロードすることは
ありません。

## 自動製品更新

ポータブルアプリは、起動時と 6 時間ごとに固定の GitHub Releases を確認します。
現在より新しい公開済み immutable release、正しい OS/アーキテクチャ資産、GitHub
SHA-256 digest、サイズ、ホスト、アーカイブ内の単一ファイルを検証してから、
バックグラウンドで置換します。

新しいアプリが正常に起動すると、認証済み UI が成功 handoff を一度だけ確認し、
正確に対応する `.previous` バックアップと成功マーカーを削除します。完了通知は
閉じることができ、自動でも消えます。失敗時は可能な範囲で以前の実行ファイルを
復元し、自動再試行ループを停止します。SDAD エンジンと検査対象プロジェクトは
更新しません。

## ソースから実行

Python 3.10 以上と Node.js 22 以上を使用します。リリース用 one-file ビルドだけは
CPython 3.12 が必須です。

```bash
python -m venv .venv
python -m pip install -e ".[desktop,build]"
npm --prefix web ci
npm --prefix web run build
sdad-inspector desktop --sdad-checkout .runtime/sdad-v3.2.2
```

プロジェクトパスを省略すると、最新の有効な履歴を開くか、初回用のアプリ内
選択画面を表示します。明示する場合:

```bash
sdad-inspector desktop /path/to/your-project --sdad-checkout .runtime/sdad-v3.2.2
```

主要な検証:

```bash
python scripts/validate_public_repository.py
python scripts/validate_release.py
python -m unittest discover -s tests -v
npm --prefix web run typecheck
npm --prefix web test -- --run
npm --prefix web run build
python scripts/validate_browser_contract.py --sdad-checkout .runtime/sdad-v3.2.2
python scripts/validate_native_contract.py --sdad-checkout .runtime/sdad-v3.2.2
```

## 制限

- インストーラー、コード署名、notarization、安定版サポート保証はありません。
- Windows では WebView2、Linux では必要な表示/WebKit ライブラリが OS 側に必要です。
- one-file 起動時は埋め込みランタイムを OS の一時ディレクトリに展開します。
- CI の結果は正確なアセットと runner の証拠であり、すべての物理 PC を保証しません。
- Inspector は SDAD エディターや自律修復ツールではありません。

## ライセンスとスポンサー

SDAD Inspector は [MIT License](LICENSE) で提供されます。継続的なメンテナンスは
[GitHub Sponsors](https://github.com/sponsors/LiveTrack-X) から支援できます。
スポンサーの有無によって、ライセンス、サポート範囲、リリース証拠は変わりません。

問題を報告するときは、Inspector のバージョン、OS/アーキテクチャ、SDAD
バージョン、Doctor exit code、再現手順を含めてください。`.env`、顧客データ、
非公開リポジトリの内容、その他の秘密情報は添付しないでください。
