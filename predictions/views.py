from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Avg, Count
from .models import NoShowPrediction
from appointments.models import Appointment
from ml_model.predictor import train_model, get_model_metrics, predict_no_show


@login_required
def predictions_dashboard(request):
    metrics = get_model_metrics()
    total_predictions = NoShowPrediction.objects.count()
    avg_risk = NoShowPrediction.objects.aggregate(avg=Avg('risk_score'))['avg'] or 0
    high_risk = NoShowPrediction.objects.filter(risk_label='High').count()
    medium_risk = NoShowPrediction.objects.filter(risk_label='Medium').count()
    low_risk = NoShowPrediction.objects.filter(risk_label='Low').count()

    high_risk_appointments = NoShowPrediction.objects.filter(
        risk_label='High'
    ).select_related('appointment__patient', 'appointment__clinic').order_by('-risk_score')[:20]

    context = {
        'metrics': metrics,
        'total_predictions': total_predictions,
        'avg_risk': round(avg_risk * 100, 1),
        'high_risk': high_risk,
        'medium_risk': medium_risk,
        'low_risk': low_risk,
        'high_risk_appointments': high_risk_appointments,
    }
    return render(request, 'predictions/dashboard.html', context)


@login_required
def train_model_view(request):
    if request.method == 'POST':
        metrics = train_model()
        if metrics:
            messages.success(request, f"Model trained! ROC-AUC: {metrics.get('roc_auc')} Accuracy: {metrics.get('accuracy')}")
        else:
            messages.error(request, 'Training failed. Check that CSV is in ml_model folder.')
        return redirect('predictions_dashboard')
    return render(request, 'predictions/train.html', {'metrics': get_model_metrics()})


@login_required
def bulk_predict(request):
    if request.method == 'POST':
        from django.utils import timezone
        today = timezone.now().date()
        upcoming = Appointment.objects.filter(
            appointment_date__gte=today,
            status__in=['Scheduled', 'Confirmed']
        ).select_related('patient', 'clinic')

        updated = 0
        for appointment in upcoming:
            patient = appointment.patient
            pred_data = {
                'age': patient.age,
                'gender': patient.gender,
                'distance_to_clinic_km': patient.distance_to_clinic_km,
                'days_in_advance': appointment.days_in_advance,
                'appointment_hour': appointment.appointment_hour,
                'is_weekend': int(appointment.is_weekend),
                'is_peak_hour': int(appointment.is_peak_hour),
                'patient_total_appointments': patient.total_appointments,
                'patient_previous_noshow_count': patient.previous_noshow_count,
                'patient_noshow_rate': patient.noshow_rate,
                'days_since_last_visit': patient.days_since_last_visit,
                'has_chronic_condition_flag': int(patient.has_chronic_condition),
                'sms_reminder_sent': int(appointment.sms_reminder_sent),
                'reminder_hours_before': appointment.reminder_hours_before,
                'number_of_reminders_sent': appointment.number_of_reminders_sent,
                'clinic_type': appointment.clinic.clinic_type if appointment.clinic else 'GP',
                'appointment_type': appointment.appointment_type,
                'day_of_week': appointment.appointment_day_of_week,
            }
            result = predict_no_show(pred_data)
            NoShowPrediction.objects.update_or_create(
                appointment=appointment,
                defaults={
                    'risk_score': result['risk_score'],
                    'top_features': result.get('top_features', {})
                }
            )
            updated += 1

        messages.success(request, f'Predictions updated for {updated} appointments.')
        return redirect('predictions_dashboard')

    return render(request, 'predictions/bulk_predict.html')