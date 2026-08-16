"""Routes d’authentification et de profil de l’application accounts."""

from django.contrib.auth import views as auth_views
from django.urls import path

from . import views
from .forms import EmailAuthenticationForm


urlpatterns = [
    path(
        "login/",
        auth_views.LoginView.as_view(
            template_name="registration/login.html",
            authentication_form=EmailAuthenticationForm,
            redirect_authenticated_user=True,
        ),
        name="login",
    ),
    path("signup/", views.signup, name="signup"),
    path("future-improvements/", views.future_improvements, name="future_improvements"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("profile/", views.profile, name="profile"),
    path("profile/avatar/<int:user_id>/", views.profile_avatar, name="profile_avatar"),
]
