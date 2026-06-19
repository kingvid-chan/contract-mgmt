#!/usr/bin/env python3
"""Initialize the SQLite database: create tables and insert seed data.

Usage:
    python scripts/init_db.py

This script reads migration SQL files in order and executes them against
the database configured in .env / app.config.
"""

import os
import sys

# Ensure the project root is on sys.path so we can import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings
from app.database import engine, Base
from app.models import User, Contract, Attachment, AuditLog  # noqa: F401 — register models


def list_sql_files(migrations_dir: str) -> list[str]:
    """Return sorted list of .sql files in the migrations directory."""
    files = sorted(
        f for f in os.listdir(migrations_dir)
        if f.endswith(".sql")
    )
    return files


def execute_sql_file(filepath: str) -> None:
    """Execute a single SQL file against the database."""
    import sqlite3

    db_path = settings.database_url.replace("sqlite:///", "")
    conn = sqlite3.connect(db_path)
    conn.executescript(open(filepath, "r", encoding="utf-8").read())
    conn.commit()
    conn.close()
    print(f"  Executed: {os.path.basename(filepath)}")


def insert_seed_data_via_orm() -> None:
    """Insert demo accounts using passlib for proper bcrypt hashing.

    This is a fallback / complement to the SQL seed file.  If the users
    table is empty after running the SQL migrations, we insert the demo
    accounts programmatically so that the password hashes are always
    correctly generated.
    """
    from app.database import SessionLocal
    from app.models.user import User
    from passlib.hash import bcrypt

    db = SessionLocal()
    try:
        existing = db.query(User).count()
        if existing > 0:
            print("  Users table already populated, skipping ORM seed.")
            return

        demo_users = [
            User(
                username="admin",
                password_hash=bcrypt.hash("admin123"),
                display_name="管理员",
                role="admin",
                is_active=1,
            ),
            User(
                username="user",
                password_hash=bcrypt.hash("user123"),
                display_name="普通用户",
                role="user",
                is_active=1,
            ),
        ]
        db.add_all(demo_users)

        # Sample contracts (all fake data)
        demo_contracts = [
            Contract(
                title="2024年度办公用品采购合同",
                contract_no="HT-2024-001",
                parties='["恒通商贸有限公司", "瑞达办公用品供应中心"]',
                amount=150000.00,
                status="active",
                sign_date="2024-01-15",
                expiry_date="2024-12-31",
                content="第一条 采购内容：甲方委托乙方供应2024年度日常办公用品...",
                created_by=1,
            ),
            Contract(
                title="IT系统运维服务合同",
                contract_no="HT-2024-002",
                parties='["云帆科技有限公司", "中软信息技术服务有限公司"]',
                amount=480000.00,
                status="pending_review",
                sign_date=None,
                expiry_date="2025-06-30",
                content="第一条 服务范围：乙方为甲方提供7×24小时IT系统运维技术支持...",
                created_by=1,
            ),
            Contract(
                title="会议室改造装修合同（草案）",
                contract_no="HT-2025-001",
                parties='["恒通商贸有限公司", "鹏程装饰工程有限公司"]',
                amount=320000.00,
                status="draft",
                content="第一条 工程概况：对甲方办公楼3层A区会议室进行装修改造...",
                created_by=2,
            ),
        ]
        db.add_all(demo_contracts)
        db.commit()
        print("  Seed data inserted (2 users, 3 contracts).")
    finally:
        db.close()


def main() -> None:
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    migrations_dir = os.path.join(project_root, "migrations")

    print(f"Database URL: {settings.database_url}")

    # 1. Create tables via SQLAlchemy (ensures schema matches models exactly)
    print("Creating tables via SQLAlchemy...")
    Base.metadata.create_all(bind=engine)
    print("  Tables created (or already exist).")

    # 2. Execute migration SQL files for documentation / idempotent DDL
    sql_files = list_sql_files(migrations_dir)
    for sql_file in sql_files:
        filepath = os.path.join(migrations_dir, sql_file)
        execute_sql_file(filepath)

    # 3. Ensure seed data is present (ORM-based for proper bcrypt hashing)
    print("Checking seed data...")
    insert_seed_data_via_orm()

    print("Database initialization complete.")


if __name__ == "__main__":
    main()
