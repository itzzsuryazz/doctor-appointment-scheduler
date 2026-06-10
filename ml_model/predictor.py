import os
import pickle
import logging
import numpy as np
import pandas as pd
from pathlib import Path
from django.conf import settings

logger = logging.getLogger(__name__)

FEATURE_COLUMNS = [
    'age', 'gender_encoded', 'distance_to_clinic_km', 'days_in_advance',
    'appointment_hour', 'is_weekend', 'is_peak_hour',
    'patient_total_appointments', 'patient_previous_noshow_count',
    'patient_noshow_rate', 'days_since_last_visit',
    'has_chronic_condition_flag', 'sms_reminder_sent',
    'reminder_hours_before', 'number_of_reminders_sent',
    'clinic_type_encoded', 'appointment_type_encoded',
    'day_of_week_encoded',
]

GENDER_MAP = {'Male': 0, 'Female': 1, 'Other': 2}
CLINIC_TYPE_MAP = {
    'GP': 0, 'Physiotherapy': 1, 'Cardiology': 2,
    'Dermatology': 3, 'Neurology': 4, 'Orthopaedics': 5, 'Psychiatry': 6,
}
APPT_TYPE_MAP = {
    'New Patient': 0, 'Follow-up': 1, 'Emergency': 2, 'Routine': 3
}
DAY_MAP = {
    'Monday': 0, 'Tuesday': 1, 'Wednesday': 2, 'Thursday': 3,
    'Friday': 4, 'Saturday': 5, 'Sunday': 6,
}


def train_model():
    try:
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.model_selection import train_test_split
        from sklearn.preprocessing import StandardScaler
        from sklearn.metrics import classification_report, roc_auc_score
        import warnings
        warnings.filterwarnings('ignore')

        csv_path = settings.TRAINING_DATA_PATH
        if not os.path.exists(csv_path):
            logger.error(f"CSV not found: {csv_path}")
            return None

        df = pd.read_csv(csv_path)
        logger.info(f"Loaded {len(df)} records")

        df['gender_encoded'] = df['gender'].map(GENDER_MAP).fillna(2)
        df['clinic_type_encoded'] = df['clinic_type'].map(CLINIC_TYPE_MAP).fillna(0)
        df['appointment_type_encoded'] = df['appointment_type'].map(APPT_TYPE_MAP).fillna(1)
        df['day_of_week_encoded'] = df['appointment_day_of_week'].map(DAY_MAP).fillna(0)
        df = df.fillna(0)

        X = df[FEATURE_COLUMNS].copy()
        y = df['no_show'].astype(int)

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )

        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)

        model = RandomForestClassifier(
            n_estimators=200, max_depth=12,
            class_weight='balanced', random_state=42, n_jobs=-1
        )
        model.fit(X_train_scaled, y_train)

        y_pred = model.predict(X_test_scaled)
        y_prob = model.predict_proba(X_test_scaled)[:, 1]
        roc_auc = roc_auc_score(y_test, y_prob)
        report = classification_report(y_test, y_pred, output_dict=True)

        model_dir = Path(settings.ML_MODEL_PATH).parent
        model_dir.mkdir(parents=True, exist_ok=True)

        with open(settings.ML_MODEL_PATH, 'wb') as f:
            pickle.dump(model, f)
        with open(settings.ML_SCALER_PATH, 'wb') as f:
            pickle.dump(scaler, f)

        metrics = {
            'roc_auc': round(roc_auc, 4),
            'accuracy': round(report['accuracy'], 4),
            'precision': round(report['1']['precision'], 4),
            'recall': round(report['1']['recall'], 4),
            'f1_score': round(report['1']['f1-score'], 4),
        }

        metrics_path = model_dir / 'metrics.pkl'
        with open(metrics_path, 'wb') as f:
            pickle.dump(metrics, f)

        logger.info("Model saved successfully")
        return metrics

    except Exception as e:
        logger.exception(f"Training error: {e}")
        return None


def load_model():
    try:
        if not os.path.exists(settings.ML_MODEL_PATH):
            return None, None
        with open(settings.ML_MODEL_PATH, 'rb') as f:
            model = pickle.load(f)
        with open(settings.ML_SCALER_PATH, 'rb') as f:
            scaler = pickle.load(f)
        return model, scaler
    except Exception as e:
        logger.exception(f"Load error: {e}")
        return None, None


def predict_no_show(appointment_data: dict) -> dict:
    model, scaler = load_model()
    if model is None:
        return _heuristic_predict(appointment_data)

    try:
        features = {
            'age': appointment_data.get('age', 35),
            'gender_encoded': GENDER_MAP.get(appointment_data.get('gender', 'Male'), 0),
            'distance_to_clinic_km': appointment_data.get('distance_to_clinic_km', 5.0),
            'days_in_advance': appointment_data.get('days_in_advance', 7),
            'appointment_hour': appointment_data.get('appointment_hour', 10),
            'is_weekend': int(appointment_data.get('is_weekend', 0)),
            'is_peak_hour': int(appointment_data.get('is_peak_hour', 0)),
            'patient_total_appointments': appointment_data.get('patient_total_appointments', 1),
            'patient_previous_noshow_count': appointment_data.get('patient_previous_noshow_count', 0),
            'patient_noshow_rate': appointment_data.get('patient_noshow_rate', 0.0),
            'days_since_last_visit': appointment_data.get('days_since_last_visit', 0),
            'has_chronic_condition_flag': int(appointment_data.get('has_chronic_condition_flag', 0)),
            'sms_reminder_sent': int(appointment_data.get('sms_reminder_sent', 1)),
            'reminder_hours_before': appointment_data.get('reminder_hours_before', 24),
            'number_of_reminders_sent': appointment_data.get('number_of_reminders_sent', 1),
            'clinic_type_encoded': CLINIC_TYPE_MAP.get(appointment_data.get('clinic_type', 'GP'), 0),
            'appointment_type_encoded': APPT_TYPE_MAP.get(appointment_data.get('appointment_type', 'Follow-up'), 1),
            'day_of_week_encoded': DAY_MAP.get(appointment_data.get('day_of_week', 'Monday'), 0),
        }

        X = np.array([[features[col] for col in FEATURE_COLUMNS]])
        X_scaled = scaler.transform(X)
        risk_score = float(model.predict_proba(X_scaled)[0][1])

        importances = model.feature_importances_
        top_features = dict(
            sorted(
                {FEATURE_COLUMNS[i]: round(float(importances[i]), 4) for i in range(len(FEATURE_COLUMNS))}.items(),
                key=lambda x: x[1], reverse=True
            )[:5]
        )

        return {
            'risk_score': round(risk_score, 4),
            'risk_label': 'High' if risk_score >= 0.6 else ('Medium' if risk_score >= 0.35 else 'Low'),
            'top_features': top_features,
            'model_used': 'RandomForest',
        }

    except Exception as e:
        logger.exception(f"Prediction error: {e}")
        return _heuristic_predict(appointment_data)


def _heuristic_predict(data: dict) -> dict:
    score = 0.15
    if data.get('patient_noshow_rate', 0) > 0.3:
        score += 0.25
    if data.get('days_in_advance', 7) > 14:
        score += 0.10
    if not data.get('sms_reminder_sent', True):
        score += 0.10
    if data.get('is_weekend', 0):
        score += 0.05
    if data.get('patient_previous_noshow_count', 0) > 2:
        score += 0.15
    score = min(score, 0.95)
    return {
        'risk_score': round(score, 4),
        'risk_label': 'High' if score >= 0.6 else ('Medium' if score >= 0.35 else 'Low'),
        'top_features': {},
        'model_used': 'Heuristic',
    }


def get_model_metrics() -> dict:
    metrics_path = Path(settings.ML_MODEL_PATH).parent / 'metrics.pkl'
    if os.path.exists(metrics_path):
        with open(metrics_path, 'rb') as f:
            return pickle.load(f)
    return {}