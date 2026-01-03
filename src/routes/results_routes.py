# src/routes/results_routes.py
"""
Flask routes for results display and explanations
"""
import asyncio
from flask import Blueprint, request, jsonify
from typing import Dict, Any

from src.services.explanation_service import ExplanationService
from src.utils.session_manager import SessionManager
from src.logger import logger


results_bp = Blueprint('results', __name__)


@results_bp.route('/get_results', methods=['GET'])
def get_results():
    """Get final results"""
    data = SessionManager.load_data()
    if not data:
        return jsonify({'error': 'Session expired'}), 400
    
    results = data.get('results', [])
    sorted_results = sorted(results, key=lambda x: x.get('inclusion_percentage', 0), reverse=True)
    
    return jsonify({
        'total_trials': len(results),
        'eligible_trials': len([r for r in results if r['eligible']]),
        'results': sorted_results
    })


@results_bp.route('/explain_result', methods=['POST'])
def explain_result():
    """Generate AI explanation for a specific trial result"""
    request_data = request.json
    nct_id = request_data.get('nct_id')
    
    if not nct_id:
        return jsonify({'error': 'Trial ID is required'}), 400
    
    data = SessionManager.load_data()
    if not data:
        return jsonify({'error': 'Session expired'}), 400
    
    # Find the trial
    trial_data = None
    for trial in data['trials_data']:
        if trial['nct_id'] == nct_id:
            trial_data = trial
            break
    
    if not trial_data:
        return jsonify({'error': 'Trial not found'}), 404
    
    # Get user responses for this trial
    user_responses = data['user_responses'].get(nct_id, {})
    
    if not user_responses:
        return jsonify({'error': 'No responses found for this trial'}), 404
    
    async def run_explanation():
        explanation_service = ExplanationService()
        return await explanation_service.generate_with_validation(nct_id, trial_data, user_responses)
    
    try:
        result = asyncio.run(run_explanation())
        
        response_data = {
            'nct_id': nct_id,
            'explanation': result['explanation'],
            'quality': {
                'comprehension_score': result['comprehension_score'],
                'attempts': result['attempts'],
                'is_acceptable': result['evaluation']['is_acceptable']
            }
        }
        
        # Add warning if quality is poor
        if 'warning' in result:
            response_data['warning'] = result['warning']
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Error generating explanation: {e}")
        return jsonify({'error': f'Failed to generate explanation: {str(e)}'}), 500