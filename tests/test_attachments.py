"""Tests for attachment upload / download / delete endpoints."""

import io

import pytest
from fastapi.testclient import TestClient

ATTACH_API = "/projects/contract-mgmt/api/contracts"
ATTACH_API_DIRECT = "/projects/contract-mgmt/api/attachments"


def _upload(client: TestClient, contract_id: int, filename: str, content: bytes, content_type: str):
    """Helper: upload a file to a contract."""
    return client.post(
        f"{ATTACH_API}/{contract_id}/attachments",
        files={"file": (filename, io.BytesIO(content), content_type)},
    )


class TestAttachmentUpload:
    def test_upload_pdf(self, admin_client: TestClient, sample_contract: dict):
        cid = sample_contract["id"]
        r = _upload(admin_client, cid, "test.pdf", b"%PDF-1.4 test", "application/pdf")
        assert r.status_code == 201
        data = r.json()
        assert data["original_name"] == "test.pdf"
        assert data["mime_type"] == "application/pdf"
        assert data["file_size"] > 0
        assert data["uploaded_by_username"] == "admin"

    def test_upload_doc(self, admin_client: TestClient, sample_contract: dict):
        cid = sample_contract["id"]
        r = _upload(admin_client, cid, "test.doc", b"DOC file", "application/msword")
        assert r.status_code == 201
        data = r.json()
        assert data["original_name"] == "test.doc"
        assert data["mime_type"] == "application/msword"
        assert data["file_size"] > 0

    def test_upload_docx(self, admin_client: TestClient, sample_contract: dict):
        cid = sample_contract["id"]
        r = _upload(
            admin_client, cid, "test.docx", b"DOCX file",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        assert r.status_code == 201
        data = r.json()
        assert "docx" in data["original_name"]

    def test_upload_invalid_type(self, admin_client: TestClient, sample_contract: dict):
        cid = sample_contract["id"]
        r = _upload(admin_client, cid, "test.txt", b"text", "text/plain")
        assert r.status_code == 400
        assert "不支持" in r.json()["detail"]

    def test_upload_to_nonexistent_contract(self, admin_client: TestClient):
        r = _upload(admin_client, 99999, "test.pdf", b"%PDF", "application/pdf")
        assert r.status_code == 404

    def test_upload_unauthenticated(self, client: TestClient, sample_contract: dict):
        cid = sample_contract["id"]
        r = _upload(client, cid, "test.pdf", b"%PDF", "application/pdf")
        assert r.status_code == 401


class TestAttachmentList:
    def test_list_attachments(self, admin_client: TestClient, sample_contract: dict):
        cid = sample_contract["id"]
        _upload(admin_client, cid, "a.pdf", b"%PDF a", "application/pdf")
        _upload(admin_client, cid, "b.pdf", b"%PDF b", "application/pdf")

        r = admin_client.get(f"{ATTACH_API}/{cid}/attachments")
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 2


class TestAttachmentDownload:
    def test_download_attachment(self, admin_client: TestClient, sample_contract: dict):
        cid = sample_contract["id"]
        _upload(admin_client, cid, "download.pdf", b"%PDF content", "application/pdf")

        r = admin_client.get(f"{ATTACH_API_DIRECT}/1/download")
        assert r.status_code == 200
        assert b"%PDF" in r.content

    def test_download_nonexistent(self, admin_client: TestClient):
        r = admin_client.get(f"{ATTACH_API_DIRECT}/99999/download")
        assert r.status_code == 404


class TestAttachmentDelete:
    def test_delete_as_admin(self, admin_client: TestClient, sample_contract: dict):
        cid = sample_contract["id"]
        _upload(admin_client, cid, "todelete.pdf", b"%PDF", "application/pdf")

        r = admin_client.delete(f"{ATTACH_API_DIRECT}/1")
        assert r.status_code == 200
        assert "已删除" in r.json()["message"]

        # Verify gone
        r = admin_client.get(f"{ATTACH_API_DIRECT}/1/download")
        assert r.status_code == 404

    def test_user_cannot_delete_admin_attachment(
        self, admin_client: TestClient, user_client: TestClient, sample_contract: dict
    ):
        cid = sample_contract["id"]
        _upload(admin_client, cid, "admin_file.pdf", b"%PDF", "application/pdf")

        r = user_client.delete(f"{ATTACH_API_DIRECT}/1")
        assert r.status_code == 403

    def test_delete_nonexistent(self, admin_client: TestClient):
        r = admin_client.delete(f"{ATTACH_API_DIRECT}/99999")
        assert r.status_code == 404
