import json
import os
import sqlite3
import sys
import time


def categorize_phrase(text: str) -> str:
    text_lower = text.lower()

    # 1. Business / Mail
    business_keywords = [
        "お世話になっております",
        "お疲れ様です",
        "株式会社",
        "よろしくお願いいたします",
        "ご担当者様",
        "拝啓",
        "敬具",
    ]
    if any(k in text_lower for k in business_keywords):
        return "Business / Mail"

    # 2. Prompts (Image Gen)
    prompt_tags = [
        "1girl",
        "2girls",
        "boy",
        "hair",
        "eyes",
        "face",
        "nsfw",
        "masterpiece",
        "best quality",
        "docking",
        "breast",
    ]
    # カンマが3つ以上あり改行がない、またはカンマが5つ以上ある、または特定のプロンプトタグが含まれる
    has_many_commas = (text_lower.count(",") >= 3 and "\n" not in text_lower) or (
        text_lower.count(",") >= 5
    )
    has_prompt_tags = any(tag in text_lower for tag in prompt_tags)

    if has_many_commas or has_prompt_tags:
        return "Prompts"

    # 3. Development / IT
    dev_keywords = [
        "python",
        "bug",
        "実装",
        "エラー",
        "スクリプト",
        "def ",
        "class ",
        "git ",
        "http",
    ]
    if any(k in text_lower for k in dev_keywords):
        return "Development / IT"

    # 4. Finance
    finance_keywords = ["ロット", "fx", "スプレッド", "手数料", "口座", "通貨", "pips"]
    if any(k in text_lower for k in finance_keywords):
        return "Finance"

    return "General / Memo"


def get_db_path():
    app_data_dir = os.path.join(
        os.environ.get("USERPROFILE", os.path.expanduser("~")), ".clipWatcher"
    )
    return os.path.join(app_data_dir, "clip_watcher.db")


def main():
    json_path = "fixed_phrases.json"
    if not os.path.exists(json_path):
        print(f"Error: {json_path} not found.")
        sys.exit(1)

    db_path = get_db_path()
    if not os.path.exists(db_path):
        print(f"Error: Database not found at {db_path}")
        sys.exit(1)

    print(f"Loading data from {json_path}...")
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        print("Error: JSON root is not a list.")
        sys.exit(1)

    print(f"Found {len(data)} phrases. Starting migration to {db_path}...")

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    cursor = conn.cursor()

    try:
        conn.execute("BEGIN TRANSACTION")

        # 既存カテゴリのキャッシュ (name -> id)
        cursor.execute("SELECT name, id FROM t_category")
        category_cache = {row[0]: row[1] for row in cursor.fetchall()}

        # 次の sort_order (カテゴリ用)
        cursor.execute("SELECT COALESCE(MAX(sort_order), -1) + 1 FROM t_category")
        next_cat_sort_order = cursor.fetchone()[0]

        # カテゴリごとの次の sort_order (フレーズ用)
        phrase_sort_orders = {}
        for cat_id in category_cache.values():
            cursor.execute(
                "SELECT COALESCE(MAX(sort_order), -1) + 1 FROM t_meta_phrase WHERE category_id = ?",
                (cat_id,),
            )
            phrase_sort_orders[cat_id] = cursor.fetchone()[0]

        migrated_count = 0
        for item in data:
            if not isinstance(item, str) or not item.strip():
                continue

            content = item.strip()
            category_name = categorize_phrase(content)

            # カテゴリが存在しなければ作成
            if category_name not in category_cache:
                cursor.execute(
                    "INSERT INTO t_category (name, sort_order) VALUES (?, ?)",
                    (category_name, next_cat_sort_order),
                )
                new_cat_id = cursor.lastrowid
                category_cache[category_name] = new_cat_id
                phrase_sort_orders[new_cat_id] = 0
                next_cat_sort_order += 1

            cat_id = category_cache[category_name]

            # titleの生成
            first_line = content.split("\n")[0]
            title = first_line[:25] + ("..." if len(first_line) > 25 else "")
            if not title:
                title = "Untitled"

            created_at = time.time()
            sort_order = phrase_sort_orders[cat_id]

            cursor.execute(
                "INSERT INTO t_meta_phrase (title, content, category_id, sort_order, created_at) VALUES (?, ?, ?, ?, ?)",
                (title, content, cat_id, sort_order, created_at),
            )
            phrase_sort_orders[cat_id] += 1
            migrated_count += 1

        conn.commit()
        print(f"Migration completed successfully. Migrated {migrated_count} phrases.")

        # Rename original file as backup
        backup_path = json_path + ".bak"
        if os.path.exists(backup_path):
            os.remove(backup_path)
        os.rename(json_path, backup_path)
        print(f"Backed up original JSON to {backup_path}")

    except Exception as e:
        conn.rollback()
        print(f"Migration failed and rolled back: {e}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
