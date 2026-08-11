# How-To: Text Workflow 分類ルールの作成・設定ガイド

本ガイドでは、`TextWorkflow` 基盤において入力テキスト（クリップボードの内容や明示的テキスト）を「議事録」「コード」「URL」等へ自動判別・分類するためのルール (`rules.json`) の作成方法を解説します。

---

## 1. ルール設定ファイルの基本構造

分類ルールは JSON 形式で定義します。設定は優先度 (`priority`) に従位して上から順に評価され、**最初にマッチしたルール**のカテゴリおよびテンプレートが適用されます。

```json
{
  "schemaVersion": 1,
  "rules": [
    {
      "id": "rule-meeting-notes",
      "enabled": true,
      "priority": 10,
      "categoryId": "meeting",
      "templateId": "meeting-summary",
      "normalizationProfile": "plain",
      "tags": ["meeting", "work"],
      "when": {
        "all": [
          { "kind": "containsAny", "values": ["議事録", "MTGノート", "打ち合わせメモ"] },
          { "kind": "containsAny", "values": ["日時", "参加者", "決定事項", "アジェンダ"] }
        ]
      }
    }
  ]
}
```

---

## 2. 条件指定 (`when`) の構文一覧

判別に使用できる条件 (`kind`) と論理結合 (`all`, `any`, `not`) の一覧です。

| 条件 (`kind`) | 説明 | 設定例 |
| :--- | :--- | :--- |
| `contains` | 指定した文字列が**全て**含まれる | `{ "kind": "contains", "value": "議事録" }` |
| `containsAny` | 指定した配列の文字列の**いずれか**が含まれる | `{ "kind": "containsAny", "values": ["議事録", "MTG"] }` |
| `regex` | 正規表現にマッチする | `{ "kind": "regex", "pattern": "^https?://" }` |
| `minLength` | テキストの文字数が指定以上 | `{ "kind": "minLength", "value": 50 }` |
| `maxLength` | テキストの文字数が指定以下 | `{ "kind": "maxLength", "value": 1000 }` |

### 論理結合のルール
- `"all": [ ... ]`: 配列内の条件を**すべて**満たす場合 (AND)
- `"any": [ ... ]`: 配列内の条件のうち**1つ以上**を満たす場合 (OR)
- `"not": { ... }`: 条件を**満たさない**場合 (NOT)

---

## 3. 実践例 (ケース別 How-To)

### ケース 1: 「議事録」を自動判別したい場合

**判別ロジック:**
1. タイトルや本文に「議事録」「MTG」「打ち合わせ」などの言葉が含まれる。
2. かつ「日時」「参加者」「決定事項」などの見出し構成が含まれている。

```json
{
  "id": "rule-meeting-notes",
  "priority": 10,
  "categoryId": "meeting",
  "templateId": "meeting-summary",
  "when": {
    "all": [
      { "kind": "containsAny", "values": ["議事録", "MTGメモ", "打ち合わせ"] },
      { "kind": "containsAny", "values": ["日時", "参加者", "アジェンダ", "決定事項", "ToDo"] }
    ]
  }
}
```

---

### ケース 2: 「URL / Webリンク」を自動判別したい場合

**判別ロジック:**
1. テキストが `http://` または `https://` で始まっている。
2. 改行を含まない短めの文字列である。

```json
{
  "id": "rule-url-link",
  "priority": 5,
  "categoryId": "url",
  "templateId": "url-bookmark",
  "when": {
    "all": [
      { "kind": "regex", "pattern": "^https?://\\S+$" },
      { "kind": "maxLength", "value": 2083 }
    ]
  }
}
```

---

### ケース 3: 「Pythonの例外スタックトレース / エラーログ」を自動判別したい場合

**判別ロジック:**
1. `Traceback (most recent call last):` という行が含まれる。

```json
{
  "id": "rule-python-traceback",
  "priority": 20,
  "categoryId": "error_log",
  "templateId": "formatted-code-block",
  "when": {
    "contains": "Traceback (most recent call last):"
  }
}
```

---

## 4. ルール設計のコツと注意事項

1. **特定ルールを優先する (`priority` の設計)**:
   - より厳密な判定ルール（例: エラーログや特定URL）は `priority: 5` などの小さい数値を設定して先に評価させます。
   - 一般的なキーワード判定（例: 一般メモ）は `priority: 100` など大きめの数値を指定します。
2. **ReDoS (正規表現の負荷) に注意する**:
   - `regex` を使う場合は `.*.*` のような複雑で重い評価になるパターンを避け、単純なパターンを設定します。
3. **デフォルトカテゴリ (`defaultCategory`) の活用**:
   - どのルールにも合致しなかった場合は `general` 等のデフォルトカテゴリが割り当てられます。
