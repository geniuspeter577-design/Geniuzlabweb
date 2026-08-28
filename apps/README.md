# Applications

This directory is the target grouping for product-facing applications and
shared client packages. The existing Django apps remain at the repository root
until their package paths are migrated deliberately.

## Current Django apps

`accounts`, `academy`, `konnect`, `motion`, `subs`, `wallet`, `payments`,
`vtu`, `chat`, `notifications`, `automation`, `assistant`, `ai_hub`, and
`dashboard` are currently first-party Django applications.

## Migration rule

Move one Django app at a time. Update `INSTALLED_APPS`, URL includes,
migration dependencies, admin registrations, imports, tests, and deployment
commands as one change. Keep compatibility imports only temporarily and remove
them after a full migration and staging verification.
