# Serving Course Images (and other media) in Production

## Current architecture

This project uses **local filesystem media storage** — there is no cloud
storage backend configured (no `django-storages`, no S3/GCS settings in
`geniuzlab/settings.py`). This document describes how to serve that local
media correctly in production. No new services are introduced.

```python
# geniuzlab/settings.py
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / "media"
```

`STORAGES["staticfiles"]` uses WhiteNoise, which serves **static** files
(CSS/JS/images shipped with the code) in production. WhiteNoise does **not**
serve `MEDIA_ROOT` (user-uploaded files) — that includes the new
`Course.image` field added in Academy 2.0, as well as pre-existing uploads
like `EnrollmentPayment.receipt` and `PortfolioItem` media.

In `geniuzlab/urls.py`, Django only serves `/media/` itself when
`DEBUG=True`:

```python
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

With `DEBUG=False` (the production setting), nothing in the Django app
serves `/media/` — the web server in front of Gunicorn must do it.

## Required Nginx configuration

Add a `location` block for `/media/` alongside the existing proxy config,
pointing at the same `MEDIA_ROOT` path the Django app writes to:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location /media/ {
        alias /path/to/project/media/;
        expires 30d;
        add_header Cache-Control "public";
    }

    location /static/ {
        alias /path/to/project/staticfiles/;
        expires 30d;
        add_header Cache-Control "public";
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

`/path/to/project/media/` must match `MEDIA_ROOT` exactly, and the Nginx
worker process needs read access to that directory (and the Gunicorn/Django
process needs write access to it, since that's where uploaded course images
land).

## Required Apache configuration

If Apache (with `mod_wsgi` or a reverse proxy to Gunicorn) is used instead:

```apache
Alias /media/ /path/to/project/media/
<Directory /path/to/project/media>
    Require all granted
</Directory>

Alias /static/ /path/to/project/staticfiles/
<Directory /path/to/project/staticfiles>
    Require all granted
</Directory>
```

## Checklist before going live

- [ ] `MEDIA_ROOT` directory exists on the production host and is writable
      by the user Gunicorn runs as.
- [ ] Nginx/Apache `location`/`Alias` for `/media/` added and pointed at the
      exact same path.
- [ ] `python manage.py collectstatic` run for `/static/` (unrelated to
      media, but commonly done at the same deploy step).
- [ ] Confirm `MAX_UPLOAD_SIZE` (used by `validate_image_upload`, the
      validator on `Course.image`) is compatible with the web server's own
      upload size limit (e.g. Nginx `client_max_body_size`).
- [ ] If disk-backed media doesn't fit the hosting setup (e.g. multiple
      app servers with no shared filesystem, ephemeral containers), the
      longer-term fix is a shared object store (S3-compatible) via
      `django-storages` — intentionally **not** added here, since the
      current architecture doesn't use one and introducing it wasn't
      requested. This is a note for future consideration, not a change
      made in this pass.
