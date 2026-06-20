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


class TestPageRouteRedirect:
    """Unauthenticated access to page routes must return 302 → /login,
    not 401 JSON."""

    def test_contracts_page_unauthenticated_redirects(self, client: TestClient):
        r = client.get(
            "/projects/contract-mgmt/contracts",
            follow_redirects=False,
        )
        assert r.status_code == 302
        assert r.headers["location"] == "/projects/contract-mgmt/login"

    def test_contracts_new_unauthenticated_redirects(self, client: TestClient):
        r = client.get(
            "/projects/contract-mgmt/contracts/new",
            follow_redirects=False,
        )
        assert r.status_code == 302
        assert r.headers["location"] == "/projects/contract-mgmt/login"

    def test_contracts_detail_unauthenticated_redirects(self, client: TestClient):
        r = client.get(
            "/projects/contract-mgmt/contracts/1",
            follow_redirects=False,
        )
        assert r.status_code == 302
        assert r.headers["location"] == "/projects/contract-mgmt/login"

    def test_contracts_edit_unauthenticated_redirects(self, client: TestClient):
        r = client.get(
            "/projects/contract-mgmt/contracts/1/edit",
            follow_redirects=False,
        )
        assert r.status_code == 302
        assert r.headers["location"] == "/projects/contract-mgmt/login"

    def test_users_page_unauthenticated_redirects(self, client: TestClient):
        r = client.get(
            "/projects/contract-mgmt/users",
            follow_redirects=False,
        )
        assert r.status_code == 302
        assert r.headers["location"] == "/projects/contract-mgmt/login"

    def test_users_new_unauthenticated_redirects(self, client: TestClient):
        r = client.get(
            "/projects/contract-mgmt/users/new",
            follow_redirects=False,
        )
        assert r.status_code == 302
        assert r.headers["location"] == "/projects/contract-mgmt/login"

    def test_login_page_accessible_without_auth(self, client: TestClient):
        """/login must NOT be protected, otherwise redirect loop happens."""
        r = client.get("/projects/contract-mgmt/login")
        assert r.status_code == 200

    def test_root_redirects_to_contracts(self, client: TestClient):
        """Root / should redirect to /contracts (307 default in Starlette)."""
        r = client.get("/projects/contract-mgmt/", follow_redirects=False)
        assert r.status_code in (302, 307)
        assert r.headers["location"] == "/projects/contract-mgmt/contracts"

    def test_contracts_page_authenticated_works(self, admin_client: TestClient):
        """Logged-in user sees contracts page normally."""
        r = admin_client.get("/projects/contract-mgmt/contracts")
        assert r.status_code == 200

    def test_root_authenticated_works(self, admin_client: TestClient):
        """Logged-in user at root redirects to contracts page."""
        r = admin_client.get(
            "/projects/contract-mgmt/",
            follow_redirects=False,
        )
        assert r.status_code in (302, 307)
        assert r.headers["location"] == "/projects/contract-mgmt/contracts"

    def test_api_routes_still_401_for_unauthenticated(self, client: TestClient):
        """API routes must continue to return 401 JSON, not 302."""
        r = client.get("/projects/contract-mgmt/api/auth/me")
        assert r.status_code == 401
        assert r.json()["detail"] == "未登录，请先登录"

    def test_api_routes_still_work_for_authenticated(self, admin_client: TestClient):
        """API routes must continue to work normally for logged-in users."""
        r = admin_client.get("/projects/contract-mgmt/api/auth/me")
        assert r.status_code == 200
        assert r.json()["username"] == "admin"
