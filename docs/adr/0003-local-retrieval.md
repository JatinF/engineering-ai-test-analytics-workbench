# ADR 0003 — Local retrieval, no hosted model

## Status

Accepted.

## Context

The investigation needs related logs and a comparison with earlier builds. A hosted chat model was not required to apply the phrase-and-rate rule, and no model endpoint was configured.

## Decision

Retrieve log chunks with SQL filtered by tenant, build, and failure code. LangGraph orders the steps and journals them so a retry does not repeat a finished tool call. StateGraph replaces state on each node, so every node returns the carried state and the journal is read back after `invoke`.

MCP is an in-process `tools/list` and `tools/call` boundary. A remote MCP server was not started.

## Consequences

CI does not need a model key. The drafts are deterministic. They are not a substitute for an engineer reading a new failure mode outside this scenario.
