import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST

from wallet.models import Wallet
from . import services
from .forms import (
    AirtimeForm, DataForm, CableVerifyForm, CablePurchaseForm,
    ElectricityVerifyForm, ElectricityPurchaseForm, EducationForm,
)
from .models import VTUOrder


def vtu_home(request):
    return render(request, "vtu/home.html")


# ---------------------------------------------------------------------------
# Shared purchase pipeline
# ---------------------------------------------------------------------------

def _process_purchase(request, service_type, service_id, amount, recipient,
                       variation_code=None, billers_code=None, recipient_name="", extra=None):
    """Debit wallet, call VTpass, reconcile the result. Returns the VTUOrder."""
    wallet, _ = Wallet.objects.get_or_create(user=request.user)

    if wallet.balance < amount:
        messages.error(request, "Insufficient wallet balance. Please fund your wallet first.")
        return None

    request_id = services.generate_request_id()

    order = VTUOrder.objects.create(
        user=request.user,
        service_type=service_type,
        service_id=service_id,
        variation_code=variation_code or "",
        recipient=recipient,
        recipient_name=recipient_name,
        amount=amount,
        request_id=request_id,
        status=VTUOrder.STATUS_PENDING,
    )

    # Debit up front so the balance can't be double-spent across concurrent
    # requests; reversed automatically below if the provider call fails.
    wallet.debit(amount, reference=request_id, description=f"{order.get_service_type_display()}: {recipient}")

    try:
        response = services.purchase(
            service_id=service_id,
            amount=amount,
            phone=recipient if service_type != "electricity" else extra.get("phone", recipient),
            request_id=request_id,
            variation_code=variation_code,
            billers_code=billers_code,
            extra=extra,
        )
    except services.VTUNotConfigured as exc:
        order.status = VTUOrder.STATUS_FAILED
        order.response_message = str(exc)
        order.save(update_fields=["status", "response_message", "updated_at"])
        wallet.credit(amount, reference=request_id, description=f"Refund: {order.get_service_type_display()} not available")
        messages.error(request, "VTU purchases aren't configured yet — the site owner needs to add VTpass API keys.")
        return order
    except Exception as exc:  # network error, timeout, etc.
        order.status = VTUOrder.STATUS_FAILED
        order.response_message = f"Network/provider error: {exc}"
        order.save(update_fields=["status", "response_message", "updated_at"])
        wallet.credit(amount, reference=request_id, description=f"Refund: {order.get_service_type_display()} failed")
        messages.error(request, "We couldn't reach the VTU provider. Your wallet has been refunded.")
        return order

    status = services.transaction_status(response)
    order.status = status
    order.raw_response = json.dumps(response)[:9000]
    order.response_message = response.get("response_description", "")
    txn = (response.get("content") or {}).get("transactions") or {}
    order.provider_transaction_id = str(txn.get("transactionId", ""))
    order.save()

    if status == VTUOrder.STATUS_FAILED:
        wallet.credit(amount, reference=request_id, description=f"Refund: {order.get_service_type_display()} failed")
        messages.error(request, f"Purchase failed: {order.response_message}. Your wallet has been refunded.")
    elif status == VTUOrder.STATUS_SUCCESSFUL:
        messages.success(request, f"{order.get_service_type_display()} purchase successful.")
    else:
        messages.warning(request, "Your purchase is processing. Check order history for the final status shortly.")

    return order


# ---------------------------------------------------------------------------
# Airtime
# ---------------------------------------------------------------------------

@login_required
def buy_airtime(request):
    if request.method == "POST":
        form = AirtimeForm(request.POST)
        if form.is_valid():
            order = _process_purchase(
                request,
                service_type=VTUOrder.SERVICE_AIRTIME,
                service_id=form.cleaned_data["network"],
                amount=form.cleaned_data["amount"],
                recipient=form.cleaned_data["phone"],
            )
            if order:
                return redirect("vtu_order_detail", pk=order.pk)
    else:
        form = AirtimeForm()
    return render(request, "vtu/airtime.html", {"form": form})


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------

@login_required
def buy_data(request):
    if request.method == "POST":
        form = DataForm(request.POST)
        if form.is_valid():
            order = _process_purchase(
                request,
                service_type=VTUOrder.SERVICE_DATA,
                service_id=form.cleaned_data["network"],
                amount=form.cleaned_data["amount"],
                recipient=form.cleaned_data["phone"],
                variation_code=form.cleaned_data["variation_code"],
                billers_code=form.cleaned_data["phone"],
            )
            if order:
                return redirect("vtu_order_detail", pk=order.pk)
    else:
        form = DataForm()
    return render(request, "vtu/data.html", {"form": form})


def api_variations(request, service_id):
    """JSON list of purchasable plans for a service — used by the data/cable pages' JS."""
    try:
        data = services.get_variations(service_id)
    except services.VTUNotConfigured as exc:
        return JsonResponse({"error": str(exc)}, status=503)
    except Exception as exc:
        return JsonResponse({"error": f"Could not load plans: {exc}"}, status=502)
    variations = (data.get("content") or {}).get("variations", [])
    return JsonResponse({"variations": variations})


# ---------------------------------------------------------------------------
# Cable TV
# ---------------------------------------------------------------------------

