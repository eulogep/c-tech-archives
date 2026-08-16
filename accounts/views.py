"""Vues liées à l’authentification et au profil privé du MVP."""

from __future__ import annotations

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.http import Http404, HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods, require_POST

from .forms import ProfileAvatarForm, SignUpForm
from .models import FutureImprovementFeature, FutureImprovementVote


FUTURE_IMPROVEMENTS = (
    {
        "feature": FutureImprovementFeature.SEARCH_OCR,
        "description": "Indexation du contenu numérisé et filtres avancés pour retrouver plus vite un document.",
        "status": "À l’étude",
    },
    {
        "feature": FutureImprovementFeature.SIGNATURE,
        "description": "Circuits de validation traçables pour formaliser les approbations documentaires.",
        "status": "Prévu",
    },
    {
        "feature": FutureImprovementFeature.RETENTION,
        "description": "Alertes sur les échéances d’archivage, de révision et de conservation des dossiers.",
        "status": "Prévu",
    },
    {
        "feature": FutureImprovementFeature.ANALYTICS,
        "description": "Tableaux de bord exportables pour suivre l’activité, les accès et le cycle de vie des archives.",
        "status": "À l’étude",
    },
    {
        "feature": FutureImprovementFeature.SECURITY,
        "description": "Double authentification et revue périodique des droits pour protéger davantage les accès.",
        "status": "À l’étude",
    },
    {
        "feature": FutureImprovementFeature.CONNECTORS,
        "description": "Intégrations contrôlées avec les outils internes de C-Tech et les espaces documentaires autorisés.",
        "status": "Vision",
    },
)


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
def future_improvements(request):
    """Présente la feuille de route et les votes de l’utilisateur connecté."""

    vote_counts = {
        entry["feature"]: entry["total"]
        for entry in FutureImprovementVote.objects.values("feature").annotate(total=Count("id"))
    }
    voted_features = set(
        FutureImprovementVote.objects.filter(user=request.user).values_list("feature", flat=True)
    )
    improvements = [
        {
            **improvement,
            "title": FutureImprovementFeature(improvement["feature"]).label,
            "vote_count": vote_counts.get(improvement["feature"], 0),
            "has_voted": improvement["feature"] in voted_features,
        }
        for improvement in FUTURE_IMPROVEMENTS
    ]
    return render(
        request,
        "accounts/future_improvements.html",
        {"improvements": improvements},
    )


@login_required
@require_POST
def toggle_future_improvement_vote(request):
    """Ajoute ou retire le vote de l’utilisateur, sans exposer les données des votants."""

    feature = request.POST.get("feature", "")
    if feature not in FutureImprovementFeature.values:
        raise Http404("Amélioration introuvable.")

    vote, created = FutureImprovementVote.objects.get_or_create(
        user=request.user,
        feature=feature,
    )
    feature_label = FutureImprovementFeature(feature).label
    if created:
        messages.success(request, f"Votre vote pour « {feature_label} » a été enregistré.")
    else:
        vote.delete()
        messages.info(request, f"Votre vote pour « {feature_label} » a été retiré.")
    return redirect("future_improvements")


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
