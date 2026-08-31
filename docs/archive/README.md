---
document_type: archive
status: archived
archived_at: 2026-08-31
current_authority: "現行コードおよびdocs/design/"
reason: "過去の設計検討・移行案・将来提案への索引を保存するため"
---

# アーカイブ資料

このディレクトリには、過去の設計検討、移行案、将来提案を保存します。アーカイブ資料は意思決定の経緯を確認するための記録であり、現行の機能仕様または実装の正本ではありません。

現行仕様を確認する場合は、次のコードと現行文書を優先してください。

| 対象                 | 正本                                        |
| :------------------- | :------------------------------------------ |
| SQLiteのDDL・DAO     | `src/db/database_manager.py`、`src/db/dao/` |
| グローバルホットキー | `src/core/hotkey/`                          |
| Text Workflow        | `src/core/text_workflow/`                   |

| 資料                                                           | 分類                                   |
| :------------------------------------------------------------- | :------------------------------------- |
| `DB_BASE.md` / `META_MANAGEMENT_DESIGN.md`                     | SQLite移行・データベース設計の検討記録 |
| `HISTORY_PERSISTENCE_INVESTIGATION.md`                         | 履歴保存・初期表示に関する調査記録     |
| `I18N_APPROACHES.md` / `REUSABLE_GUI_MODULES.md`               | 国際化・GUI構成の技術整理              |
| `INVESTIGATION_QUICK_TASK_AND_MULTI_INSTANCE.md`               | クイックタスク・多重起動の機能提案調査 |
| `EXTENSIBILITY_PROPOSAL_STD_LIB.md` / `PLUGIN_ARCHITECTURE.md` | 拡張機能・プラグインに関する未実装提案 |
| `NETWORK_API_IMPLEMENTATION.md`                                | Network APIの未採用実装提案            |

アーカイブ内の提案を実装・再採用する場合は、現行コードとの整合性、セキュリティ、必要な要件を改めて確認してください。