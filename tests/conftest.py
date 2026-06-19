"""Pytest fixtures for contract management system tests."""

import os
import sys
import tempfile
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _seed(db) -> None:
    from passlib.hash import bcrypt
    from app.models.user import User

    db.add_all([
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
    ])
    db.commit()


@pytest.fixture(scope="function")
def app():
    """Create a FastAPI app backed by a unique per-test SQLite database."""
    db_path = os.path.join(tempfile.gettempdir(), f"test_cm_{uuid.uuid4().hex}.db")
    db_url = f"sqlite:///{db_path}"
    upload_dir = os.path.join(tempfile.gettempdir(), f"test_up_{uuid.uuid4().hex}")

    from app.config import settings
    settings.database_url = db_url
    settings.upload_dir = upload_dir

    import app.database as db_mod
    test_engine = create_engine(db_url, connect_args={"check_same_thread": False})
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    db_mod.engine = test_engine
    db_mod.SessionLocal = TestSessionLocal

    from app.database import Base, get_db
    from app.main import create_app

    application = create_app()

    def get_test_db():
        db = TestSessionLocal()
        try:
            yield db
        finally:
            db.close()

    application.dependency_overrides[get_db] = get_test_db

    yield application

    Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()
    try:
        os.remove(db_path)
    except OSError:
        pass
    try:
        import shutil
        shutil.rmtree(upload_dir, ignore_errors=True)
    except Exception:
        pass


@pytest.fixture(scope="function")
def client(app) -> TestClient:
    """Unauthenticated TestClient."""
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="function")
def admin_client(app) -> TestClient:
    """TestClient pre-authenticated as admin (separate client instance)."""
    with TestClient(app) as c:
        r = c.post(
            "/projects/contract-mgmt/api/auth/login",
            json={"username": "admin", "password": "admin123"},
        )
        assert r.status_code == 200, f"Admin login failed: {r.json()}"
        yield c


@pytest.fixture(scope="function")
def user_client(app) -> TestClient:
    """TestClient pre-authenticated as regular user (separate client instance)."""
    with TestClient(app) as c:
        r = c.post(
            "/projects/contract-mgmt/api/auth/login",
            json={"username": "user", "password": "user123"},
        )
        assert r.status_code == 200, f"User login failed: {r.json()}"
        yield c


@pytest.fixture(scope="function")
def sample_contract(admin_client: TestClient) -> dict:
    """Create a sample contract and return its JSON representation."""
    r = admin_client.post(
        "/projects/contract-mgmt/api/contracts/",
        json={
            "title": "测试合同",
            "contract_no": f"HT-{uuid.uuid4().hex[:6].upper()}",
            "parties": [
                {"name": "甲方公司", "role": "甲方"},
                {"name": "乙方公司", "role": "乙方"},
            ],
            "amount": 100000.0,
        },
    )
    assert r.status_code == 201, f"Contract creation failed: {r.json()}"
    return r.json()
