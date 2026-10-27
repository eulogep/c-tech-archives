"""Routes d’authentification et de profil de l’application accounts."""

from django.contrib.auth import views as auth_views
from django.urls import path

from . import views


urlpatterns = [
    path("login/", views.ThrottledLoginView.as_view(), name="login"),
    path("signup/", views.signup, name="signup"),
    path("future-improvements/", views.future_improvements, name="future_improvements"),
    path(
        "future-improvements/vote/",
        views.toggle_future_improvement_vote,
        name="toggle_future_improvement_vote",
    ),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("profile/", views.profile, name="profile"),
    path(
        "profile/password/",
        views.AuditedPasswordChangeView.as_view(),
        name="password_change",
    ),
    path("profile/avatar/<int:user_id>/", views.profile_avatar, name="profile_avatar"),
]
