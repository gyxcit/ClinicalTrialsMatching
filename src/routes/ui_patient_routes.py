# src/routes/ui_patient_routes.py
from flask import Blueprint, render_template, request, redirect, url_for, session
patient_bp = Blueprint("patient", __name__)

@patient_bp.get("/patient-profile")
def patient_profile():
        profile = session.get("patient_profile", {})
        return render_template(
            "patient_profile.html",
            layout="app",
            active_page="patient_profile",
            profile=profile,
            workflow_error=session.pop("workflow_error", None)  # optionnel
        )

@patient_bp.post("/patient-profile/save")
def save_patient_profile():
        profile = session.get("patient_profile", {})

        profile["name"] = request.form.get("name", "").strip()
        profile["age"] = request.form.get("age", "").strip()
        profile["gender"] = request.form.get("gender", "").strip()
        profile["diagnosis"] = request.form.get("diagnosis", "").strip()
        profile["stage"] = request.form.get("stage", "").strip()
        profile["ecogStatus"] = request.form.get("ecogStatus", "").strip()
        profile["freeText"] = request.form.get("freeText", "").strip()

        def split_hidden(key: str):
            raw = (request.form.get(key) or "").strip()
            return [x.strip() for x in raw.split("||") if x.strip()] if raw else []

        profile["biomarkers"] = split_hidden("biomarkers")
        profile["priorTreatments"] = split_hidden("priorTreatments")
        profile["comorbidities"] = split_hidden("comorbidities")

        session["patient_profile"] = profile
        session.modified = True

        # ✅ NOUVEAU: lance le workflow et va automatiquement au questionnaire
        return redirect(url_for("workflow.run_from_profile", num_studies=10))

@patient_bp.post("/patient-profile/sample")
def load_sample_profile():
    session["patient_profile"] = {
        "name": "John Doe",
        "age": "58",
        "gender": "Male",
        "diagnosis": "Non-Small Cell Lung Cancer",
        "stage": "Stage IV",
        "ecogStatus": "1",
        "biomarkers": ["PD-L1 High (80%)", "EGFR-"],
        "priorTreatments": ["No prior systemic therapy"],
        "comorbidities": ["Hypertension"],
        "freeText": "Diagnosed recently. Looking for trial options. High PD-L1."
    }
    session.modified = True
    return redirect(url_for("patient.patient_profile"))
