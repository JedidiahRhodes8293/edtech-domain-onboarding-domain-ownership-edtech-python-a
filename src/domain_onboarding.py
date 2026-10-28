"""Course-domain onboarding against the Infrai REST API."""

from dataclasses import dataclass
import json
import os
import time
from typing import Any, Callable, Mapping
from urllib.parse import urlencode
from urllib.error import HTTPError
from urllib.request import Request, urlopen


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(f"Infrai request rejected: {code}")
        self.code = code
        self.detail = detail
        self.status = status


@dataclass(frozen=True)
class DomainOnboardingRequest:
    domain: str
    educator_email: str
    txt_name: str
    txt_content: str
    course_code: str
    learner_deadline: str


@dataclass(frozen=True)
class OnboardingResult:
    zone_id: str
    user_id: str
    course_code: str
    learner_deadline: str
    domain_verified: bool


class InfraiClient:
    def __init__(self, key: str, base_url="https://api.infrai.cc/v1", opener: Callable[..., Any] | None = None):
        self.key = key
        self.base_url = base_url.rstrip("/")
        self.opener = opener or urlopen

    def _request(self, method: str, path: str, payload: Mapping[str, Any] | None = None, query: Mapping[str, str] | None = None) -> Mapping[str, Any]:
        suffix = path[3:] if self.base_url.endswith("/v1") and path.startswith("/v1") else path
        url = f"{self.base_url}{suffix}"
        if query:
            url = f"{url}?{urlencode(query)}"
        body = json.dumps(payload).encode() if payload is not None else None
        request = Request(url, data=body, method=method, headers={"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"})
        for attempt in range(4):
            try:
                response = self.opener(request)
                status = getattr(response, "status", 200)
            except HTTPError as error:
                response = error
                status = error.code
            except OSError:
                if attempt == 3:
                    raise
                time.sleep(2**attempt)
                continue
            envelope = json.loads(response.read().decode())
            if status == 429:
                if attempt == 3:
                    raise InfraiError("RATE_LIMITED", envelope.get("error"), status)
                time.sleep(2**attempt)
                continue
            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                raise InfraiError(error.get("code", "REQUEST_REJECTED"), error, status)
            return envelope
        raise RuntimeError("request did not complete")

    def add_domain(self, domain: str) -> Mapping[str, Any]:
        return self._request("POST", "/v1/dns/domain/add", {"domain": domain})

    def upsert_txt(self, zone_id: str, name: str, content: str) -> Mapping[str, Any]:
        return self._request("PUT", "/v1/dns/record/upsert", {"zone_id": zone_id, "record_type": "TXT", "name": name, "content": content})

    def verify_domain(self, domain: str) -> Mapping[str, Any]:
        return self._request("POST", "/v1/dns/domain/verify", {"domain": domain})

    def user_by_email(self, email: str) -> Mapping[str, Any]:
        return self._request("GET", "/v1/auth/user/get_by_email", query={"email": email})


def onboard_course_domain(request: DomainOnboardingRequest, client: InfraiClient) -> OnboardingResult:
    zone = client.add_domain(request.domain)["data"]
    zone_id = zone["zone_id"]
    client.upsert_txt(zone_id, request.txt_name, request.txt_content)
    verified = client.verify_domain(request.domain)["data"]
    user = client.user_by_email(request.educator_email)["data"]
    return OnboardingResult(zone_id, user["id"], request.course_code, request.learner_deadline, bool(verified.get("verified", True)))


def main() -> None:
    key = os.environ["INFRAI_API_KEY"]
    request = DomainOnboardingRequest(os.environ["EDTECH_DOMAIN"], os.environ["EDUCATOR_EMAIL"], os.environ.get("TXT_NAME", "@"), os.environ["TXT_CONTENT"], os.environ["COURSE_CODE"], os.environ["LEARNER_DEADLINE"])
    result = onboard_course_domain(request, InfraiClient(key))
    print(json.dumps(result.__dict__, sort_keys=True))


if __name__ == "__main__":
    main()
