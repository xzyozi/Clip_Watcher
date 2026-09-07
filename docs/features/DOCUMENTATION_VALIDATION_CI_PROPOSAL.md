---
title: "文書検証CI導入提案"
document_type: feature_proposal
status: proposed
created_at: 2026-09-07
updated_at: 2026-09-07
---

# 文書検証CI導入提案

> **状態:** 提案のみ。検証スクリプト、GitHub Actionsワークフロー、依存関係は未追加です。

## 目的

文書の移動・改名・正本差し替えで、相対リンク、互換案内、文字コードが壊れることをプルリクエスト時点で検出する。

## 導入する検証

1. `README.md`、`README.ja.md`、`docs/**/*.md` のUTF-8（BOMなし）・LF・末尾空白を検証する。
2. Markdownの未閉鎖コードフェンスと、リポジトリ内を指す相対リンク切れを検証する。
3. `compatibility_stub` の `canonical_source` が存在し、別の互換スタブやアーカイブを正本として指していないことを検証する。
4. `docs/README.md`、`docs/review/README.md`、`docs/archive/README.md` の存在を検証する。

外部URLへのアクセス、`.kiro/specs/` の検証、既存のMermaid描画検証の置換は対象外とする。

## 実装構成

```text
.github/scripts/validate_docs.py
.github/workflows/validate-docs.yml
```

検証スクリプトはPython標準ライブラリだけで実装する。ワークフローは文書・検証スクリプト・Git属性の変更時だけ起動し、既存の `ci.yml` と `validate-mermaid.yml` とは独立して実行する。

## 導入手順

1. ローカル実行で既存文書を監査し、既存違反を解消する。
2. `validate_docs.py` と専用ワークフローを追加する。
3. プルリクエストと `main` / `develop` へのpushで必須チェックとして有効化する。
4. frontmatter要件は新規・大規模更新文書から段階的に強化する。

## 完了条件

- 文書変更を含むプルリクエストで検証が実行される。
- 相対リンク切れ、CRLF、BOM、末尾空白、壊れた正本参照でCIが失敗する。
- Mermaid図は既存の `validate-mermaid.yml` で引き続き検証される。
