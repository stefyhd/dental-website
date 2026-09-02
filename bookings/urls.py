from django.urls import path
from . import views

urlpatterns = [
    path("", views.booking, name="booking"),
    path("detalii/", views.booking_details, name="booking_details"),
    path("creeaza/", views.create_appointment, name="create_appointment"),
    path("succes/", views.booking_success, name="booking_success"),
]