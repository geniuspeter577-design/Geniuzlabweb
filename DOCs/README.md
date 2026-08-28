# GeniuzLab Project Docs

This directory is the maintained orientation point for the project. Read in this order:

1. [Architecture](ARCHITECTURE.md) for ownership boundaries and request/data flow.
2. [Operations](OPERATIONS.md) for local setup, environment configuration, deployment checks, and scheduled jobs.
3. [Testing](TESTING.md) for the current verification contract and coverage gaps.
4. [Roadmap](ROADMAP.md) for the recommended path from current state to production readiness.

The restructuring foundations are described in the directory guides:
[`backend/`](../backend/README.md), [`apps/`](../apps/README.md),
[`frontend/`](../frontend/README.md), [`mobile/`](../mobile/README.md), and
[`infra/`](../infra/README.md).

The root [audit_result.md](../audit_result.md) records the dated engineering assessment and evidence behind the readiness decision. Update it when a release blocker changes, rather than allowing older phase notes to become the only source of truth.
