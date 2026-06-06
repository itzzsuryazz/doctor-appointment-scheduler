from django.contrib import admin
from .models import NoShowPrediction


@admin.register(NoShowPrediction)
class NoShowPredictionAdmin(admin.ModelAdmin):
    list_display = ['appointment', 'risk_score', 'risk_label', 'prediction_date']
    list_filter = ['risk_label']
    search_fields = ['appointment__appointment_id']