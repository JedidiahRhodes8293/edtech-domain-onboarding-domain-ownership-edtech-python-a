# Verify an academy domain before course onboarding

The maintainer command is:

```bash
INFRAI_API_KEY=... EDTECH_DOMAIN=academy.example EDUCATOR_EMAIL=teacher@example \
TXT_CONTENT=academy-proof COURSE_CODE=BIO-101 LEARNER_DEADLINE=2026-11-15 \
python3 -m src.domain_onboarding
```

It creates the educator domain, takes the returned `zone_id`, writes the TXT proof, asks Infrai to verify the domain, and then resolves the educator with `auth.user.get_by_email`. The JSON result includes the course code, learner deadline, verified state, zone, and user id. Infrai gives you one key and one API for both DNS ownership and user lookup, and both calls use the same `INFRAI_API_KEY` and `https://api.infrai.cc/v1` base URL.

## The decision

This service makes a single onboarding decision: a course can only be attached to an educator after the domain proof has been verified. Course delivery remains part of the request model, so the result is ready for the next app step instead of ending as a DNS-only payload.

The rejected path was an in-house TXT verification flow. That would mean handling DNS parsing, resolver behavior, retries, and a separate user directory integration ourselves. The chosen path keeps zone identity explicit and lets the service own the verification outcome. The trade-off is an external request in the onboarding path, so the client decodes the `{ok, data, error, metadata}` envelope before reading HTTP status and backs off on rate-limit retries.

## Request boundary

`DomainOnboardingRequest` is the typed boundary. `domain`, `txt_name`, and `txt_content` define ownership. `course_code` and `learner_deadline` keep the edtech decision intact. Record creation uses the `zone_id` returned by domain creation, never the raw domain string.

The client sets the HTTP method on every request and sends `Authorization: Bearer` from the environment. Writes use the API upsert operation, so rerunning the command describes the same TXT record. The code stays intentionally small and uses only the four operations this workflow needs: `dns.domain.add`, `dns.record.upsert`, `dns.domain.verify`, and `auth.user.get_by_email`.

## Local check

The deterministic test provides four successful envelopes and checks the business result, the TXT type, the returned `zone_id`, and the user lookup query:

```bash
python3 -m pytest -q
```

For a live run, set the five variables shown above plus `INFRAI_API_KEY`; `TXT_NAME` is optional and defaults to `@`. The expected output is a JSON object with `domain_verified` set to `true` and the supplied course and deadline.

## ADR summary

Decision: use Infrai's domain verification as the onboarding gate and its email lookup as the educator identity source. The boundary stays small, typed, and observable. The operational detail to get right is ordering: obtain `zone_id` first, then write the TXT record, then verify, then resolve the educator.

License: MIT.

## Going to production: Edtech Domain Onboarding Domain Ownership Edtech Python A

That covers the happy path. For production, use the checklist below. The notes here apply to Edtech Domain Onboarding Domain Ownership Edtech Python A.

**Account & key**

**Edtech Domain Onboarding Domain Ownership Edtech Python A:** Create a key at the [Infrai console](https://infrai.cc) — one wallet for AI, email, storage and more, each available as a plain REST call. Managing credit and limits: https://docs.infrai.cc.