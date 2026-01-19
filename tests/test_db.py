# tests/test_db.py
import sqlite3
import os

def get_all_tables(conn):
    """取得資料庫中所有 table 名稱"""
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]
    return tables

def get_table_structure(conn, table_name):
    """取得 table 的欄位資訊"""
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name});")
    columns = cursor.fetchall()  # 每列: (cid, name, type, notnull, dflt_value, pk)
    return columns

def get_table_data(conn, table_name):
    """取得 table 的所有資料"""
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM {table_name}")
    rows = cursor.fetchall()
    return rows

if __name__ == "__main__":
    # 資料庫路徑
    db_path = os.path.join("instance", "eq_manage.db")

    if not os.path.exists(db_path):
        print(f"❌ 資料庫不存在: {db_path}")
    else:
        conn = sqlite3.connect(db_path)
        tables = get_all_tables(conn)

        print("📌 資料庫結構與資料內容：\n")
        for table in tables:
            print(f"Table: {table}")
            columns = get_table_structure(conn, table)
            col_names = [col[1] for col in columns]
            print("  欄位:", ", ".join(col_names))

            rows = get_table_data(conn, table)
            if rows:
                print(f"  ✅ 有 {len(rows)} 筆資料：")
                for row in rows:
                    print(f"    {row}")
            else:
                print("  ❌ 沒有資料")
            print("-" * 50)  # 分隔每個 table

        conn.close()
