# Remote database blocked

`GET /health` does not open `DATABASE_URL`. If a caller passes a non-local URL and `ENG_WORKBENCH_ALLOW_REMOTE` is not `1`, the gate raises `remote_blocked`. The error text does not include the URL, and the process does not dial.

Leave the variable unset on a workstation. The lab then stays on SQLite.
