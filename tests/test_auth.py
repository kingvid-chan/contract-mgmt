"""Tests for authentication endpoints."""

import pytest
from fastapi.testclient import TestClient


class TestAuthLogin:
    def test_login_success_admin(self, client: TestClient):
        r = client.post(
            "/projects/contract-mgmt/api/auth/login",
            json={"username": "admin", "password": "admin123"},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["message"] == "登录成功"
        assert data["user"]["username"] == "admin"
        assert data["user"]["role"] == "admin"
        assert "password" not in str(data)

    def test_login_success_user(self, client: TestClient):
        r = client.post(
            "/projects/contract-mgmt/api/auth/login",
            json={"username": "user", "password": "user123"},
        )
        assert r.status_code == 200
        assert r.json()["user"]["role"] == "user"

    def test_login_wrong_password(self, client: TestClient):
        r = client.post(
            "/projects/contract-mgmt/api/auth/login",
            json={"username": "admin", "password": "wrong"},
        )
        assert r.status_code == 401
        assert "用户名或密码错误" in r.json()["detail"]

    def test_login_nonexistent_user(self, client: TestClient):
        r = client.post(
            "/projects/contract-mgmt/api/auth/login",
            json={"username": "nobody", "password": "whatever"},
        )
        assert r.status_code == 401

    def test_login_disabled_user(self, client: TestClient):
        # Login as admin first, then disable user
        client.post(
            "/projects/contract-mgmt/api/auth/login",
            json={"username": "admin", "password": "admin123"},
        )
        client.put("/projects/contract-mgmt/api/users/2/status")
        # Now try to login as the disabled user
        r = client.post(
            "/projects/contract-mgmt/api/auth/login",
            json={"username": "user", "password": "user123"},
        )
        assert r.status_code == 403
        assert "禁用" in r.json()["detail"]


class TestAuthLogout:
    def test_logout(self, client: TestClient):
        client.post(
            "/projects/contract-mgmt/api/auth/login",
            json={"username": "admin", "password": "admin123"},
        )
        r = client.post("/projects/contract-mgmt/api/auth/logout")
        assert r.status_code == 200
        assert r.json()["message"] == "已登出"

    def test_me_after_logout(self, client: TestClient):
        client.post(
            "/projects/contract-mgmt/api/auth/login",
            json={"username": "admin", "password": "admin123"},
        )
        client.post("/projects/contract-mgmt/api/auth/logout")
        r = client.get("/projects/contract-mgmt/api/auth/me")
        assert r.status_code == 401


class TestAuthMe:
    def test_me_authenticated(self, client: TestClient):
        client.post(
            "/projects/contract-mgmt/api/auth/login",
            json={"username": "admin", "password": "admin123"},
        )
        r = client.get("/projects/contract-mgmt/api/auth/me")
        assert r.status_code == 200
        assert r.json()["username"] == "admin"
        assert r.json()["display_name"] == "管理员"

    def test_me_unauthenticated(self, client: TestClient):
        r = client.get("/projects/contract-mgmt/api/auth/me")
        assert r.status_code == 401
