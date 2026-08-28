# Infrastructure

This directory is reserved for deployment and operational assets.

Planned contents include:

- CI workflows for checks, tests, migrations, and static collection
- container/process definitions for web, worker, beat, and scheduler services
- reverse-proxy and deployment configuration
- observability, health checks, and backup/restore runbooks

Production secrets must remain outside the repository. Use the environment
contract in `DOCs/OPERATIONS.md`.
