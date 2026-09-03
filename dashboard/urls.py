from django.contrib.auth.views import LoginView, LogoutView
from django.urls import path
from . import views

urlpatterns = [
   path(
    "login/",
    LoginView.as_view(
        template_name="dashboard/login.html",
        redirect_authenticated_user=True,
        next_page="dashboard_home",
    ),
    name="dashboard_login",
    ),

    path(
        "logout/",
        LogoutView.as_view(next_page="dashboard_login"),
        name="dashboard_logout",
    ),

    path("", views.home, name="dashboard_home"),

    path("confirm/<int:appointment_id>/", views.confirm_appointment, name="confirm_appointment"),
    path("reject/<int:appointment_id>/", views.reject_appointment, name="reject_appointment"),

    path("manual/", views.manual_appointment, name="manual_appointment"),
    path("appointments/", views.appointments, name="dashboard_appointments"),
    path("schedule/", views.schedule, name="dashboard_schedule"),
    path("services/", views.services, name="dashboard_services"),
    path("schedule/block/<int:block_id>/delete/", views.delete_schedule_block, name="delete_schedule_block"),
    path(
    "appointments/<int:appointment_id>/edit/",
    views.appointment_edit,
    name="appointment_edit",
    ),
    path(
        "appointments/<int:appointment_id>/delete/",
        views.appointment_delete,
        name="appointment_delete",
    ),

    path(
        "services/new/",
        views.service_create,
        name="service_create",
    ),
    path(
        "services/<int:service_id>/edit/",
        views.service_edit,
        name="service_edit",
    ),
    path(
        "services/<int:service_id>/delete/",
        views.service_delete,
        name="service_delete",
    ),
    path(
        "patients/search/",
        views.patient_search,
        name="patient_search",
    ),
    path("patients/", views.patients, name="dashboard_patients"),
    path("patients/<int:patient_id>/", views.patient_detail, name="patient_detail"),
    path(
        "refresh-statuses/",
        views.refresh_statuses,
        name="refresh_statuses",
    ),
    path(
        "appointments/<int:appointment_id>/status/",
        views.appointment_status,
        name="appointment_status",
    ),
    path(
        "manual/day-data/",
        views.manual_day_data,
        name="manual_day_data",
    ),
    path(
        "schedule/block-times/",
        views.schedule_block_times,
        name="schedule_block_times",
    ),
    ]