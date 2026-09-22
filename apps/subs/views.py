from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST

from .models import SubscriptionPlan, UserSubscription


def subs_home(request):
    plans = SubscriptionPlan.objects.filter(is_active=True)
    return render(request, "pages/subs.html", {"plans": plans})


@login_required
@require_POST
def subscribe(request, pk):
    plan = get_object_or_404(SubscriptionPlan, pk=pk, is_active=True)

    from apps.wallet.models import Wallet
    from django.db import transaction

    wallet, _ = Wallet.objects.get_or_create(user=request.user)
    try:
        with transaction.atomic():
            if UserSubscription.objects.select_for_update().filter(
                user=request.user, plan=plan, status="active"
            ).exists():
                messages.info(request, f"You already have an active {plan.name} subscription.")
                return redirect("subs")
            wallet.debit(plan.price, description=f"Subscription: {plan.name}")
            UserSubscription.objects.create(user=request.user, plan=plan, status="active")
        messages.success(request, f"Subscribed to {plan.name}.")
    except ValueError:
        messages.error(
            request,
            f"Insufficient wallet balance for {plan.name}. Please fund your wallet first."
        )
    except Exception:
        messages.error(request, "Unable to process subscription right now.")

    return redirect("subs")


@login_required
def my_subscriptions(request):
    subs = request.user.subscriptions.select_related("plan")
    return render(request, "subs/my_subscriptions.html", {"subs": subs})
