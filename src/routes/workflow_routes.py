# src/routes/workflow_routes.py
"""
Flask routes for workflow initialization and processing
"""
import asyncio
from flask import Blueprint, request, jsonify, session, redirect, url_for
from typing import Dict, Any

from src.services.illness_analyzer import IllnessAnalyzer
from src.services.trial_filter import TrialFilter
from src.services.question_generator import QuestionGenerator
from src.trials import fetch_trials_async
from src.logger import logger
from src.utils.session_manager import SessionManager

workflow_bp = Blueprint("workflow", __name__)


def _run_coro(coro):
    """
    Run async coroutine safely from sync Flask routes.
    Fixes: 'asyncio.run() cannot be called from a running event loop'
    """
    try:
        loop = asyncio.get_running_loop()
        # If already running (rare in Flask, but happens in some setups),
        # run in a brand new loop.
        new_loop = asyncio.new_event_loop()
        try:
            return new_loop.run_until_complete(coro)
        finally:
            new_loop.close()
    except RuntimeError:
        # No running loop → normal case
        return asyncio.run(coro)


def _build_description_from_profile(profile: Dict[str, Any]) -> str:
    free = (profile.get("freeText") or "").strip()
    if free:
        return free

    parts = []
    for k, label in [
        ("diagnosis", "Diagnosis"),
        ("stage", "Stage"),
        ("age", "Age"),
        ("gender", "Gender"),
        ("ecogStatus", "ECOG"),
    ]:
        v = (profile.get(k) or "").strip()
        if v:
            parts.append(f"{label}: {v}")

    biomarkers = profile.get("biomarkers") or []
    if biomarkers:
        parts.append("Biomarkers: " + ", ".join(biomarkers))

    prior = profile.get("priorTreatments") or []
    if prior:
        parts.append("Prior treatments: " + ", ".join(prior))

    com = profile.get("comorbidities") or []
    if com:
        parts.append("Comorbidities: " + ", ".join(com))

    return " | ".join(parts) if parts else "Patient looking for clinical trial options."


async def _run_workflow_async(user_description: str, num_studies: int) -> Dict[str, Any]:
    illness_analyzer = IllnessAnalyzer()
    trial_filter = TrialFilter()
    question_generator = QuestionGenerator()

    logger.info("Step 1: Analyzing illness...")
    illness_info = await illness_analyzer.analyze(user_description)
    

    # ✅ Robust: accept IllnessInfo OR str
    illness_name = getattr(illness_info, "illness_name", None)
    if not illness_name and isinstance(illness_info, str):
        illness_name = illness_info.strip()

    illness_name = illness_name or "Unknown"

    logger.info(f"Step 2: Fetching clinical trials for condition='{illness_name}'...")
    trials = await fetch_trials_async(
        condition=illness_name,
        max_studies=num_studies,
        return_status=True,
        json_output=False,
        timeout=10,
    )

    if not trials:
        return {"error": "No trials found"}

    filtered_trials = await trial_filter.filter_by_keywords(illness_info, trials)
    if not filtered_trials:
        return {"error": "No relevant trials found"}

    trials_eligibility = trial_filter.extract_eligibility_criteria(filtered_trials)
    trials_with_questions = await question_generator.generate_for_all_trials(trials_eligibility)

    session_id = SessionManager.initialize_session()
    SessionManager.create_data_file(
        session_id,
        {
            "trials_data": trials_with_questions,
            "current_trial_index": 0,
            "results": [],
            "user_responses": {},
            "inclusion_scores": {},
        },
    )

    session["total_trials"] = len(trials_with_questions)
    session["workflow_started"] = True
    session.modified = True

    return {"success": True, "total_trials": len(trials_with_questions)}


@workflow_bp.route("/start_workflow", methods=["POST"])
def start_workflow():
    data = request.json or {}
    user_description = data.get("description", "")
    num_studies = int(data.get("num_studies", 10))

    session["user_description"] = user_description
    session["num_studies"] = num_studies
    session["workflow_started"] = True
    session.modified = True

    return jsonify({"success": True})


@workflow_bp.route("/process_workflow", methods=["GET"])
def process_workflow():
    user_description = session.get("user_description", "")
    num_studies = int(session.get("num_studies", 10))

    result = _run_coro(_run_workflow_async(user_description, num_studies))
    if "error" in result:
        return jsonify(result), 400
    return jsonify(result)


@workflow_bp.route("/run_from_profile", methods=["GET"])
def run_from_profile():
    profile = session.get("patient_profile", {}) or {}
    user_description = _build_description_from_profile(profile)
    num_studies = int(request.args.get("num_studies", 10))

    session["user_description"] = user_description
    session["num_studies"] = num_studies
    session.modified = True

    result = _run_coro(_run_workflow_async(user_description, num_studies))

    if "error" in result:
        session["workflow_error"] = result["error"]
        session.modified = True
        return redirect(url_for("patient.patient_profile"))

    return redirect(url_for("workflow.loading"))


@workflow_bp.get("/loading")
def loading():
    # page de transition (UI)
    return render_template(
        "workflow_loading.html",
        layout="app",
        active_page="matching"
    )