"""Vues minimales liées à l’authentification du MVP."""

from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def home(request):
    """Page protégée de démonstration, sans implémenter le futur tableau de bord."""
    return render(request, "accounts/home.html")
