import sqlite3

def execute_sql(db, q) -> tuple:
    try:
        return [], []
    except Exception as e:
        return None, f"error: {e}"
    finally:
        pass
    return None, None

def main():
    c, r = execute_sql("db", "q")

main()
