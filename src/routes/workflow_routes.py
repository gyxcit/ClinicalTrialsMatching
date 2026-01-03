# src/routes/workflow_routes.py
"""
Flask routes for workflow initialization and processing
"""
import asyncio
from flask import Blueprint, render_template, request, jsonify, session
from typing import Dict, Any

from src.services.illness_analyzer import IllnessAnalyzer
from src.services.trial_filter import TrialFilter
from src.services.question_generator import QuestionGenerator
from src.trials import fetch_trials_async
from src.logger import logger
from src.utils.session_manager import SessionManager


workflow_bp = Blueprint('workflow', __name__)


@workflow_bp.route('/')
def home():
    """Home page"""
    return render_template('home.html')


@workflow_bp.route('/start_workflow', methods=['POST'])
def start_workflow():
    """Initialize the workflow with user input"""
    data = request.json
    user_description = data.get('description', '')
    num_studies = data.get('num_studies', 10)
    
    session['user_description'] = user_description
    session['num_studies'] = num_studies
    session['workflow_started'] = True
    
    return jsonify({'success': True})


@workflow_bp.route('/process_workflow', methods=['GET'])
def process_workflow():
    """Process the complete workflow"""
    async def run_workflow():
        user_description = session.get('user_description', '')
        num_studies = session.get('num_studies', 10)
        
        # Initialize services
        illness_analyzer = IllnessAnalyzer()
        trial_filter = TrialFilter()
        question_generator = QuestionGenerator()
        
        # Step 1: Analyze illness
        logger.info("Step 1: Analyzing illness...")
        illness_info = await illness_analyzer.analyze(user_description)
        
        # Step 2: Fetch trials
        logger.info("Step 2: Fetching clinical trials...")
        trials = await fetch_trials_async(
            condition=illness_info.illness_name,
            max_studies=num_studies,
            return_status=True,
            json_output=False,
            timeout=10
        )
        
        if not trials:
            return {'error': 'No trials found'}
        
        # Step 3: Filter trials
        filtered_trials = await trial_filter.filter_by_keywords(illness_info, trials)
        
        if not filtered_trials:
            return {'error': 'No relevant trials found'}
        
        # Step 4: Extract eligibility
        trials_eligibility = trial_filter.extract_eligibility_criteria(filtered_trials)
        
        # Step 5: Generate questions
        trials_with_questions = await question_generator.generate_for_all_trials(trials_eligibility)
        
        # Save to file instead of session
        session_id = SessionManager.initialize_session()
        SessionManager.create_data_file(session_id, {
            'trials_data': trials_with_questions,
            'current_trial_index': 0,
            'results': [],
            'user_responses': {},
            'inclusion_scores': {}
        })
        
        # Only store minimal data in session
        session['total_trials'] = len(trials_with_questions)
        session.modified = True
        
        return {'success': True, 'total_trials': len(trials_with_questions)}

    result = asyncio.run(run_workflow())
    
    if 'error' in result:
        return jsonify(result), 400
    
    return jsonify(result)