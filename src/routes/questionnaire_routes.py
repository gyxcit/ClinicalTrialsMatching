# src/routes/questionnaire_routes.py
"""
Flask routes for questionnaire interface
"""
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from typing import Dict, Any
import asyncio

from src.utils.session_manager import SessionManager
from src.logger import logger



questionnaire_bp = Blueprint("questionnaire", __name__)


@questionnaire_bp.route("/questionnaire")
def questionnaire():
    """
    Questionnaire page

    IMPORTANT:
    Le workflow stocke la data dans un fichier (session['data_file']).
    Donc pour commencer le questionnaire, on doit avoir data_file (ou pouvoir le reconstruire via session_id).
    """
    # ✅ condition réelle: data_file (ou fallback via SessionManager.load_data())
    data = SessionManager.load_data()

    if not data:
        # pas de session workflow => on renvoie vers la page profile
        return redirect(url_for("patient.patient_profile"))

    return render_template(
        "questionnaire.html",
        layout="app",
        active_page="matching",
        total_trials=session.get("total_trials", 0),
    )


@questionnaire_bp.route("/get_current_trial", methods=["GET"])
def get_current_trial():
    """Get current trial and first question"""
    data = SessionManager.load_data()
    if not data:
        return jsonify({"error": "Session expired"}), 400

    trials_data = data["trials_data"]
    trial_index = data["current_trial_index"]

    if trial_index >= len(trials_data):
        return jsonify({"completed": True, "results": data["results"]})

    trial = trials_data[trial_index]
    exclusion_questions = trial["questions"]["exclusion"]

    if exclusion_questions:
        first_q_id = list(exclusion_questions.keys())[0]
        return jsonify(
            {
                "completed": False,
                "trial_info": {
                    "nct_id": trial["nct_id"],
                    "title": trial["title"],
                    "trial_number": trial_index + 1,
                    "total_trials": len(trials_data),
                },
                "current_question": {
                    "question_id": first_q_id,
                    "question": exclusion_questions[first_q_id]["question"],
                    "type": "exclusion",
                },
            }
        )

    return _get_next_question_internal(data, trial["nct_id"])


@questionnaire_bp.route("/reformulate_question", methods=["POST"])
def reformulate_question():
    """Reformulate a question to be simpler"""
    from src.services.question_simplifier import QuestionSimplifier
    
    request_data = request.json
    question = request_data.get("question")
    context = request_data.get("context", {})
    
    if not question:
        return jsonify({"error": "Question is required"}), 400
    
    async def run_simplification():
        simplifier = QuestionSimplifier()
        return await simplifier.simplify(question, context)
    
    try:
        simplified = asyncio.run(run_simplification())
        return jsonify({
            "original_question": question,
            "simplified_question": simplified
        })
    except Exception as e:
        logger.error(f"Error simplifying question: {e}")
        return jsonify({"error": f"Failed to simplify: {str(e)}"}), 500


