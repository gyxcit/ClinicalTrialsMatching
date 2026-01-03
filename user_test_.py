"""
Web interface for clinical trial eligibility questionnaire
"""
import json
from flask import Flask, render_template, request, jsonify, session
import secrets

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

# Charger les données des trials
with open('trials_questions_structured.json', 'r', encoding='utf-8') as f:
    TRIALS_DATA = json.load(f)


@app.route('/')
def index():
    """Page d'accueil"""
    return render_template('index.html', total_trials=len(TRIALS_DATA))


@app.route('/start_questionnaire', methods=['POST'])
def start_questionnaire():
    """Initialiser le questionnaire"""
    session['current_trial_index'] = 0
    session['results'] = []
    session['user_responses'] = {}
    session['inclusion_scores'] = {}  # Nouveau: stocker les scores d'inclusion
    
    return jsonify({
        'success': True,
        'message': 'Questionnaire started'
    })


@app.route('/get_current_trial', methods=['GET'])
def get_current_trial():
    """Obtenir le trial courant et la première question"""
    trial_index = session.get('current_trial_index', 0)
    
    if trial_index >= len(TRIALS_DATA):
        return jsonify({
            'completed': True,
            'results': session.get('results', [])
        })
    
    trial = TRIALS_DATA[trial_index]
    
    # Commencer par les questions d'exclusion
    exclusion_questions = trial['questions']['exclusion']
    
    if exclusion_questions:
        first_question_id = list(exclusion_questions.keys())[0]
        first_question = exclusion_questions[first_question_id]
        
        return jsonify({
            'completed': False,
            'trial_info': {
                'nct_id': trial['nct_id'],
                'title': trial['title'],
                'trial_number': trial_index + 1,
                'total_trials': len(TRIALS_DATA)
            },
            'current_question': {
                'question_id': first_question_id,
                'question': first_question['question'],
                'type': 'exclusion'
            }
        })
    else:
        # Pas de questions d'exclusion, passer aux questions d'inclusion
        return get_next_question(trial['nct_id'])


@app.route('/submit_answer', methods=['POST'])
def submit_answer():
    """Soumettre une réponse et obtenir la question suivante"""
    data = request.json
    question_id = data.get('question_id')
    answer = data.get('answer')  # True or False
    nct_id = data.get('nct_id')
    question_type = data.get('question_type')
    
    # Sauvegarder la réponse
    if 'user_responses' not in session:
        session['user_responses'] = {}
    
    if nct_id not in session['user_responses']:
        session['user_responses'][nct_id] = {}
    
    session['user_responses'][nct_id][question_id] = answer
    session.modified = True
    
    # Si c'est une question d'exclusion et la réponse est Yes (True)
    if question_type == 'exclusion' and answer:
        # Patient est exclu de ce trial
        trial_index = session.get('current_trial_index', 0)
        trial = TRIALS_DATA[trial_index]
        
        session['results'].append({
            'nct_id': nct_id,
            'title': trial['title'],
            'eligible': False,
            'reason': 'Excluded',
            'failed_question': question_id,
            'inclusion_score': 0,
            'inclusion_percentage': 0
        })
        session.modified = True
        
        # Passer au trial suivant
        session['current_trial_index'] = trial_index + 1
        session.modified = True
        
        return jsonify({
            'excluded': True,
            'message': 'You are not eligible for this trial. Moving to next trial.',
            'move_to_next': True
        })
    
    # Si c'est une question d'inclusion et la réponse est Yes, ajouter un point
    if question_type == 'inclusion' and answer:
        if 'inclusion_scores' not in session:
            session['inclusion_scores'] = {}
        
        if nct_id not in session['inclusion_scores']:
            session['inclusion_scores'][nct_id] = 0
        
        session['inclusion_scores'][nct_id] += 1
        session.modified = True
    
    # Obtenir la question suivante
    return get_next_question(nct_id)


def get_next_question(nct_id):
    """Obtenir la prochaine question pour ce trial"""
    trial_index = session.get('current_trial_index', 0)
    trial = TRIALS_DATA[trial_index]
    
    user_responses = session.get('user_responses', {}).get(nct_id, {})
    
    # Vérifier les questions d'exclusion
    exclusion_questions = trial['questions']['exclusion']
    for q_id, q_data in exclusion_questions.items():
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
                    'total_trials': len(TRIALS_DATA)
                }
            })
    
    # Toutes les questions d'exclusion sont répondues, passer aux questions d'inclusion
    inclusion_questions = trial['questions']['inclusion']
    for q_id, q_data in inclusion_questions.items():
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
                    'total_trials': len(TRIALS_DATA)
                }
            })
    
    # Toutes les questions sont répondues pour ce trial
    # Calculer le score d'inclusion
    total_inclusion_questions = len(inclusion_questions)
    inclusion_score = session.get('inclusion_scores', {}).get(nct_id, 0)
    inclusion_percentage = (inclusion_score / total_inclusion_questions * 100) if total_inclusion_questions > 0 else 0
    
    # Vérifier l'éligibilité (toutes les questions d'inclusion doivent être Yes)
    eligible = inclusion_score == total_inclusion_questions
    
    session['results'].append({
        'nct_id': nct_id,
        'title': trial['title'],
        'eligible': eligible,
        'reason': 'Eligible' if eligible else f'Met {inclusion_score}/{total_inclusion_questions} inclusion criteria',
        'inclusion_score': inclusion_score,
        'total_inclusion_questions': total_inclusion_questions,
        'inclusion_percentage': round(inclusion_percentage, 1)
    })
    session.modified = True
    
    # Passer au trial suivant
    session['current_trial_index'] = trial_index + 1
    session.modified = True
    
    # Vérifier s'il y a d'autres trials
    if session['current_trial_index'] >= len(TRIALS_DATA):
        return jsonify({
            'trial_completed': True,
            'all_completed': True,
            'results': session.get('results', [])
        })
    
    return jsonify({
        'trial_completed': True,
        'all_completed': False,
        'eligible': eligible,
        'inclusion_score': inclusion_score,
        'total_inclusion_questions': total_inclusion_questions,
        'inclusion_percentage': round(inclusion_percentage, 1),
        'message': f'Trial assessment complete. Eligible: {eligible} ({inclusion_percentage:.1f}% match)',
        'move_to_next': True
    })


@app.route('/get_results', methods=['GET'])
def get_results():
    """Obtenir les résultats finaux"""
    results = session.get('results', [])
    
    eligible_trials = [r for r in results if r['eligible']]
    
    # Trier les résultats par pourcentage d'inclusion (du plus haut au plus bas)
    sorted_results = sorted(results, key=lambda x: x.get('inclusion_percentage', 0), reverse=True)
    
    return jsonify({
        'total_trials': len(results),
        'eligible_trials': len(eligible_trials),
        'results': sorted_results
    })


if __name__ == '__main__':
    app.run(debug=True, port=5000)