from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum
from django.utils import timezone
import json

from .models import Appointment, Doctor, Clinic
from .forms import AppointmentForm, AppointmentStatusForm
from patients.models import Patient
from predictions.models import NoShowPrediction
from ml_model.predictor import predict_no_show


@login_required
def dashboard(request):
    today = timezone.now().date()
    total_appointments = Appointment.objects.count()
    total_no_shows = Appointment.objects.filter(no_show=True).count()
    no_show_rate = round((total_no_shows / total_appointments * 100), 1) if total_appointments > 0 else 0
    total_patients = Patient.objects.count()

    upcoming = Appointment.objects.filter(
        appointment_date__gte=today,
        status__in=['Scheduled', 'Confirmed']
    ).select_related('patient', 'doctor').order_by('appointment_date')[:10]

    revenue_loss = Appointment.objects.filter(
        no_show=True
    ).aggregate(total=Sum('estimated_revenue_loss_gbp'))['total'] or 0

    from collections import defaultdict
    day_stats = defaultdict(lambda: {'total': 0, 'no_show': 0})
    for appt in Appointment.objects.all():
        day = appt.appointment_day_of_week
        day_stats[day]['total'] += 1
        if appt.no_show:
            day_stats[day]['no_show'] += 1

    days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    day_chart_data = {
        'labels': days_order,
        'no_show_rates': [
            round(day_stats[d]['no_show'] / day_stats[d]['total'] * 100, 1)
            if day_stats[d]['total'] > 0 else 0
            for d in days_order
        ]
    }

    high = NoShowPrediction.objects.filter(risk_label='High').count()
    medium = NoShowPrediction.objects.filter(risk_label='Medium').count()
    low = NoShowPrediction.objects.filter(risk_label='Low').count()

    clinic_stats = []
    for clinic in Clinic.objects.all():
        total = Appointment.objects.filter(clinic=clinic).count()
        no_show = Appointment.objects.filter(clinic=clinic, no_show=True).count()
        clinic_stats.append({
            'name': clinic.name,
            'total': total,
            'no_show': no_show,
            'rate': round(no_show / total * 100, 1) if total > 0 else 0,
        })

    context = {
        'total_appointments': total_appointments,
        'total_no_shows': total_no_shows,
        'no_show_rate': no_show_rate,
        'total_patients': total_patients,
        'upcoming': upcoming,
        'revenue_loss': round(revenue_loss, 2),
        'day_chart_data': json.dumps(day_chart_data),
        'risk_distribution': json.dumps({'high': high, 'medium': medium, 'low': low}),
        'clinic_stats': clinic_stats,
        'today': today,
    }
    return render(request, 'dashboard/dashboard.html', context)


@login_required
def appointment_list(request):
    appointments = Appointment.objects.select_related(
        'patient', 'doctor', 'clinic'
    ).order_by('-appointment_date')
    status = request.GET.get('status')
    if status:
        appointments = appointments.filter(status=status)
    clinics = Clinic.objects.all()
    return render(request, 'appointments/list.html', {
        'appointments': appointments[:100],
        'clinics': clinics,
    })


@login_required
def appointment_detail(request, pk):
    appointment = get_object_or_404(Appointment, pk=pk)
    try:
        prediction = appointment.prediction
    except NoShowPrediction.DoesNotExist:
        prediction = None

    if request.method == 'POST':
        form = AppointmentStatusForm(request.POST, instance=appointment)
        if form.is_valid():
            appt = form.save()
            if appt.no_show:
                appt.estimated_revenue_loss_gbp = appt.consultation_fee_gbp
                appt.staff_idle_cost_gbp = round(appt.consultation_fee_gbp * 0.35, 2)
                appt.save()
            appt.patient.update_stats()
            messages.success(request, 'Appointment updated.')
            return redirect('appointment_detail', pk=pk)
    else:
        form = AppointmentStatusForm(instance=appointment)

    return render(request, 'appointments/detail.html', {
        'appointment': appointment,
        'prediction': prediction,
        'form': form,
    })


@login_required
def appointment_create(request):
    if request.method == 'POST':
        form = AppointmentForm(request.POST)
        if form.is_valid():
            appointment = form.save(commit=False)
            last = Appointment.objects.order_by('-id').first()
            appointment.appointment_id = f"APT{(last.id + 1 if last else 1):05d}"
            appointment.save()

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
            NoShowPrediction.objects.create(
                appointment=appointment,
                risk_score=result['risk_score'],
                top_features=result.get('top_features', {}),
            )
            messages.success(request, f'Appointment booked! Risk: {result["risk_label"]}')
            return redirect('appointment_detail', pk=appointment.pk)
    else:
        form = AppointmentForm(initial={'scheduled_date': timezone.now().date()})

    return render(request, 'appointments/create.html', {'form': form})


@login_required
def appointment_cancel(request, pk):
    appointment = get_object_or_404(Appointment, pk=pk)
    if request.method == 'POST':
        appointment.status = 'Cancelled'
        appointment.save()
        messages.info(request, 'Appointment cancelled.')
        return redirect('appointment_list')
    return render(request, 'appointments/confirm_cancel.html', {'appointment': appointment})


@login_required
def send_reminder(request, pk):
    appointment = get_object_or_404(Appointment, pk=pk)
    appointment.sms_reminder_sent = True
    appointment.number_of_reminders_sent += 1
    appointment.save()
    messages.success(request, 'Reminder sent!')
    return redirect('appointment_detail', pk=pk)