from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Patient
from .forms import PatientForm


@login_required
def patient_list(request):
    q = request.GET.get('q', '')
    risk = request.GET.get('risk', '')
    patients = Patient.objects.all().order_by('last_name')
    if q:
        from django.db.models import Q
        patients = patients.filter(
            Q(first_name__icontains=q) |
            Q(last_name__icontains=q) |
            Q(patient_id__icontains=q)
        )
    if risk == 'High':
        patients = patients.filter(noshow_rate__gte=0.5)
    elif risk == 'Medium':
        patients = patients.filter(noshow_rate__gte=0.25, noshow_rate__lt=0.5)
    elif risk == 'Low':
        patients = patients.filter(noshow_rate__lt=0.25)
    return render(request, 'patients/list.html', {'patients': patients, 'q': q, 'risk_filter': risk})


@login_required
def patient_detail(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    appointments = patient.appointments.order_by('-appointment_date')[:20]
    return render(request, 'patients/detail.html', {'patient': patient, 'appointments': appointments})


@login_required
def patient_create(request):
    if request.method == 'POST':
        form = PatientForm(request.POST)
        if form.is_valid():
            patient = form.save(commit=False)
            last = Patient.objects.order_by('-id').first()
            patient.patient_id = f"PAT{(last.id + 1 if last else 1):05d}"
            patient.save()
            messages.success(request, f'Patient {patient.full_name} registered.')
            return redirect('patient_detail', pk=patient.pk)
    else:
        form = PatientForm()
    return render(request, 'patients/create.html', {'form': form})


@login_required
def patient_edit(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    if request.method == 'POST':
        form = PatientForm(request.POST, instance=patient)
        if form.is_valid():
            form.save()
            messages.success(request, 'Patient updated.')
            return redirect('patient_detail', pk=pk)
    else:
        form = PatientForm(instance=patient)
    return render(request, 'patients/edit.html', {'form': form, 'patient': patient})

def patient_register(request):
    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        age = request.POST.get('age', 0)
        gender = request.POST.get('gender', '')
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        postcode_area = request.POST.get('postcode_area', '').strip()
        distance = request.POST.get('distance_to_clinic_km', 0.0)
        has_chronic = request.POST.get('has_chronic_condition') == 'on'

        if not all([first_name, last_name, age, gender, postcode_area]):
            messages.error(request, 'Please fill in all required fields marked with *')
            return render(request, 'registration/register.html')

        try:
            last = Patient.objects.order_by('-id').first()
            new_id = (last.id + 1) if last else 1
            patient_id = f"PAT{new_id:05d}"

            patient = Patient.objects.create(
                patient_id=patient_id,
                first_name=first_name,
                last_name=last_name,
                age=int(age),
                gender=gender,
                email=email,
                phone=phone,
                postcode_area=postcode_area,
                distance_to_clinic_km=float(distance) if distance else 0.0,
                has_chronic_condition=has_chronic,
            )
            messages.success(
                request,
                f'Registration successful! Your Patient ID is {patient.patient_id}. '
                f'Please visit or call the clinic to book your first appointment.'
            )
        except Exception as e:
            messages.error(request, f'Registration failed. Please try again.')

        return render(request, 'registration/register.html')

    return render(request, 'registration/register.html')