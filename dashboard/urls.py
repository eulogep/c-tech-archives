"""Routes du tableau de bord."""

from django.urls import path

from . import views


urlpatterns = [
    path("", views.home, name="home"),
]
