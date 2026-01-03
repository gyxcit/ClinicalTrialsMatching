# src/routes/questionnaire_routes.py
"""
Flask routes for questionnaire interface
"""
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from typing import Dict, Any

from src.utils.session_manager import SessionManager


questionnaire_bp = Blueprint('questionnaire', __name__)


@questionnaire_bp.route('/questionnaire')
def questionnaire():
    """Questionnaire page"""
    if not session.get('session_id'):
        return redirect(url_for('workflow.home'))
    
    return render_template('questionnaire.html', total_trials=session.get('total_trials', 0))


@questionnaire_bp.route('/get_current_trial', methods=['GET'])
def get_current_trial():
    """Get current trial and first question"""
    data = SessionManager.load_data()
    if not data:
        return jsonify({'error': 'Session expired'}), 400
    
    trials_data = data['trials_data']
    trial_index = data['current_trial_index']
    
    if trial_index >= len(trials_data):
        return jsonify({'completed': True, 'results': data['results']})
    
    trial = trials_data[trial_index]
    exclusion_questions = trial['questions']['exclusion']
    
    if exclusion_questions:
        first_q_id = list(exclusion_questions.keys())[0]
        return jsonify({
            'completed': False,
            'trial_info': {
                'nct_id': trial['nct_id'],
                'title': trial['title'],
                'trial_number': trial_index + 1,
                'total_trials': len(trials_data)
            },
            'current_question': {
                'question_id': first_q_id,
                'question': exclusion_questions[first_q_id]['question'],
                'type': 'exclusion'
            }
        })
    
    return _get_next_question_internal(data, trial['nct_id'])


@questionnaire_bp.route('/submit_answer', methods=['POST'])
def submit_answer():
    """Submit answer and get next question"""
    request_data = request.json
    question_id = request_data.get('question_id')
    answer = request_data.get('answer')
    nct_id = request_data.get('nct_id')
    question_type = request_data.get('question_type')
    
    data = SessionManager.load_data()
    if not data:
        return jsonify({'error': 'Session expired'}), 400
    
    # Save response
    if nct_id not in data['user_responses']:
        data['user_responses'][nct_id] = {}
    data['user_responses'][nct_id][question_id] = answer
    
    # Exclusion logic
    if question_type == 'exclusion' and answer:
        trial_index = data['current_trial_index']
        trial = data['trials_data'][trial_index]
        
        data['results'].append({
            'nct_id': nct_id,
            'title': trial['title'],
            'eligible': False,
            'reason': 'Excluded',
            'inclusion_score': 0,
            'total_inclusion_questions': len(trial['questions']['inclusion']),
            'inclusion_percentage': 0
        })
        data['current_trial_index'] = trial_index + 1
        SessionManager.save_data(data)
        
        return jsonify({
            'excluded': True,
            'message': 'You are not eligible for this trial.',
            'move_to_next': True
        })
    
    # Inclusion scoring
    if question_type == 'inclusion' and answer:
        if nct_id not in data['inclusion_scores']:
            data['inclusion_scores'][nct_id] = 0
        data['inclusion_scores'][nct_id] += 1
    
    SessionManager.save_data(data)
    return _get_next_question_internal(data, nct_id)


def _get_next_question_internal(data: Dict[str, Any], nct_id: str):
    """Get next question for trial (internal helper)"""
    trial_index = data['current_trial_index']
    trials_data = data['trials_data']
    trial = trials_data[trial_index]
    user_responses = data['user_responses'].get(nct_id, {})
    
    # Check exclusion questions
    for q_id, q_data in trial['questions']['exclusion'].items():
        if q_id not in user_responses:
            return jsonify({
                'excluded': False,
                'current_question': {
                    'question_id': q_id,
                    'question': q_data['question'],
                    'type': 'exclusion'
                },
                'trial_info': {
                    'nct_id': trial['nct_id'],
                    'title': trial['title'],
                    'trial_number': trial_index + 1,
                    'total_trials': len(trials_data)
                }
            })
    
    # Check inclusion questions
    for q_id, q_data in trial['questions']['inclusion'].items():
        if q_id not in user_responses:
            return jsonify({
                'excluded': False,
                'current_question': {
                    'question_id': q_id,
                    'question': q_data['question'],
                    'type': 'inclusion'
                },
                'trial_info': {
                    'nct_id': trial['nct_id'],
                    'title': trial['title'],
                    'trial_number': trial_index + 1,
                    'total_trials': len(trials_data)
                }
            })
    
    # Calculate eligibility
    inclusion_questions = trial['questions']['inclusion']
    total_inclusion = len(inclusion_questions)
    inclusion_score = data['inclusion_scores'].get(nct_id, 0)
    inclusion_percentage = (inclusion_score / total_inclusion * 100) if total_inclusion > 0 else 0
    eligible = inclusion_score == total_inclusion
    
    data['results'].append({
        'nct_id': nct_id,
        'title': trial['title'],
        'eligible': eligible,
        'reason': 'Eligible' if eligible else f'Met {inclusion_score}/{total_inclusion} criteria',
        'inclusion_score': inclusion_score,
        'total_inclusion_questions': total_inclusion,
        'inclusion_percentage': round(inclusion_percentage, 1)
    })
    data['current_trial_index'] = trial_index + 1
    SessionManager.save_data(data)
    
    if data['current_trial_index'] >= len(trials_data):
        return jsonify({
            'trial_completed': True,
            'all_completed': True,
            'results': data['results']
        })
    
    return jsonify({
        'trial_completed': True,
        'all_completed': False,
        'eligible': eligible,
        'inclusion_score': inclusion_score,
        'total_inclusion_questions': total_inclusion,
        'inclusion_percentage': round(inclusion_percentage, 1),
        'move_to_next': True
    })