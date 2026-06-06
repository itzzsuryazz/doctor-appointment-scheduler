from django import forms
from django.utils import timezone
from .models import Appointment


class AppointmentForm(forms.ModelForm):
    appointment_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    scheduled_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        initial=timezone.now().date
    )

    class Meta:
        model = Appointment
        fields = [
            'patient', 'doctor', 'clinic', 'appointment_type',
            'scheduled_date', 'appointment_date', 'appointment_hour',
            'consultation_fee_gbp', 'sms_reminder_sent',
            'reminder_hours_before', 'notes',
        ]
        widgets = {
            'patient': forms.Select(attrs={'class': 'form-select'}),
            'doctor': forms.Select(attrs={'class': 'form-select'}),
            'clinic': forms.Select(attrs={'class': 'form-select'}),
            'appointment_type': forms.Select(attrs={'class': 'form-select'}),
            'appointment_hour': forms.NumberInput(attrs={'class': 'form-control', 'min': 8, 'max': 18}),
            'consultation_fee_gbp': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'sms_reminder_sent': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'reminder_hours_before': forms.Select(
                choices=[(12, '12 hours'), (24, '24 hours'), (48, '48 hours'), (72, '72 hours')],
                attrs={'class': 'form-select'}
            ),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class AppointmentStatusForm(forms.ModelForm):
    class Meta:
        model = Appointment
        fields = ['status', 'no_show', 'slot_rebooked', 'notes']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select'}),
            'no_show': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'slot_rebooked': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }