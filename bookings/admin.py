from django.contrib import admin
from .models import Appointment, Service

admin.site.register(Service)
admin.site.register(Appointment)