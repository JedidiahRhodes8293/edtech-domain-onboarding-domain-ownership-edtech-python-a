import json
from urllib.error import HTTPError

from src.domain_onboarding import DomainOnboardingRequest, InfraiClient, onboard_course_domain


class Response:
    status = 200

    def __init__(self, data):
        self.data = json.dumps(data).encode()

    def read(self):
        return self.data

    def close(self):
        pass


def test_onboarding_uses_zone_id_and_returns_verified_course_state():
    calls = []
    replies = [
        {"ok": True, "data": {"zone_id": "zone-7"}},
        {"ok": True, "data": {"record_id": "record-3"}},
        {"ok": True, "data": {"verified": True}},
        {"ok": True, "data": {"id": "user-9"}},
    ]

    def opener(request):
        calls.append((request.method, request.full_url, json.loads(request.data) if request.data else None))
        return Response(replies.pop(0))

    client = InfraiClient("test-key", base_url="https://example.test/v1", opener=opener)
    result = onboard_course_domain(DomainOnboardingRequest("academy.example", "teacher@example", "@", "academy-proof", "BIO-101", "2026-11-15"), client)

    assert result == result.__class__("zone-7", "user-9", "BIO-101", "2026-11-15", True)
    assert calls[1][2]["zone_id"] == "zone-7"
    assert calls[1][2]["record_type"] == "TXT"
    assert calls[2][0] == "POST"
    assert "email=teacher%40example" in calls[3][1]


def test_http_error_decodes_rate_limit_envelope_and_retries():
    attempts = []

    def opener(request):
        attempts.append(request)
        if len(attempts) == 1:
            raise HTTPError(request.full_url, 429, "rate limited", {}, Response({"ok": False, "error": {"code": "RATE_LIMITED"}}))
        return Response({"ok": True, "data": {"zone_id": "zone-7"}})

    client = InfraiClient("test-key", base_url="https://example.test/v1", opener=opener)
    assert client.add_domain("academy.example")["data"]["zone_id"] == "zone-7"
    assert len(attempts) == 2
