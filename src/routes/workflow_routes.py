# src/routes/workflow_routes.py
"""
Flask routes for workflow initialization and processing
"""
import asyncio
from typing import Dict, Any

from flask import Blueprint, request, jsonify, session, redirect, url_for, render_template

from src.services.illness_analyzer import IllnessAnalyzer
from src.services.trial_filter import TrialFilter
from src.services.question_generator import QuestionGenerator
from src.services.language_service import LanguageService
from src.trials import fetch_trials_async
from src.logger import logger
from src.utils.session_manager import SessionManager

workflow_bp = Blueprint("workflow", __name__)


def _run_coro(coro):
    """
    Run async coroutine safely from sync Flask routes.
    """
    try:
        asyncio.get_running_loop()
        new_loop = asyncio.new_event_loop()
        try:
            return new_loop.run_until_complete(coro)
        finally:
            new_loop.close()
    except RuntimeError:
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
        v = (profile.get(k) or "")
        v = str(v).strip()
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
    """
    IMPORTANT:
    - Do NOT touch Flask session here (avoid request-context issues).
    - Return everything needed, then session is updated in the sync route.
    """
    illness_analyzer = IllnessAnalyzer()
    trial_filter = TrialFilter()
    question_generator = QuestionGenerator()
    language_service = LanguageService()

    # Step 0: detect language
    logger.info("Step 0: Detecting user's language...")
    language_info = await language_service.detect_language(user_description)
    user_language = language_info.get("code", "en")
    user_language_name = language_info.get("name", "English")
    logger.info(f"📝 User language: {user_language_name} ({user_language})")

    # Step 1: illness analysis
    logger.info("Step 1: Analyzing illness...")
    illness_info = await illness_analyzer.analyze(user_description)

    illness_name = getattr(illness_info, "illness_name", None)
    if not illness_name and isinstance(illness_info, str):
        illness_name = illness_info.strip()
    illness_name = illness_name or "Unknown"

    # Step 2: fetch trials
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

    # Step 3: generate questions in English
    logger.info("Step 3: Generating questions in English (backend)...")
    trials_with_questions = await question_generator.generate_for_all_trials(trials_eligibility)

    # Step 4: translate questions
    if user_language != "en":
        logger.info(f"Step 4: Translating questions to {user_language_name}...")
        for trial in trials_with_questions:
            trial["questions"]["inclusion"] = await language_service.translate_questions_batch(
                trial["questions"]["inclusion"], user_language
            )
            trial["questions"]["exclusion"] = await language_service.translate_questions_batch(
                trial["questions"]["exclusion"], user_language
            )

    # persist in file session store
    session_id = SessionManager.initialize_session()
    SessionManager.create_data_file(
        session_id,
        {
            "trials_data": trials_with_questions,
            "current_trial_index": 0,
            "results": [],
            "user_responses": {},
            "inclusion_scores": {},
            "user_language": user_language,
        },
    )

    return {
        "success": True,
        "total_trials": len(trials_with_questions),
        "language_code": user_language,
        "language_name": user_language_name,
    }


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
    """
    API endpoint called by /workflow/loading (JS fetch)
    MUST always return JSON (even on crash), otherwise front may show Failed to fetch.
    """
    user_description = session.get("user_description", "")
    num_studies = int(session.get("num_studies", 10))

    try:
        result = _run_coro(_run_workflow_async(user_description, num_studies))

        if not isinstance(result, dict):
            return jsonify({"error": "Workflow returned invalid response"}), 500

        if "error" in result:
            return jsonify(result), 400

        # ✅ NOW we can safely write to Flask session (sync context)
        session["total_trials"] = result.get("total_trials", 0)
        session["workflow_started"] = True
        session["user_language"] = result.get("language_code", "en")
        session["user_language_name"] = result.get("language_name", "English")
        session.modified = True

        return jsonify(result)

    except Exception as e:
        logger.exception("process_workflow crashed")
        return jsonify({"error": f"Workflow crashed: {str(e)}"}), 500


@workflow_bp.route("/run_from_profile", methods=["GET"])
def run_from_profile():
    """
    UI entry: Patient profile -> store inputs -> redirect to loading page
    """
    profile = session.get("patient_profile", {}) or {}
    user_description = _build_description_from_profile(profile)
    num_studies = int(request.args.get("num_studies", 10))

    session["user_description"] = user_description
    session["num_studies"] = num_studies
    session.modified = True

    return redirect(url_for("workflow.loading"))


@workflow_bp.get("/loading")
def loading():
    return render_template(
        "workflow_loading.html",
        layout="app",
        active_page="matching",
    )
