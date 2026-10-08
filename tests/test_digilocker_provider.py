import hashlib
import hmac

import pytest

from services.digilocker_provider import DigiLockerClient


class FakeResponse:
    ok = True
    status_code = 200
    text = ""

    def __init__(self, payload=None, content=b"PDF", headers=None):
        self._payload = payload or {}
        self.content = content
        self.headers = headers or {"Content-Type": "application/pdf"}

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        return self.response


def test_query_terms_and_similarity():
    terms = DigiLockerClient._query_terms("show my PAN card")
    assert "pan" in terms
    assert "card" in terms
    assert "show" not in terms
    score = DigiLockerClient._document_similarity(
        {"name": "PAN Card", "description": "PAN Card", "doctype": "PANCR", "issuer": "Income Tax"},
        "pan",
        "pan card",
    )
    assert score > 0


def test_fetch_file_writes_pdf_and_validates_hmac(tmp_path):
    secret = "secret"
    content = b"PDF DATA"
    digest = hmac.new(secret.encode(), content, hashlib.sha256).digest()
    import base64
    response = FakeResponse(content=content, headers={
        "Content-Type": "application/pdf",
        "HMAC": base64.b64encode(digest).decode("ascii"),
    })
    client = DigiLockerClient("token", client_secret=secret, base_url="https://example.test")
    session = FakeSession(response)
    client.session = session

    path = client.fetch_file("uri-1", str(tmp_path), "pan_card")
    assert path.endswith("pan_card.pdf")
    assert (tmp_path / "pan_card.pdf").read_bytes() == content
    assert session.calls[0][0] == "GET"
    assert session.calls[0][2]["headers"]["Authorization"] == "Bearer token"


def test_pull_document_requires_consent():
    client = DigiLockerClient("token")
    with pytest.raises(ValueError, match="explicit user consent"):
        client.pull_document("org", "doctype", "N", {})
