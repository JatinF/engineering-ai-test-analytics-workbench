# Threat model

The lab has two tenants and four fixture actors. Tokens are compared with `secrets.compare_digest` after a length check. They are not an external identity provider.

| Boundary | Behavior |
| --- | --- |
| Tenant | Tool arguments cannot override the actor's tenant. A denied override is audited. |
| Flash tool | `flash_firmware` is listed and denied for every actor. Accepted calls stay 0. `device_calls` stays 0. |
| Review | `investigation.review` is required. The requester cannot review their own draft. |
| Remote URL | A non-local `DATABASE_URL` raises `remote_blocked` and the message does not include the URL. |
| Logs | Search is filtered by tenant, build, and failure code. Marshline chunks are not returned to the Ridgebench tenant. |
| Request body | Extra fields such as `approved` are rejected by the schema. Approval is a second call. |

Dirty rows are stored only in `dq_rejects`. They do not enter `test_runs`, `failures`, or `telemetry`.

No real device log, customer firmware, or factory credential is in this repository.
