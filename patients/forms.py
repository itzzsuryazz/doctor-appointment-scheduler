from django import forms
from .models import Patient


class PatientForm(forms.ModelForm):
    class Meta:
        model = Patient
        fields = [
            'first_name', 'last_name', 'age', 'gender',
            'email', 'phone', 'postcode_area',
            'distance_to_clinic_km', 'has_chronic_condition',
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'age': forms.NumberInput(attrs={'class': 'form-control'}),
            'gender': forms.Select(attrs={'class': 'form-select'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'postcode_area': forms.TextInput(attrs={'class': 'form-control'}),
            'distance_to_clinic_km': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'has_chronic_condition': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }