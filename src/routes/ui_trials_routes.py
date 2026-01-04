from flask import Blueprint, render_template, request, session
from src.trials import fetch_trials

trials_bp = Blueprint("trials", __name__)

@trials_bp.route("/clinical-trials", methods=["GET", "POST"])
def clinical_trials():
    trials = session.get("trials", [])

    if request.method == "POST":
        condition = request.form.get("condition", "Type 2 diabetes")
        max_studies = int(request.form.get("max_studies", "30"))

        studies = fetch_trials(
            condition=condition,
            max_studies=max_studies,
            return_status=True,
            json_output=False
        ) or []

        session["trials"] = studies
        trials = studies

    favorites = session.get("favorites", [])

    return render_template(
        "clinical_trials.html",
        layout="app",
        active_page="clinical_trials",
        trials=trials,
        favorites=favorites
    )
