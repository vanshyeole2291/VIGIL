import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sqlalchemy import text
from backend.database import engine, DATABASE_URL, DB_PATH

def migrate():
    print(f"Checking database at: {DB_PATH}")
    with engine.connect() as conn:
        try:
            res = conn.execute(text("PRAGMA table_info(incidents)"))
            cols = [row[1] for row in res.fetchall()]
            print("Incidents columns:", cols)
            if cols:
                if "notes" not in cols:
                    print("Adding column notes to incidents...")
                    conn.execute(text("ALTER TABLE incidents ADD COLUMN notes TEXT"))
                if "supporting_evidence" not in cols:
                    print("Adding column supporting_evidence to incidents...")
                    conn.execute(text("ALTER TABLE incidents ADD COLUMN supporting_evidence TEXT"))
            conn.commit()
        except Exception as e:
            print(f"Error migrating incidents: {e}")

        try:
            res = conn.execute(text("PRAGMA table_info(evidence)"))
            cols = [row[1] for row in res.fetchall()]
            print("Evidence columns:", cols)
            if cols:
                if "checksum_sha256" not in cols:
                    print("Adding column checksum_sha256 to evidence...")
                    conn.execute(text("ALTER TABLE evidence ADD COLUMN checksum_sha256 VARCHAR(64)"))
            conn.commit()
        except Exception as e:
            print(f"Error migrating evidence: {e}")

    # Now also update backend/database.py to include this migration inside init_db()
    with open("backend/database.py", "r", encoding="utf-8") as f:
        src = f.read()

    migration_code = """    Base.metadata.create_all(bind=engine)

    # Auto-migration for SQLite new columns
    if DATABASE_URL.startswith("sqlite"):
        from sqlalchemy import text
        with engine.connect() as conn:
            try:
                res = conn.execute(text("PRAGMA table_info(incidents)"))
                cols = [row[1] for row in res.fetchall()]
                if cols:
                    if "notes" not in cols:
                        conn.execute(text("ALTER TABLE incidents ADD COLUMN notes TEXT"))
                    if "supporting_evidence" not in cols:
                        conn.execute(text("ALTER TABLE incidents ADD COLUMN supporting_evidence TEXT"))
                conn.commit()
            except Exception:
                pass

            try:
                res = conn.execute(text("PRAGMA table_info(evidence)"))
                cols = [row[1] for row in res.fetchall()]
                if cols:
                    if "checksum_sha256" not in cols:
                        conn.execute(text("ALTER TABLE evidence ADD COLUMN checksum_sha256 VARCHAR(64)"))
                conn.commit()
            except Exception:
                pass
"""
    if "Auto-migration for SQLite" not in src:
        src = src.replace("    Base.metadata.create_all(bind=engine)", migration_code, 1)
        with open("backend/database.py", "w", encoding="utf-8") as f:
            f.write(src)
        print("Updated backend/database.py with auto-migration.")

if __name__ == "__main__":
    migrate()
