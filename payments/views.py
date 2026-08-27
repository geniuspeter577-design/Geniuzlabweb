import uuid
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404

from .models import Transaction


@login_required
def transaction_history(request):
    transactions = request.user.transactions.all()
    return render(request, "payments/history.html", {"transactions": transactions})


@login_required
def initiate_payment(request):
    """
    Foundation for real gateway integration. Providers are configured via
    environment variables (see settings.py / .env.example). Until live keys
    are added, this creates a pending transaction record so the rest of the
    platform (receipts, history, wallet crediting) is fully wired and ready.
    """
    if request.method == "POST":
        provider = request.POST.get("provider", "paystack")
        purpose = request.POST.get("purpose", "wallet_funding")
        description = request.POST.get("description", "")
        amount_raw = request.POST.get("amount", "0")

        try:
            amount = Decimal(amount_raw)
        except (InvalidOperation, TypeError):
            messages.error(request, "Enter a valid amount.")
            return redirect("initiate_payment")

        if amount <= 0:
            messages.error(request, "Amount must be greater than zero.")
            return redirect("initiate_payment")

        txn = Transaction.objects.create(
            user=request.user,
            reference=str(uuid.uuid4()),
            provider=provider,
            purpose=purpose,
            amount=amount,
            description=description,
        )

        configured = bool(
            getattr(settings, "PAYMENT_PROVIDERS", {}).get(provider, {}).get("secret_key")
        )
        if not configured:
            messages.info(
                request,
                f"{txn.get_provider_display()} keys are not configured yet. "
                "Your transaction was recorded as pending — add API keys in "
                "the environment to enable live checkout.",
            )
        return redirect("payment_receipt", reference=txn.reference)

    providers = settings.PAYMENT_PROVIDERS
    return render(request, "payments/initiate.html", {"providers": providers})


@login_required
def payment_receipt(request, reference):
    txn = get_object_or_404(Transaction, reference=reference, user=request.user)
    return render(request, "payments/receipt.html", {"transaction": txn})
