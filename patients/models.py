from django.db import models


class Patient(models.Model):
    GENDER_CHOICES = [
        ('Male', 'Male'),
        ('Female', 'Female'),
        ('Other', 'Other'),
    ]

    patient_id = models.CharField(max_length=20, unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    age = models.IntegerField()
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    postcode_area = models.CharField(max_length=10)
    distance_to_clinic_km = models.FloatField(default=0.0)
    has_chronic_condition = models.BooleanField(default=False)
    total_appointments = models.IntegerField(default=0)
    previous_noshow_count = models.IntegerField(default=0)
    noshow_rate = models.FloatField(default=0.0)
    days_since_last_visit = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['last_name', 'first_name']

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.patient_id})"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def risk_level(self):
        if self.noshow_rate >= 0.5:
            return 'High'
        elif self.noshow_rate >= 0.25:
            return 'Medium'
        return 'Low'

    def update_stats(self):
        from appointments.models import Appointment
        appts = Appointment.objects.filter(patient=self)
        total = appts.count()
        no_shows = appts.filter(no_show=True).count()
        self.total_appointments = total
        self.previous_noshow_count = no_shows
        self.noshow_rate = round(no_shows / total, 2) if total > 0 else 0.0
        self.save()