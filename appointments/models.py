from django.db import models
from patients.models import Patient


class Clinic(models.Model):
    CLINIC_TYPE_CHOICES = [
        ('GP', 'GP Practice'),
        ('Physiotherapy', 'Physiotherapy'),
        ('Cardiology', 'Cardiology'),
        ('Dermatology', 'Dermatology'),
        ('Neurology', 'Neurology'),
        ('Orthopaedics', 'Orthopaedics'),
        ('Psychiatry', 'Psychiatry'),
    ]
    clinic_id = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=200)
    clinic_type = models.CharField(max_length=50, choices=CLINIC_TYPE_CHOICES)
    address = models.TextField(blank=True)
    postcode = models.CharField(max_length=10, blank=True)
    phone = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return f"{self.name} ({self.clinic_type})"


class Doctor(models.Model):
    SPECIALTY_CHOICES = [
        ('GP', 'General Practitioner'),
        ('Physiotherapy', 'Physiotherapy'),
        ('Cardiology', 'Cardiology'),
        ('Dermatology', 'Dermatology'),
        ('Neurology', 'Neurology'),
        ('Orthopaedics', 'Orthopaedics'),
        ('Psychiatry', 'Psychiatry'),
    ]
    doctor_id = models.CharField(max_length=20, unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    specialty = models.CharField(max_length=50, choices=SPECIALTY_CHOICES)
    clinic = models.ForeignKey(Clinic, on_delete=models.SET_NULL, null=True)
    email = models.EmailField(blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Dr. {self.first_name} {self.last_name} - {self.specialty}"

    @property
    def full_name(self):
        return f"Dr. {self.first_name} {self.last_name}"


class Appointment(models.Model):
    STATUS_CHOICES = [
        ('Scheduled', 'Scheduled'),
        ('Confirmed', 'Confirmed'),
        ('Completed', 'Completed'),
        ('Cancelled', 'Cancelled'),
        ('No-Show', 'No-Show'),
    ]
    APPOINTMENT_TYPE_CHOICES = [
        ('New Patient', 'New Patient'),
        ('Follow-up', 'Follow-up'),
        ('Emergency', 'Emergency'),
        ('Routine', 'Routine'),
    ]
    REMINDER_RESPONSE_CHOICES = [
        ('Confirmed', 'Confirmed'),
        ('No Response', 'No Response'),
        ('Rescheduled', 'Rescheduled'),
        ('Cancelled', 'Cancelled'),
    ]

    appointment_id = models.CharField(max_length=20, unique=True)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='appointments')
    doctor = models.ForeignKey(Doctor, on_delete=models.SET_NULL, null=True, blank=True)
    clinic = models.ForeignKey(Clinic, on_delete=models.SET_NULL, null=True, blank=True)
    appointment_type = models.CharField(max_length=20, choices=APPOINTMENT_TYPE_CHOICES, default='Follow-up')
    scheduled_date = models.DateField()
    appointment_date = models.DateField()
    appointment_hour = models.IntegerField(default=9)
    consultation_fee_gbp = models.FloatField(default=0.0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Scheduled')
    no_show = models.BooleanField(default=False)
    is_weekend = models.BooleanField(default=False)
    is_peak_hour = models.BooleanField(default=False)
    days_in_advance = models.IntegerField(default=0)
    sms_reminder_sent = models.BooleanField(default=False)
    reminder_hours_before = models.IntegerField(default=24)
    reminder_response = models.CharField(max_length=20, choices=REMINDER_RESPONSE_CHOICES, blank=True)
    number_of_reminders_sent = models.IntegerField(default=0)
    estimated_revenue_loss_gbp = models.FloatField(default=0.0)
    staff_idle_cost_gbp = models.FloatField(default=0.0)
    slot_rebooked = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-appointment_date', '-appointment_hour']

    def __str__(self):
        return f"{self.patient.full_name} - {self.appointment_date}"

    def save(self, *args, **kwargs):
        if self.scheduled_date and self.appointment_date:
            delta = self.appointment_date - self.scheduled_date
            self.days_in_advance = max(delta.days, 0)
        if self.appointment_date:
            self.is_weekend = self.appointment_date.weekday() >= 5
        if self.appointment_hour:
            self.is_peak_hour = (9 <= self.appointment_hour <= 11) or (17 <= self.appointment_hour <= 19)
        super().save(*args, **kwargs)

    @property
    def appointment_day_of_week(self):
        return self.appointment_date.strftime('%A') if self.appointment_date else ''