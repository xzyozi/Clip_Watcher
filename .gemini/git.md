# Git Commit Message Conventions

このプロジェクトのコミットメッセージの規約です。一貫性のある分かりやすい履歴を保つため、この規約に従ってください。

---

## フォーマット

コミットメッセージは以下の形式で記述します。
また基本的に日本語での記述とします。
ただしtypeに関しては英語で行う。
```
<type>: <subject>
```

### 例
```
add : Alembic version script
update : refactored the structure to switch between multiple screens
```

---

## 1. Type (接頭辞)

コミットで行った変更の種類を示す接頭辞です。必ず以下のいずれかを使用してください。

- **add**: 新機能や新規ファイルの追加
- **update**: 既存機能の更新・改善
- **fix**: バグ修正
- **refactor**: バグ修正や機能追加を伴わないコードのリファクタリング
- **remake**: 大規模なリファクタリングや機能の作り直し
- **clean**: 不要なコードやファイルの整理
- **delete**: ファイルや機能の削除 (`del` も使用可)
- **docs**: ドキュメントのみの変更
- **style**: コードの意味に影響しないスタイルの変更（空白、フォーマットなど）
- **test**: テストの追加・修正
- **chore**: ビルドプロセスや補助ツール、ライブラリの変更など
- **WIP**: 作業の途中経過 (Work In Progress)

## 2. Subject (要約)

変更内容の簡潔な要約です。

- **英語**で記述します。
- **小文字**で書き始めます。
- 文末にピリオドは不要です。

---

## 3. 本文 (Body) のルール

### `fix` コミットの詳細

バグ修正 (`fix`) の場合は、コミットの本文（2行目以降）に以下の情報を含めることを推奨します。これにより、どのようなバグがなぜ修正されたのかが明確になります。

**フォーマット:**
```
fix: [修正内容の要約]

Problem:
[どのような問題（バグ）があったかを簡潔に説明]

Solution:
[どのように問題を解決したかを簡潔に説明]

Closes #[イシュー番号]
```

**具体例:**
```
fix: correct user login error

Problem:
Users were unable to log in if their password contained special characters.

Solution:
Added proper decoding middleware to the authentication route.

Closes #42
```
> `Closes #[番号]` と記述すると、このコミットが `main` ブランチにマージされた際に、関連するGitHub Issueを自動で閉じることができます。

---

## 良い例

```
add : database setup script
update : screen transition logic
fix : typo in error message
docs : update alembic command guide
```