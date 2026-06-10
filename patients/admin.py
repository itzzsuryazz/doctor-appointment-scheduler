from django.contrib import admin
from .models import Patient


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ['patient_id', 'full_name', 'age', 'gender', 'noshow_rate']
    search_fields = ['first_name', 'last_name', 'patient_id']
    list_filter = ['gender', 'has_chronic_condition']