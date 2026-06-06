from django.db import models
from appointments.models import Appointment


class NoShowPrediction(models.Model):
    appointment = models.OneToOneField(
        Appointment, on_delete=models.CASCADE, related_name='prediction'
    )
    risk_score = models.FloatField()
    risk_label = models.CharField(max_length=10)
    model_version = models.CharField(max_length=20, default='v1.0')
    top_features = models.JSONField(default=dict, blank=True)
    prediction_date = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.appointment} - {self.risk_label} ({self.risk_score:.2f})"

    def save(self, *args, **kwargs):
        if self.risk_score >= 0.6:
            self.risk_label = 'High'
        elif self.risk_score >= 0.35:
            self.risk_label = 'Medium'
        else:
            self.risk_label = 'Low'
        super().save(*args, **kwargs)

    @property
    def risk_percent(self):
        return round(self.risk_score * 100, 1)