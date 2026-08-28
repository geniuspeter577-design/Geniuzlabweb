from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone

from .models import Wallet


@login_required
def wallet_home(request):
    wallet, _ = Wallet.objects.get_or_create(user=request.user)
    entries = wallet.entries.all()[:50]

    now = timezone.now()
    month_entries = wallet.entries.filter(created_at__year=now.year, created_at__month=now.month)
    credited = sum((e.amount for e in month_entries if e.type == "credit"), Decimal("0"))
    debited = sum((e.amount for e in month_entries if e.type == "debit"), Decimal("0"))

    return render(request, "wallet/wallet.html", {
        "wallet": wallet,
        "entries": entries,
        "month_credited": credited,
        "month_debited": debited,
    })
