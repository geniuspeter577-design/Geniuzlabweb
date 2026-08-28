"""
Shared file-upload validators.

Use on every ImageField / FileField that accepts user uploads:

    from geniuzlab.validators import validate_image_upload
    avatar = models.ImageField(upload_to="...", validators=[validate_image_upload])

Checks performed:
  - file extension is an allowed image type
  - file size is under the configured limit (MAX_UPLOAD_SIZE, default 5MB)
  - content actually decodes as an image (via Pillow) — blocks a
    ".jpg" that is actually a script/executable, and blocks Pillow
    "decompression bomb" style oversized images.
"""
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.deconstruct import deconstructible

ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "webp"}
ALLOWED_IMAGE_CONTENT_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}


@deconstructible
class FileSizeValidator:
    def __init__(self, max_size=None):
        self.max_size = max_size

    def __call__(self, value):
        max_size = self.max_size or getattr(settings, "MAX_UPLOAD_SIZE", 5 * 1024 * 1024)
        if value.size > max_size:
            raise ValidationError(
                f"File too large ({value.size / (1024 * 1024):.1f}MB). "
                f"Max size is {max_size / (1024 * 1024):.0f}MB."
            )


ALLOWED_DOCUMENT_EXTENSIONS = {
    "pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx", "zip", "rar", "7z",
}
# Design/source files a creative needs to deliver finished work — the
# GeniuzLab chat is meant to handle real project delivery (logos, brand
# kits, video projects), not just office documents.
ALLOWED_SOURCE_EXTENSIONS = {
    "ai", "psd", "eps", "svg", "indd", "xd", "fig", "sketch",
    "cdr", "aep", "prproj", "veg",
}
ALLOWED_VIDEO_EXTENSIONS_CHAT = {"mp4", "mov", "webm", "m4v", "avi", "mkv"}

ALLOWED_ATTACHMENT_EXTENSIONS = (
    ALLOWED_IMAGE_EXTENSIONS
    | ALLOWED_DOCUMENT_EXTENSIONS
    | ALLOWED_SOURCE_EXTENSIONS
    | ALLOWED_VIDEO_EXTENSIONS_CHAT
)


def validate_chat_attachment(value):
    """Looser than validate_image_upload: allows the full range of files a
    client/creative project actually needs to exchange — documents,
    spreadsheets, slide decks, archives, video, and design/source files
    (.ai/.psd/.svg/.fig/etc.) — not just images. Still enforces an
    extension allowlist and the shared size limit (video gets the larger
    MAX_VIDEO_UPLOAD_SIZE ceiling instead of the default)."""
    name = (value.name or "").lower()
    ext = name.rsplit(".", 1)[-1] if "." in name else ""
    if ext not in ALLOWED_ATTACHMENT_EXTENSIONS:
        raise ValidationError(
            f"Unsupported file type '.{ext}'. Allowed: {', '.join(sorted(ALLOWED_ATTACHMENT_EXTENSIONS))}."
        )
    if ext in ALLOWED_VIDEO_EXTENSIONS_CHAT:
        FileSizeValidator(max_size=getattr(settings, "MAX_VIDEO_UPLOAD_SIZE", 60 * 1024 * 1024))(value)
    else:
        FileSizeValidator(max_size=getattr(settings, "MAX_CHAT_ATTACHMENT_SIZE", 25 * 1024 * 1024))(value)


ALLOWED_VIDEO_EXTENSIONS = {"mp4", "mov", "webm", "m4v"}
ALLOWED_VIDEO_CONTENT_TYPES = {"video/mp4", "video/quicktime", "video/webm", "video/x-m4v"}


ALLOWED_RECEIPT_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "webp", "pdf"}
ALLOWED_RECEIPT_CONTENT_TYPES = {
    "image/jpeg", "image/png", "image/gif", "image/webp", "application/pdf",
}


def validate_receipt_upload(value):
    """For payment-receipt uploads (e.g. EnrollmentPayment.receipt): a bank
    transfer receipt is realistically a photo or a PDF, never a video,
    archive, or executable — so this is intentionally narrower than
    validate_chat_attachment. Enforces an extension + content-type
    allowlist and the shared size limit. Unlike validate_image_upload,
    this does not attempt a Pillow decode, since PDFs are a valid and
    expected receipt format here."""
    name = (value.name or "").lower()
    ext = name.rsplit(".", 1)[-1] if "." in name else ""
    if ext not in ALLOWED_RECEIPT_EXTENSIONS:
        raise ValidationError(
            f"Unsupported file type '.{ext}'. Allowed: "
            f"{', '.join(sorted(ALLOWED_RECEIPT_EXTENSIONS))}."
        )
    content_type = getattr(value, "content_type", None)
    if content_type and content_type not in ALLOWED_RECEIPT_CONTENT_TYPES:
        raise ValidationError(f"Unsupported content type '{content_type}'.")
    FileSizeValidator(max_size=getattr(settings, "MAX_UPLOAD_SIZE", 5 * 1024 * 1024))(value)


def validate_project_media(value):
    """Used for Portfolio/Project gallery uploads: accepts either an image
    (validated the same way as validate_image_upload) or a short video file
    (extension/content-type/size checked only — Pillow can't decode video)."""
    name = (value.name or "").lower()
    ext = name.rsplit(".", 1)[-1] if "." in name else ""

    if ext in ALLOWED_IMAGE_EXTENSIONS:
        validate_image_upload(value)
        return

    if ext in ALLOWED_VIDEO_EXTENSIONS:
        content_type = getattr(value, "content_type", None)
        if content_type and content_type not in ALLOWED_VIDEO_CONTENT_TYPES:
            raise ValidationError(f"Unsupported content type '{content_type}'.")
        FileSizeValidator(max_size=getattr(settings, "MAX_VIDEO_UPLOAD_SIZE", 40 * 1024 * 1024))(value)
        return

    allowed = sorted(ALLOWED_IMAGE_EXTENSIONS | ALLOWED_VIDEO_EXTENSIONS)
    raise ValidationError(f"Unsupported file type '.{ext}'. Allowed: {', '.join(allowed)}.")


def validate_image_upload(value):
    """Validate extension, declared content-type, size, and that the bytes
    actually decode as a real image (blocks disguised executables/scripts)."""
    name = (value.name or "").lower()
    ext = name.rsplit(".", 1)[-1] if "." in name else ""
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValidationError(
            f"Unsupported file type '.{ext}'. Allowed: {', '.join(sorted(ALLOWED_IMAGE_EXTENSIONS))}."
        )

    content_type = getattr(value, "content_type", None)
    if content_type and content_type not in ALLOWED_IMAGE_CONTENT_TYPES:
        raise ValidationError(f"Unsupported content type '{content_type}'.")

    FileSizeValidator()(value)

    # Verify the bytes really are an image (Pillow), not just a renamed file.
    from PIL import Image

    try:
        value.seek(0)
        img = Image.open(value)
        img.verify()
    except Exception:
        raise ValidationError("File is not a valid image.")
    finally:
        value.seek(0)
