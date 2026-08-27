from django.shortcuts import render
from .models import MotionShowcase


def motion_home(request):
    showcase = MotionShowcase.objects.all()[:6]
    return render(request, "pages/motion.html", {"showcase": showcase})