@login_required
def buy_cable(request):
    if request.method == "POST":
        form = CablePurchaseForm(request.POST)
        if form.is_valid():
            order = _process_purchase(
                request,
                service_type=VTUOrder.SERVICE_CABLE,
                service_id=form.cleaned_data["provider"],
                amount=form.cleaned_data["amount"],
                recipient=form.cleaned_data["smartcard_number"],
                variation_code=form.cleaned_data["variation_code"],
                billers_code=form.cleaned_data["smartcard_number"],
                recipient_name=request.POST.get("recipient_name", ""),
            )
            if order:
                return redirect("vtu_order_detail", pk=order.pk)
    else:
        form = CablePurchaseForm()
    return render(request, "vtu/cable.html", {"form": form, "verify_form": CableVerifyForm()})


@login_required
@require_POST
def api_verify_cable(request):
    form = CableVerifyForm(request.POST)
    if not form.is_valid():
        return JsonResponse({"error": "Invalid input"}, status=400)
    try:
        content = services.verify_merchant(
            form.cleaned_data["provider"], form.cleaned_data["smartcard_number"]
        )
    except services.VTUNotConfigured as exc:
        return JsonResponse({"error": str(exc)}, status=503)
    except services.VTUProviderError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    return JsonResponse({"customer_name": content.get("Customer_Name", "")})


# ---------------------------------------------------------------------------
# Electricity
# ---------------------------------------------------------------------------

@login_required
def buy_electricity(request):
    if request.method == "POST":
        form = ElectricityPurchaseForm(request.POST)
        if form.is_valid():
            order = _process_purchase(
                request,
                service_type=VTUOrder.SERVICE_ELECTRICITY,
                service_id=form.cleaned_data["provider"],
                amount=form.cleaned_data["amount"],
                recipient=form.cleaned_data["meter_number"],
                variation_code=form.cleaned_data["meter_type"],
                billers_code=form.cleaned_data["meter_number"],
                extra={"phone": form.cleaned_data["phone"]},
            )
            if order:
                return redirect("vtu_order_detail", pk=order.pk)
    else:
        form = ElectricityPurchaseForm()
    return render(request, "vtu/electricity.html", {"form": form, "verify_form": ElectricityVerifyForm()})


@login_required
@require_POST
def api_verify_electricity(request):
    form = ElectricityVerifyForm(request.POST)
    if not form.is_valid():
        return JsonResponse({"error": "Invalid input"}, status=400)
    try:
        content = services.verify_merchant(
            form.cleaned_data["provider"],
            form.cleaned_data["meter_number"],
            variation_code=form.cleaned_data["meter_type"],
        )
    except services.VTUNotConfigured as exc:
        return JsonResponse({"error": str(exc)}, status=503)
    except services.VTUProviderError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    return JsonResponse({"customer_name": content.get("Customer_Name", "")})


# ---------------------------------------------------------------------------
# Education (WAEC / JAMB)
# ---------------------------------------------------------------------------

@login_required
def buy_education(request):
    if request.method == "POST":
        form = EducationForm(request.POST)
        if form.is_valid():
            exam_type = form.cleaned_data["exam_type"]
            qty = form.cleaned_data["quantity"]
            plan = {}
            try:
                variations = services.get_variations(exam_type)
                plan = (variations.get("content") or {}).get("variations", [{}])[0]
                unit_price = float(plan.get("variation_amount", 0))
            except Exception:
                unit_price = 0
            amount = unit_price * qty
            order = _process_purchase(
                request,
                service_type=VTUOrder.SERVICE_EDUCATION,
                service_id=exam_type,
                amount=amount,
                recipient=form.cleaned_data["phone"],
                variation_code=plan.get("variation_code", "") if unit_price else None,
                extra={"quantity": qty},
            )
            if order:
                return redirect("vtu_order_detail", pk=order.pk)
    else:
        form = EducationForm()
    return render(request, "vtu/education.html", {"form": form})


# ---------------------------------------------------------------------------
# History
# ---------------------------------------------------------------------------

@login_required
def order_history(request):
    orders = request.user.vtu_orders.all()
    return render(request, "vtu/order_history.html", {"orders": orders})


@login_required
def order_detail(request, pk):
    order = get_object_or_404(VTUOrder, pk=pk, user=request.user)
    return render(request, "vtu/order_detail.html", {"order": order})


@login_required
@require_POST
def order_requery(request, pk):
    """Manually re-check a pending order's final status with the provider."""
    order = get_object_or_404(VTUOrder, pk=pk, user=request.user)
    if order.is_final:
        messages.info(request, "This order already has a final status.")
        return redirect("vtu_order_detail", pk=pk)
    try:
        response = services.requery(order.request_id)
    except services.VTUNotConfigured as exc:
        messages.error(request, str(exc))
        return redirect("vtu_order_detail", pk=pk)
    except Exception as exc:
        messages.error(request, f"Could not reach provider: {exc}")
        return redirect("vtu_order_detail", pk=pk)

    new_status = services.transaction_status(response)
    if new_status != order.status:
        if new_status == VTUOrder.STATUS_FAILED and order.status == VTUOrder.STATUS_PENDING:
            wallet, _ = Wallet.objects.get_or_create(user=request.user)
            wallet.credit(order.amount, reference=order.request_id, description="Refund: order failed on requery")
        order.status = new_status
        order.raw_response = json.dumps(response)[:9000]
        order.save()
    messages.info(request, f"Order status: {order.get_status_display()}")
    return redirect("vtu_order_detail", pk=pk)
