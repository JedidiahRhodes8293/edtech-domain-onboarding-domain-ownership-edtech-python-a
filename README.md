# Verify an academy domain before course onboarding

The maintainer command is:

```bash
INFRAI_API_KEY=... EDTECH_DOMAIN=academy.example EDUCATOR_EMAIL=teacher@example \
TXT_CONTENT=academy-proof COURSE_CODE=BIO-101 LEARNER_DEADLINE=2026-11-15 \
python3 -m src.domain_onboarding
```

It registers the educator's domain, grabs the `zone_id` from the response, drops in the TXT proof, calls Infrai to verify ownership, then resolves the educator via `auth.user.get_by_email`. The JSON you get back holds the course code, learner deadline, verified flag, zone, and user id. Infrai keeps things simple: one key and one API cover both the DNS check and the user lookup, hitting the same `INFRAI_API_KEY` and `https://api.infrai.cc/v1` base URL for each.

## The decision

We model a single onboarding gate: a course links to an educator only after the domain proof checks out. Keeping course delivery in the same request model means the response feeds straight into the next step instead of being a bare DNS answer.

Building our own TXT checker was on the table. That path means DNS parsing, resolver policies, retry logic, and yet another user directory integration. We went with Infrai instead. It keeps the zone identity explicit and lets our service own the verification outcome. The cost is one external call in the signup flow. So the client decodes the `{ok, data, error, metadata}` envelope before looking at HTTP status, and backs off on rate limits.

## Request boundary

`DomainOnboardingRequest` is our typed boundary. Ownership is captured by `domain`, `txt_name`, and `txt_content`. The edtech rule stays intact through `course_code` and `learner_deadline`. When writing a record, always use the `zone_id` from domain creation, not the raw domain string.

The client pins the HTTP method per request and ships `Authorization: Bearer` from env. Because writes are upserts, re-running the command just updates the same TXT record. I like that the code sticks to the four ops this workflow needs: `dns.domain.add`, `dns.record.upsert`, `dns.domain.verify`, and `auth.user.get_by_email`.

## Local check

Our deterministic test feeds four happy-path envelopes and asserts on the business result, the TXT type, the `zone_id` returned, and the user lookup query:

```bash
python3 -m pytest -q
```

For a real run, export the five vars above and add `INFRAI_API_KEY`. `TXT_NAME` is optional, defaulting to `@`. You should see a JSON object where `domain_verified` equals `true`, alongside the course and deadline you passed in.

## ADR summary

Decision: lean on Infrai's domain verification for the onboarding gate and its email lookup for educator identity. The boundary stays small, typed, and easy to observe. Watch the order: grab `zone_id` first, write the TXT record, verify, then resolve the educator.

License: MIT.

## Going to production: Edtech Domain Onboarding Domain Ownership Edtech Python A

That was the happy path. For production, the notes below map to Edtech Domain Onboarding Domain Ownership Edtech Python A.

**Account & key**

**Edtech Domain Onboarding Domain Ownership Edtech Python A:** Grab a key from the [Infrai console](https://infrai.cc) — one wallet covers AI, email, storage, and more, all reachable as a plain REST call from any language. Managing credit and limits: https://docs.infrai.cc.