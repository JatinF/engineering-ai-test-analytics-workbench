# ADR 0001 — Keep the agent in front of the SQL view

## Status

Accepted for this synthetic lab. Not a deployment approval.

## Context

The semantic views already show pass rate, failure trend, and the rate delta against earlier builds. A four-query lookup is enough to see that `SYN-FW-417` thermal failures jumped.

The agent adds a citation check: a regression draft must quote log chunks that contain the build's change note. Floors were set first: success and citation accuracy at least 0.90, and no accepted protected flash call.

## Decision

Keep the agent. The measured success rate is 0.9375 and citation accuracy is 0.9375. Protected accepts are 0.

The agent is not faster. Its p50 on 40 repeats was 0.0020158999977866188 seconds. The SQL lookup p50 was 0.0003892999957315624 seconds. Time saved is not the reason.

## Consequences

`SYN-FW-419` latency stays a correction. The synonym was not added to the rule after the run. A hosted model was not called, so there is no dollar cost to compare. Price stays none.
