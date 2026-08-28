# Frontend

This directory is reserved for a dedicated browser client when the product
needs one. The current browser experience is Django-template based and remains
in the root `templates/` and `static/` directories.

## Migration rule

A frontend extraction must preserve authentication, CSRF, URL contracts, file
uploads, SSE behavior, and progressive enhancement. Choose a framework and
build tool only when a concrete workflow benefits from it; do not duplicate
server-rendered pages without an agreed API boundary.

## First planned boundary

Document API contracts before moving UI code. The likely first candidates are
AI Hub JSON/SSE endpoints and authenticated dashboard interactions, because
those already expose machine-readable responses.
