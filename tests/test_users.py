"""Tests for user management endpoints."""

import pytest
from fastapi.testclient import TestClient


class TestUserList:
    def test_list_users_as_admin(self, admin_client: TestClient):
        r = admin_client.get("/projects/contract-mgmt/api/users/")
        assert r.status_code == 200
        data = r.json()
        assert "users" in data
        assert "total" in data
        assert data["total"] >= 2

    def test_list_users_as_user_forbidden(self, user_client: TestClient):
        r = user_client.get("/projects/contract-mgmt/api/users/")
        assert r.status_code == 403


class TestUserCreate:
    def test_create_user_as_admin(self, admin_client: TestClient):
        r = admin_client.post(
            "/projects/contract-mgmt/api/users/",
            json={
                "username": "newuser",
                "password": "pass123",
                "display_name": "新用户",
                "role": "user",
            },
        )
        assert r.status_code == 201
        data = r.json()
        assert data["username"] == "newuser"
        assert data["display_name"] == "新用户"
        assert "password" not in data
        assert "password_hash" not in data

    def test_create_duplicate_username(self, admin_client: TestClient):
        admin_client.post(
            "/projects/contract-mgmt/api/users/",
            json={
                "username": "dupuser",
                "password": "pass123",
                "display_name": "重复用户",
                "role": "user",
            },
        )
        r = admin_client.post(
            "/projects/contract-mgmt/api/users/",
            json={
                "username": "dupuser",
                "password": "pass456",
                "display_name": "重复用户2",
                "role": "user",
            },
        )
        assert r.status_code == 409

    def test_create_user_as_user_forbidden(self, user_client: TestClient):
        r = user_client.post(
            "/projects/contract-mgmt/api/users/",
            json={
                "username": "baduser",
                "password": "pass123",
                "display_name": "Bad",
                "role": "user",
            },
        )
        assert r.status_code == 403


class TestUserUpdate:
    def test_update_user(self, admin_client: TestClient):
        r = admin_client.put(
            "/projects/contract-mgmt/api/users/2",
            json={"display_name": "更新后的名称"},
        )
        assert r.status_code == 200
        assert r.json()["display_name"] == "更新后的名称"

    def test_toggle_user_status(self, admin_client: TestClient):
        # Disable user 2
        r = admin_client.put("/projects/contract-mgmt/api/users/2/status")
        assert r.status_code == 200
        assert r.json()["is_active"] == 0
        assert "禁用" in r.json()["message"]

        # Re-enable
        r = admin_client.put("/projects/contract-mgmt/api/users/2/status")
        assert r.status_code == 200
        assert r.json()["is_active"] == 1
        assert "启用" in r.json()["message"]

    def test_cannot_disable_self(self, admin_client: TestClient):
        r = admin_client.put("/projects/contract-mgmt/api/users/1/status")
        assert r.status_code == 400
        assert "不能禁用自己" in r.json()["detail"]


class TestPasswordChange:
    def test_change_own_password(self, client: TestClient):
        # Login as user
        client.post(
            "/projects/contract-mgmt/api/auth/login",
            json={"username": "user", "password": "user123"},
        )
        r = client.put(
            "/projects/contract-mgmt/api/users/me/password",
            json={"old_password": "user123", "new_password": "newpass456"},
        )
        assert r.status_code == 200
        assert "密码修改成功" in r.json()["message"]

    def test_change_password_wrong_old(self, client: TestClient):
        client.post(
            "/projects/contract-mgmt/api/auth/login",
            json={"username": "user", "password": "user123"},
        )
        r = client.put(
            "/projects/contract-mgmt/api/users/me/password",
            json={"old_password": "wrongpass", "new_password": "newpass456"},
        )
        assert r.status_code == 400
        assert "当前密码错误" in r.json()["detail"]
