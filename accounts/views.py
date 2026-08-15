"""Vues liées à l’authentification et au profil privé du MVP."""

from __future__ import annotations

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from .forms import ProfileAvatarForm, SignUpForm


@login_required
def home(request):
    """Page protégée de démonstration, sans implémenter le futur tableau de bord."""

    return render(request, "accounts/home.html")


@require_http_methods(["GET", "POST"])
def signup(request):
    """Inscrit un consultant sans possibilité d’auto-attribution de privilèges."""

    if request.user.is_authenticated:
        return redirect("home")

    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user, backend="accounts.backends.EmailBackend")
            messages.success(request, "Votre compte Consultant a été créé avec succès.")
            return redirect("home")
    else:
        form = SignUpForm()

    return render(request, "registration/signup.html", {"form": form})


@login_required
def profile(request):
    """Permet à l’utilisateur connecté de gérer son unique avatar privé."""

    if request.method == "POST":
        form = ProfileAvatarForm(request.POST, request.FILES)
        if form.is_valid():
            avatar = form.cleaned_data["avatar"]
            request.user.profile_avatar = avatar.read()
            request.user.profile_avatar_content_type = avatar.content_type
            request.user.save(
                update_fields=["profile_avatar", "profile_avatar_content_type"]
            )
            messages.success(request, "Votre photo de profil a été mise à jour.")
            return redirect("profile")
    else:
        form = ProfileAvatarForm()

    return render(request, "accounts/profile.html", {"form": form})


@login_required
def profile_avatar(request, user_id: int):
    """Diffuse l’avatar uniquement au propriétaire authentifié du profil."""

    if request.user.pk != user_id or not request.user.has_profile_avatar:
        raise Http404("Avatar introuvable.")

    response = HttpResponse(
        bytes(request.user.profile_avatar),
        content_type=request.user.profile_avatar_content_type,
    )
    response["Cache-Control"] = "private, no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response
