from pathlib import Path

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
    def __init__(self):
        self.calls = []

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        if url.endswith('/public/oauth2/2/files/issued'):
            return FakeResponse({"items": [
                {"name": "PAN Card", "description": "PAN Card", "doctype": "PANCR", "uri": "pan-uri"},
                {"name": "Driving Licence", "description": "Driving Licence", "doctype": "DRVLC", "uri": "dl-uri"},
            ]})
        if url.endswith('/public/oauth2/1/file/uri'):
            return FakeResponse(content=b"pdf-bytes")
        raise AssertionError(url)


def test_digilocker_issued_document_search_and_fetch(tmp_path):
    client = DigiLockerClient("access-token")
    session = FakeSession()
    client.session = session

    matches = client.search_issued_documents("pan", "PAN Card", limit=1)
    assert matches and matches[0]["doctype"] == "PANCR"

    output = client.fetch_file(matches[0]["uri"], str(tmp_path), "pan_card")
    assert Path(output).read_bytes() == b"pdf-bytes"
    assert session.calls[0][2]["headers"]["Authorization"] == "Bearer access-token"
    assert session.calls[1][2]["params"] == {"uri": "pan-uri"}


def test_digilocker_can_match_an_unmapped_issued_document_name(tmp_path):
    client = DigiLockerClient("access-token")
    session = FakeSession()
    session.request = lambda method, url, **kwargs: FakeResponse({"items": [
        {"name": "Ayushman Bharat Health Account", "description": "Ayushman Bharat Health Account", "doctype": "ABHA1", "uri": "abha-uri"},
        {"name": "Driving Licence", "description": "Driving Licence", "doctype": "DRVLC", "uri": "dl-uri"},
    ]})
    client.session = session
    matches = client.search_issued_documents(None, "please show my Ayushman Bharat Health Account", limit=1)
    assert matches and matches[0]["uri"] == "abha-uri"
