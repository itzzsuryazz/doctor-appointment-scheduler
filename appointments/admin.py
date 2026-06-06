from django.contrib import admin
from .models import Appointment, Doctor, Clinic


@admin.register(Clinic)
class ClinicAdmin(admin.ModelAdmin):
    list_display = ['name', 'clinic_type', 'postcode']
    search_fields = ['name', 'clinic_id']


@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'specialty', 'clinic', 'is_active']
    search_fields = ['first_name', 'last_name']


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ['appointment_id', 'patient', 'appointment_date', 'status', 'no_show']
    search_fields = ['appointment_id', 'patient__first_name', 'patient__last_name']
    list_filter = ['status', 'no_show', 'clinic']