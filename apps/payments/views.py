from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import Transaction
from .services import (
    PaymentConfigurationError,
    PaymentProviderError,
    fulfill_verified_payment,
    initialize_provider_payment,
    verify_provider_payment,
)


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
        provider = request.POST.get("provider", "paystack").strip().lower()
        purpose = request.POST.get("purpose", "wallet_funding")
        description = request.POST.get("description", "")
        amount_raw = request.POST.get("amount", "0")

        try:
            amount = Decimal(amount_raw)
        except (InvalidOperation, TypeError):
            messages.error(request, "Enter a valid amount.")
            return redirect("initiate_payment")

        if amount <= 0 or amount.as_tuple().exponent < -2:
            messages.error(request, "Amount must be greater than zero.")
            return redirect("initiate_payment")

        if provider not in {"paystack", "flutterwave"}:
            messages.error(request, "That payment provider is not available.")
            return redirect("initiate_payment")
        if purpose not in {choice[0] for choice in Transaction.PURPOSE_CHOICES}:
            messages.error(request, "That payment purpose is not available.")
            return redirect("initiate_payment")

        txn = Transaction.objects.create(
            user=request.user,
            provider=provider,
            purpose=purpose,
            amount=amount,
            description=description,
        )

        try:
            checkout_url = initialize_provider_payment(request, txn)
        except (PaymentConfigurationError, PaymentProviderError) as exc:
            txn.status = "failed"
            txn.description = f"Initialization failed: {exc}"[:255]
            txn.save(update_fields=["status", "description", "updated_at"])
            messages.error(request, str(exc))
            return redirect("payment_receipt", reference=txn.reference)
        return redirect(checkout_url)

    providers = settings.PAYMENT_PROVIDERS
    return render(request, "payments/initiate.html", {"providers": providers})


@login_required
def initiate_course_payment(request, slug):
    from apps.academy.models import Course, Enrollment

    course = get_object_or_404(Course, slug=slug, is_published=True)
    if Enrollment.objects.filter(user=request.user, course=course).exists():
        messages.info(request, "You're already enrolled in this course.")
        return redirect("dashboard")
    if request.method != "POST":
        return render(request, "academy/course_payment.html", {"course": course})

    provider = request.POST.get("provider", "paystack").strip().lower()
    if provider not in {"paystack", "flutterwave"}:
        messages.error(request, "That payment provider is not available.")
        return redirect("course_payment", slug=slug)

    txn = Transaction.objects.filter(
        user=request.user, course=course, status="pending",
    ).first()
    if txn:
        try:
            return redirect(initialize_provider_payment(request, txn))
        except (PaymentConfigurationError, PaymentProviderError) as exc:
            messages.error(request, str(exc))
            return redirect("payment_receipt", reference=txn.reference)

    txn = Transaction.objects.create(
        user=request.user,
        course=course,
        provider=provider,
        purpose="course_enrollment",
        amount=course.price,
        description=f"Enrollment: {course.title}",
    )
    try:
        return redirect(initialize_provider_payment(request, txn))
    except (PaymentConfigurationError, PaymentProviderError) as exc:
        txn.status = "failed"
        txn.description = f"Initialization failed: {exc}"[:255]
        txn.save(update_fields=["status", "description", "updated_at"])
        messages.error(request, str(exc))
        return redirect("payment_receipt", reference=txn.reference)


def payment_callback(request, provider):
    reference = request.GET.get("reference") or request.GET.get("tx_ref")
    if not reference:
        return JsonResponse({"ok": False, "error": "Missing payment reference."}, status=400)
    txn = get_object_or_404(Transaction, reference=reference)
    try:
        result = verify_provider_payment(provider, txn, request.GET)
        if not result:
            raise PaymentProviderError("Payment could not be verified.")
        fulfill_verified_payment(txn, result)
    except (PaymentConfigurationError, PaymentProviderError, ValueError) as exc:
        txn.status = "failed"
        txn.description = f"Verification failed: {exc}"[:255]
        txn.save(update_fields=["status", "description", "updated_at"])
        messages.error(request, "Payment verification failed. No access or wallet credit was granted.")
    return redirect("payment_receipt", reference=txn.reference)


@csrf_exempt
@require_POST
def payment_webhook(request, provider):
    try:
        result = verify_provider_payment(provider, None, request.headers, raw_body=request.body)
    except (PaymentConfigurationError, PaymentProviderError, ValueError) as exc:
        return HttpResponse(str(exc), status=400)
    if not result:
        return HttpResponse("Ignored", status=200)
    txn = get_object_or_404(Transaction, reference=result["reference"])
    try:
        fulfill_verified_payment(txn, result)
    except (PaymentProviderError, ValueError) as exc:
        return HttpResponse(str(exc), status=400)
    return HttpResponse("ok", status=200)


@login_required
def payment_receipt(request, reference):
    txn = get_object_or_404(Transaction, reference=reference, user=request.user)
    return render(request, "payments/receipt.html", {"transaction": txn})
