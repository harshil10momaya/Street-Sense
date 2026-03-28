"""Quick test: can we connect to PostgreSQL?"""
import psycopg2

try:
    conn = psycopg2.connect(
        host="127.0.0.1",
        port=5432,
        dbname="streetsense_db",
        user="streetsense",
        password="streetsense_pass",
    )
    cur = conn.cursor()
    cur.execute("SELECT version();")
    version = cur.fetchone()[0]
    print(f"[OK] Connected! PostgreSQL: {version[:50]}...")
    cur.close()
    conn.close()
except Exception as e:
    print(f"[FAIL] {e}")
