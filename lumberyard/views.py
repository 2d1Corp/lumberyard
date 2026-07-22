from django.contrib.auth.decorators import login_required
from django.shortcuts import render


def index(request):
    return render(request, "lumberyard/index.html")


@login_required
def dashboard(request):
    return render(request, "lumberyard/dashboard.html")