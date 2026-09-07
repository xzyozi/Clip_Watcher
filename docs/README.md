---
title: "ClipWatcher ドキュメント案内"
document_type: documentation_index
updated_at: 2026-09-07
---

# ClipWatcher ドキュメント案内

このページは、目的別に現行文書へ到達するための入口です。機能の現状を確認する際は、対象コードと現行の設計書を優先してください。過去の検討資料・レビューは、現行仕様の正本ではありません。

## 現行文書

| 目的                     | 場所                                                                       | 読者・用途                                             |
| :----------------------- | :------------------------------------------------------------------------- | :----------------------------------------------------- |
| プロジェクトの概要・導入 | [リポジトリREADME](../README.md) / [日本語README](../README.ja.md)         | 利用者・開発者の入口                                   |
| 基本・詳細設計           | [design/](design/)                                                         | 実装者が責務境界・仕様契約を確認する正本               |
| 開発環境・依存・Git・CI  | [setup/](setup/)                                                           | 開発者・保守者の手順                                   |
| Text Workflowルール作成  | [how-to/HOWTO_TEXT_WORKFLOW_RULES.md](how-to/HOWTO_TEXT_WORKFLOW_RULES.md) | Text Workflowの設定者                                  |
| 現行レビュー             | [review/](review/)                                                         | 保守性・UX・設計課題の確認                             |
| 過去レビュー             | [review/archive/](review/archive/)                                         | 過去の評価・判断経緯の参照                             |
| 過去の設計検討・提案     | [archive/](archive/)                                                       | 非現行資料の参照。再採用時は現行コードとの整合を再確認 |
| 設計書テンプレート       | [design/TEMPLATE/](design/TEMPLATE/)                                       | 新規設計書の作成                                       |

## 正本と互換案内

- 現行の基本設計・詳細設計は `docs/design/` を正本とします。個別の実装状況は対象コードで確認してください。
- `docs/` 直下とリポジトリ直下にある `compatibility_stub` 文書は、旧URLを維持するための案内です。仕様本文を更新せず、`canonical_source` が示す正本を更新してください。
- `docs/archive/` と `docs/review/archive/` は履歴資料です。現行の機能仕様・実装判断の根拠として単独では使用しません。

## Kiroの作業仕様

[`.kiro/specs/`](../.kiro/specs/) は、個別変更の requirements、design、tasks を管理するための作業記録です。製品・開発者向けの恒久ドキュメントは、原則として `docs/` に配置します。
