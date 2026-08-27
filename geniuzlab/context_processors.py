from django.conf import settings


def feature_flags(request):
    """Exposes feature flags site-wide so templates can hide nav links,
    dashboard quick actions, and buttons for temporarily-disabled
    functionality without every view needing to pass it in.

    Currently just FEATURE_VTU_ENABLED, which gates GeniuzSubs (VTU:
    airtime/data/cable/electricity), wallet funding, and subscription
    checkout. See the flag's definition in settings.py for details.
    """
    return {
        "FEATURE_VTU_ENABLED": getattr(settings, "FEATURE_VTU_ENABLED", False),
    }