@questionnaire_bp.route("/submit_answer", methods=["POST"])
def submit_answer():
    """Submit answer and get next question"""
    request_data = request.json or {}
    question_id = request_data.get("question_id")
    answer = request_data.get("answer")  # ✅ Peut être true, false, ou "unsure"
    nct_id = request_data.get("nct_id")
    question_type = request_data.get("question_type")

    data = SessionManager.load_data()
    if not data:
        return jsonify({"error": "Session expired"}), 400

    # ✅ Gérer "unsure" comme une réponse partielle
    if answer == "unsure":
        # Pour "I don't know", on enregistre comme False mais on ajoute un flag
        actual_answer = False
        is_unsure = True
    else:
        actual_answer = answer
        is_unsure = False

    # Save response
    if nct_id not in data["user_responses"]:
        data["user_responses"][nct_id] = {}
    data["user_responses"][nct_id][question_id] = {
        "answer": actual_answer,
        "is_unsure": is_unsure
    }

    # Exclusion logic
    if question_type == "exclusion" and actual_answer:
        trial_index = data["current_trial_index"]
        trial = data["trials_data"][trial_index]

        data["results"].append(
            {
                "nct_id": nct_id,
                "title": trial["title"],
                "eligible": False,
                "reason": "Excluded",
                "inclusion_score": 0,
                "total_inclusion_questions": len(trial["questions"]["inclusion"]),
                "inclusion_percentage": 0,
            }
        )
        data["current_trial_index"] = trial_index + 1
        SessionManager.save_data(data)

        return jsonify(
            {
                "excluded": True,
                "message": "You are not eligible for this trial.",
                "move_to_next": True,
            }
        )

    # ✅ Inclusion scoring avec pénalité pour "unsure"
    if question_type == "inclusion":
        if nct_id not in data["inclusion_scores"]:
            data["inclusion_scores"][nct_id] = 0.0
        
        if actual_answer:
            # Réponse "Yes" = 1 point
            data["inclusion_scores"][nct_id] += 1.0
        elif is_unsure:
            # Réponse "I don't know" = 0.5 point
            data["inclusion_scores"][nct_id] += 0.5

    SessionManager.save_data(data)
    return _get_next_question_internal(data, nct_id)


def _get_next_question_internal(data: Dict[str, Any], nct_id: str):
    """Get next question for trial (internal helper)"""
    trial_index = data["current_trial_index"]
    trials_data = data["trials_data"]
    trial = trials_data[trial_index]
    user_responses = data["user_responses"].get(nct_id, {})

    # Check exclusion questions
    for q_id, q_data in trial["questions"]["exclusion"].items():
        if q_id not in user_responses:
            return jsonify(
                {
                    "excluded": False,
                    "current_question": {
                        "question_id": q_id,
                        "question": q_data["question"],
                        "type": "exclusion",
                    },
                    "trial_info": {
                        "nct_id": trial["nct_id"],
                        "title": trial["title"],
                        "trial_number": trial_index + 1,
                        "total_trials": len(trials_data),
                    },
                }
            )

    # Check inclusion questions
    for q_id, q_data in trial["questions"]["inclusion"].items():
        if q_id not in user_responses:
            return jsonify(
                {
                    "excluded": False,
                    "current_question": {
                        "question_id": q_id,
                        "question": q_data["question"],
                        "type": "inclusion",
                    },
                    "trial_info": {
                        "nct_id": trial["nct_id"],
                        "title": trial["title"],
                        "trial_number": trial_index + 1,
                        "total_trials": len(trials_data),
                    },
                }
            )

    # ✅ Calculate eligibility with decimal support for "unsure" answers
    inclusion_questions = trial["questions"]["inclusion"]
    total_inclusion = len(inclusion_questions)
    inclusion_score = data["inclusion_scores"].get(nct_id, 0.0)  # ✅ Float instead of int
    inclusion_percentage = (inclusion_score / total_inclusion * 100) if total_inclusion > 0 else 0
    eligible = inclusion_score == total_inclusion  # ✅ Full score required for eligible

    data["results"].append(
        {
            "nct_id": nct_id,
            "title": trial["title"],
            "eligible": eligible,
            "reason": "Eligible" if eligible else f"Met {inclusion_score:.1f}/{total_inclusion} criteria",  # ✅ Show decimal
            "inclusion_score": inclusion_score,
            "total_inclusion_questions": total_inclusion,
            "inclusion_percentage": round(inclusion_percentage, 1),
        }
    )
    data["current_trial_index"] = trial_index + 1
    SessionManager.save_data(data)

    if data["current_trial_index"] >= len(trials_data):
        return jsonify(
            {
                "trial_completed": True,
                "all_completed": True,
                "results": data["results"],
            }
        )

    return jsonify(
        {
            "trial_completed": True,
            "all_completed": False,
            "eligible": eligible,
            "inclusion_score": inclusion_score,
            "total_inclusion_questions": total_inclusion,
            "inclusion_percentage": round(inclusion_percentage, 1),
            "move_to_next": True,
        }
    )
