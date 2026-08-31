---
document_type: operation
updated_at: 2026-08-31
canonical_source: .github/workflows/branch-cleanup.yml, .github/workflows/ci.yml
---

# Git Flow 運用規約 ＆ ブランチ自動管理ガイド

本書は Git Flow の運用ルールと、リポジトリに定義された CI・ブランチクリーンアップの実態を定義します。

## 1. ブランチ戦略

| 種別                | 用途                       | 分岐元・マージ先                               |
| :------------------ | :------------------------- | :--------------------------------------------- |
| `main`              | 本番環境用の安定ブランチ   | 長期維持                                       |
| `develop`           | 開発成果を集約するブランチ | 長期維持                                       |
| `feat/<機能名>`     | 新機能開発                 | `develop` から分岐し、PR で `develop` へマージ |
| `fix/<修正内容>`    | バグ修正                   | `develop` から分岐し、PR で `develop` へマージ |
| `docs/<文書名>`     | 文書更新                   | 対応する変更先へ PR でマージ                   |
| `hotfix/<緊急修正>` | 本番障害の緊急修正         | `main` から分岐し、`main` と `develop` へ反映  |

## 2. CI とリモートの自動管理

### 2.1 CI

[ci.yml](../../.github/workflows/ci.yml) は `main` と `develop` への push、および両ブランチを対象とする PR で起動します。`windows-latest` 上で依存を導入し、Ruff の lint・format check、Mypy、Pytest を実行します。CI の必須設定や保護ルールは GitHub 側の設定に依存するため、本書だけで有効化を保証しません。

### 2.2 マージ済みリモートブランチのクリーンアップ

[branch-cleanup.yml](../../.github/workflows/branch-cleanup.yml) は毎週月曜 00:00 UTC と手動実行で起動します。`origin/develop` にマージ済みのリモートブランチを調べ、`main`、`develop`、`HEAD` を保護して、それ以外のブランチを削除します。`origin/main` へのマージだけでは削除対象になりません。

GitHub の **Automatically delete head branches** はリポジトリ設定です。利用する場合は GitHub の `Settings` > `General` > `Pull Requests` で有効化してください。ワークフローの動作とは独立しているため、設定状態は GitHub 管理画面で確認します。

## 3. ローカル追跡ブランチの整理

### 3.1 自動 prune

リモートで削除された追跡情報を更新時に取り除くには、次を一度実行します。

```powershell
git config --global fetch.prune true
```

### 3.2 Git Bash の一括削除エイリアス

次のエイリアスは `grep`、`awk`、`xargs` を使用するため、**Git Bash 専用**です。Windows PowerShell 共通のコマンドではありません。

```bash
git config --global alias.cleanup "!git branch -vv | grep '\[gone\]' | awk '{print $1}' | xargs -r git branch -d"
git cleanup
```

### 3.3 Windows PowerShell の安全な代替手順

Windows PowerShell では、POSIX ツールに依存せず、まず削除候補だけを表示して確認します。

```powershell
git fetch --prune
$goneBranches = git for-each-ref --format="%(refname:short)|%(upstream:track)" refs/heads |
    Where-Object { $_ -match "\|\[gone\]$" } |
    ForEach-Object { ($_ -split "\|", 2)[0] }
$goneBranches
```

表示内容を確認して削除してよい場合だけ、`DELETE` と入力します。`git branch -d` は未マージのブランチを削除しません。

```powershell
if ((Read-Host "表示したブランチを削除する場合は DELETE と入力") -eq "DELETE") {
    $goneBranches | ForEach-Object { git branch -d $_ }
}
```

## 改訂履歴

| 日付       | 変更内容                                                                                                                                         |
| :--------- | :----------------------------------------------------------------------------------------------------------------------------------------------- |
| 2026-08-31 | 軽量メタデータと改訂履歴を追加。現行 CI・週次クリーンアップの対象を明記し、Git Bash 専用エイリアスと Windows PowerShell の安全な代替手順を分離。 |
