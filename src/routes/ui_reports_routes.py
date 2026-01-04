from flask import Blueprint, render_template, session

reports_bp = Blueprint("reports", __name__)

@reports_bp.get("/reports")
def reports():
    return render_template(
        "reports.html",
        layout="app",
        active_page="reports",
        profile=session.get("patient_profile", {}),
        results=session.get("match_results", [])
    )
