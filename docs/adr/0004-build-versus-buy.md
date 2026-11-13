# ADR 0004 — Build the lab, do not apply a platform

## Status

Accepted. Deployment remains NO-GO.

## Context

A warehouse, a BI suite, an orchestration product, and an EKS cluster could host this lab later. None of those were available on the workstation, and this repository is not a factory deployment.

## Decision

Build the control path in Python, SQLite, dbt, and a React workbench. Document EKS and Terraform as an unapplied sketch. Leave the Grafana JSON unimported. The reliability page reads the same counters the `/metrics` text exposes.

## Consequences

The reference environment is the local install in the README. Actions `docker-build` is the image proof after that job is green. Applying the Terraform file would be a different decision, with its own evidence.
