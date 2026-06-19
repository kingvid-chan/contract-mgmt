"""Tests for contract management endpoints."""

import pytest
from fastapi.testclient import TestClient

API = "/projects/contract-mgmt/api/contracts"


class TestContractCreate:
    def test_create_contract(self, admin_client: TestClient):
        r = admin_client.post(
            f"{API}/",
            json={
                "title": "2026年度软件开发合同",
                "contract_no": "HT-2026-001",
                "parties": [
                    {"name": "恒通商贸有限公司", "role": "甲方"},
                    {"name": "云帆科技有限公司", "role": "乙方"},
                ],
                "amount": 500000.0,
                "sign_date": "2026-01-15",
                "expiry_date": "2026-12-31",
            },
        )
        assert r.status_code == 201
        data = r.json()
        assert data["title"] == "2026年度软件开发合同"
        assert data["contract_no"] == "HT-2026-001"
        assert data["status"] == "draft"
        assert len(data["parties"]) == 2
        assert data["amount"] == 500000.0
        assert data["created_by_username"] == "admin"

    def test_duplicate_contract_no(self, admin_client: TestClient):
        admin_client.post(
            f"{API}/",
            json={
                "title": "第一个合同",
                "contract_no": "HT-DUP-001",
                "parties": [
                    {"name": "A", "role": "甲方"},
                    {"name": "B", "role": "乙方"},
                ],
                "amount": 100.0,
            },
        )
        r = admin_client.post(
            f"{API}/",
            json={
                "title": "重复编号合同",
                "contract_no": "HT-DUP-001",
                "parties": [
                    {"name": "A", "role": "甲方"},
                    {"name": "B", "role": "乙方"},
                ],
                "amount": 200.0,
            },
        )
        assert r.status_code == 409
        assert "合同编号已存在" in r.json()["detail"]


class TestContractList:
    def test_list_contracts(self, admin_client: TestClient):
        # Create 2 contracts first
        for i in range(2):
            admin_client.post(
                f"{API}/",
                json={
                    "title": f"合同{i}",
                    "contract_no": f"HT-LIST-00{i}",
                    "parties": [
                        {"name": "甲方", "role": "甲方"},
                        {"name": "乙方", "role": "乙方"},
                    ],
                    "amount": 100.0 * (i + 1),
                },
            )
        r = admin_client.get(f"{API}/")
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 2
        assert data["page"] == 1
        assert data["page_size"] == 20
        assert len(data["contracts"]) == 2

    def test_search_contracts(self, admin_client: TestClient):
        admin_client.post(
            f"{API}/",
            json={
                "title": "采购合同",
                "contract_no": "HT-SEARCH-001",
                "parties": [
                    {"name": "甲", "role": "甲方"},
                    {"name": "乙", "role": "乙方"},
                ],
                "amount": 100.0,
            },
        )
        admin_client.post(
            f"{API}/",
            json={
                "title": "服务合同",
                "contract_no": "HT-SEARCH-002",
                "parties": [
                    {"name": "甲", "role": "甲方"},
                    {"name": "乙", "role": "乙方"},
                ],
                "amount": 200.0,
            },
        )
        r = admin_client.get(f"{API}/?search=采购")
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 1
        assert "采购" in data["contracts"][0]["title"]

    def test_filter_by_status(self, admin_client: TestClient):
        admin_client.post(
            f"{API}/",
            json={
                "title": "草稿合同",
                "contract_no": "HT-STAT-001",
                "parties": [
                    {"name": "甲", "role": "甲方"},
                    {"name": "乙", "role": "乙方"},
                ],
                "amount": 100.0,
            },
        )
        r = admin_client.get(f"{API}/?status=draft")
        assert r.status_code == 200
        for c in r.json()["contracts"]:
            assert c["status"] == "draft"


class TestContractDetail:
    def test_get_contract_detail(self, admin_client: TestClient, sample_contract: dict):
        contract_id = sample_contract["id"]
        r = admin_client.get(f"{API}/{contract_id}")
        assert r.status_code == 200
        data = r.json()
        assert data["contract_no"] == sample_contract["contract_no"]
        assert "attachments" in data
        assert "allowed_transitions" in data
        assert "pending_review" in data["allowed_transitions"]

    def test_get_nonexistent_contract(self, admin_client: TestClient):
        r = admin_client.get(f"{API}/99999")
        assert r.status_code == 404


class TestContractUpdate:
    def test_update_draft_contract(self, admin_client: TestClient, sample_contract: dict):
        contract_id = sample_contract["id"]
        r = admin_client.put(
            f"{API}/{contract_id}",
            json={"title": "更新后的合同标题"},
        )
        assert r.status_code == 200
        assert r.json()["title"] == "更新后的合同标题"


class TestContractStatusFlow:
    def test_full_status_flow(self, admin_client: TestClient, sample_contract: dict):
        cid = sample_contract["id"]

        # draft → pending_review
        r = admin_client.post(
            f"{API}/{cid}/status",
            json={"status": "pending_review", "reason": "请审批"},
        )
        assert r.status_code == 200
        assert r.json()["status"] == "pending_review"

        # pending_review → active
        r = admin_client.post(
            f"{API}/{cid}/status",
            json={"status": "active", "reason": "审批通过"},
        )
        assert r.status_code == 200
        assert r.json()["status"] == "active"

        # active → expired
        r = admin_client.post(
            f"{API}/{cid}/status",
            json={"status": "expired", "reason": "合同到期"},
        )
        assert r.status_code == 200
        assert r.json()["status"] == "expired"

    def test_draft_to_terminated(self, admin_client: TestClient, sample_contract: dict):
        cid = sample_contract["id"]
        r = admin_client.post(
            f"{API}/{cid}/status",
            json={"status": "terminated", "reason": "合同取消"},
        )
        assert r.status_code == 200
        assert r.json()["status"] == "terminated"

    def test_invalid_transition(self, admin_client: TestClient, sample_contract: dict):
        cid = sample_contract["id"]
        # Try draft → expired (invalid)
        r = admin_client.post(
            f"{API}/{cid}/status",
            json={"status": "expired", "reason": "attempt"},
        )
        assert r.status_code == 400
        assert "不允许" in r.json()["detail"]

    def test_edit_after_terminated(self, admin_client: TestClient, sample_contract: dict):
        cid = sample_contract["id"]
        # First terminate
        admin_client.post(
            f"{API}/{cid}/status",
            json={"status": "terminated"},
        )
        # Then try to edit
        r = admin_client.put(
            f"{API}/{cid}",
            json={"title": "不能修改"},
        )
        assert r.status_code == 400
        assert "不允许编辑" in r.json()["detail"]


class TestContractDelete:
    def test_admin_delete_contract(self, admin_client: TestClient, sample_contract: dict):
        cid = sample_contract["id"]
        r = admin_client.delete(f"{API}/{cid}")
        assert r.status_code == 200
        assert "已删除" in r.json()["message"]

    def test_user_cannot_delete_others_contract(
        self, admin_client: TestClient, user_client: TestClient, sample_contract: dict
    ):
        cid = sample_contract["id"]
        r = user_client.delete(f"{API}/{cid}")
        assert r.status_code == 403
