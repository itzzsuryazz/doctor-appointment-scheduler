import os
import pandas as pd
from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone


class Command(BaseCommand):
    help = 'Import CSV data and train ML model'

    def add_arguments(self, parser):
        parser.add_argument('--csv', type=str, default=str(settings.TRAINING_DATA_PATH))
        parser.add_argument('--limit', type=int, default=500)
        parser.add_argument('--train', action='store_true')

    def handle(self, *args, **options):
        from patients.models import Patient
        from appointments.models import Appointment, Clinic, Doctor

        csv_path = options['csv']
        if not os.path.exists(csv_path):
            self.stderr.write(f'CSV not found: {csv_path}')
            return

        self.stdout.write(f'Loading {csv_path}...')
        df = pd.read_csv(csv_path).head(options['limit'])
        self.stdout.write(f'Loaded {len(df)} records')

        clinic_map = {}
        for clinic_id in df['clinic_id'].unique():
            rows = df[df['clinic_id'] == clinic_id]
            clinic_type = rows['clinic_type'].iloc[0]
            clinic, _ = Clinic.objects.get_or_create(
                clinic_id=str(clinic_id),
                defaults={
                    'name': f'{clinic_type} Clinic {clinic_id}',
                    'clinic_type': clinic_type,
                    'postcode': str(rows['postcode_area'].iloc[0]),
                }
            )
            clinic_map[clinic_id] = clinic
        self.stdout.write(f'  {len(clinic_map)} clinics done')

        doctor_map = {}
        for clinic_id, clinic in clinic_map.items():
            doctor, _ = Doctor.objects.get_or_create(
                doctor_id=f'DR_{clinic_id}',
                defaults={
                    'first_name': 'Doctor',
                    'last_name': clinic.clinic_type,
                    'specialty': clinic.clinic_type if clinic.clinic_type in [
                        'GP','Physiotherapy','Cardiology',
                        'Dermatology','Neurology','Orthopaedics','Psychiatry'
                    ] else 'GP',
                    'clinic': clinic,
                }
            )
            doctor_map[clinic_id] = doctor
        self.stdout.write(f'  {len(doctor_map)} doctors done')

        patient_map = {}
        for pid in df['patient_id'].unique():
            rows = df[df['patient_id'] == pid]
            row = rows.iloc[0]
            patient, _ = Patient.objects.get_or_create(
                patient_id=f'PAT{int(pid):05d}',
                defaults={
                    'first_name': 'Patient',
                    'last_name': f'{int(pid):05d}',
                    'age': int(row['age']),
                    'gender': row['gender'],
                    'postcode_area': str(row['postcode_area']),
                    'distance_to_clinic_km': float(row['distance_to_clinic_km']),
                    'has_chronic_condition': bool(row['has_chronic_condition_flag']),
                    'total_appointments': int(row['patient_total_appointments']),
                    'previous_noshow_count': int(row['patient_previous_noshow_count']),
                    'noshow_rate': float(row['patient_noshow_rate']),
                    'days_since_last_visit': int(row['days_since_last_visit']),
                }
            )
            patient_map[pid] = patient
        self.stdout.write(f'  {len(patient_map)} patients done')

        created_count = 0
        for _, row in df.iterrows():
            appt_id = f'APT{int(row["appointment_id"]):05d}'
            if Appointment.objects.filter(appointment_id=appt_id).exists():
                continue
            patient = patient_map.get(row['patient_id'])
            clinic = clinic_map.get(row['clinic_id'])
            doctor = doctor_map.get(row['clinic_id'])
            if not patient:
                continue
            try:
                appt_date = pd.to_datetime(row['appointment_date']).date()
                sched_date = pd.to_datetime(row['scheduled_date']).date()
            except Exception:
                continue

            reminder_resp = str(row.get('reminder_response', ''))
            if reminder_resp not in ['Confirmed', 'No Response', 'Rescheduled', 'Cancelled']:
                reminder_resp = 'No Response'

            appt_type = row['appointment_type']
            if appt_type not in ['New Patient', 'Follow-up', 'Emergency', 'Routine']:
                appt_type = 'Follow-up'

            Appointment.objects.create(
                appointment_id=appt_id,
                patient=patient,
                doctor=doctor,
                clinic=clinic,
                appointment_type=appt_type,
                scheduled_date=sched_date,
                appointment_date=appt_date,
                appointment_hour=int(row['appointment_hour']),
                consultation_fee_gbp=float(row['consultation_fee_gbp']),
                status='Completed' if appt_date < timezone.now().date() else 'Scheduled',
                no_show=bool(row['no_show']),
                is_weekend=bool(row['is_weekend']),
                is_peak_hour=bool(row['is_peak_hour']),
                days_in_advance=int(row['days_in_advance']),
                sms_reminder_sent=bool(row['sms_reminder_sent']),
                reminder_hours_before=int(row['reminder_hours_before']),
                reminder_response=reminder_resp,
                number_of_reminders_sent=int(row['number_of_reminders_sent']),
                estimated_revenue_loss_gbp=float(row['estimated_revenue_loss_gbp']),
                staff_idle_cost_gbp=float(row['staff_idle_cost_gbp']),
                slot_rebooked=bool(row['slot_rebooked_flag']),
            )
            created_count += 1

        self.stdout.write(f'  {created_count} appointments done')
        self.stdout.write(self.style.SUCCESS('Import complete!'))

        if options['train']:
            self.stdout.write('Training ML model...')
            import shutil
            dst = str(settings.TRAINING_DATA_PATH)
            if csv_path != dst:
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy(csv_path, dst)
            from ml_model.predictor import train_model
            metrics = train_model()
            if metrics:
                self.stdout.write(self.style.SUCCESS(
                    f"Model trained! ROC-AUC: {metrics['roc_auc']} Accuracy: {metrics['accuracy']}"
                ))
            else:
                self.stderr.write('Training failed.')