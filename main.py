"""
Main Flask application for Clinical Trial Matching
Combines illness extraction, trial filtering, question generation, and eligibility assessment
"""
import asyncio
import json
import os
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import secrets
from typing import List, Dict, Any
import tempfile
import pickle

# Import workflow functions
from src.agent_manager import AgentManager, AgentModel, ResponseFormat
from src.response_models import IllnessInfo, EligibilityQuestions, ExplanationEvaluation
from src.config import MISTRAL_AGENT_ID
from src.logger import logger
from src.trials import fetch_trials_async

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)


# ==================== WORKFLOW FUNCTIONS ====================

async def get_illness_type_structured(user_illness: str):
    """Get illness type with structured response."""
    logger.info("🏥 Analyzing patient description...")
    
    async with AgentManager(max_retries=3, retry_delay=5.0) as manager:
        agent = manager.create_agent(
            agent_id=MISTRAL_AGENT_ID,
            name="IllnessTypeAgent",
            model=AgentModel.SMALL.value,
            response_format=ResponseFormat.JSON,
            response_model=IllnessInfo
        )
        
        prompt = f"""
        The response MUST be in English.
        Analyze the following patient description and return a JSON object compatible with the IllnessInfo model.
        Patient input: {user_illness}
        
        Rules:
        - illness_name: general illness name only (no types, subtypes, stages, variants, or anatomical locations)
        - type: specific type or subtype if mentioned, else null
        - subtype: specific variant if mentioned, else null
        - stage: disease stage if explicitly mentioned, else null
        - anatomical_location: primary affected body part or system if mentioned, else null
        - organ_touched: specific organ or tissue affected if mentioned, else null
        - category: medical category (e.g., chronic, acute, infectious, genetic, autoimmune)
        - severity: mild/moderate/severe if mentioned, else null
        - affected_systems: list affected body systems
        - keywords: include any types, stages, variants, organs, or other relevant terms
        - Use null for unknown fields
        
        Normalization rules:
        - All medical terms MUST be in canonical singular form
        - "diabetes" → "diabetes", "kidneys" → "kidney", "eyes" → "eye"
        """
        
        response = await manager.chat_with_retry_async(
            agent_name="IllnessTypeAgent",
            message=prompt,
            response_model=IllnessInfo
        )
        
        return response


def trial_contains_keywords(study: Dict[str, Any], keywords: List[str]) -> tuple:
    """Check if trial contains keywords and calculate score"""
    protocol_section = study.get("protocolSection", {})
    texts_to_search = []
    
    # Extract all relevant texts
    identification = protocol_section.get("identificationModule", {})
    title = identification.get("officialTitle") or identification.get("briefTitle") or ""
    texts_to_search.append(title)
    
    description_module = protocol_section.get("descriptionModule", {})
    texts_to_search.extend([
        description_module.get("briefSummary") or "",
        description_module.get("detailedDescription") or ""
    ])
    
    combined_text = " ".join(texts_to_search).lower()
    
    total_occurrences = 0
    keywords_found = []
    for keyword in keywords:
        keyword_lower = keyword.lower()
        count = combined_text.count(keyword_lower)
        if count > 0:
            total_occurrences += count
            keywords_found.append(keyword)
    
    return len(keywords_found), total_occurrences, keywords_found


async def filter_trials_by_keywords(illness_info: IllnessInfo, trials: List[Dict[str, Any]]):
    """Filter trials based on illness keywords"""
    logger.info("🔍 Filtering trials by relevance...")
    
    list_of_words = []
    if illness_info.keywords:
        list_of_words.extend(illness_info.keywords)
    if illness_info.type:
        list_of_words.append(illness_info.type)
    if illness_info.organ_touched:
        list_of_words.extend(illness_info.organ_touched)
    if illness_info.anatomical_location:
        list_of_words.extend(illness_info.anatomical_location)
    if illness_info.affected_systems:
        list_of_words.extend(illness_info.affected_systems)
    
    list_of_words = list(set([word.lower() for word in list_of_words if word]))
    
    if not list_of_words:
        return trials
    
    # Identify universal keywords
    keyword_presence = {keyword: 0 for keyword in list_of_words}
    for study in trials:
        _, _, keywords_found = trial_contains_keywords(study, list_of_words)
        for keyword in keywords_found:
            keyword_presence[keyword] += 1
    
    universal_keywords = [kw for kw, count in keyword_presence.items() if count == len(trials)]
    filtered_keywords = [kw for kw in list_of_words if kw not in universal_keywords]
    
    if not filtered_keywords:
        return trials
    
    # Filter studies
    filtered_studies = []
    for study in trials:
        num_keywords, total_occurrences, keywords_found = trial_contains_keywords(study, filtered_keywords)
        if num_keywords > 0:
            filtered_studies.append({
                "study": study,
                "num_keywords": num_keywords,
                "total_occurrences": total_occurrences,
                "keywords_found": keywords_found
            })
    
    filtered_studies.sort(key=lambda x: (x["num_keywords"], x["total_occurrences"]), reverse=True)
    return filtered_studies


def extract_eligibility_criteria(filtered_trials: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Extract eligibility criteria from filtered trials"""
    logger.info("📋 Extracting eligibility criteria...")
    
    trials_eligibility = []
    for item in filtered_trials:
        study = item["study"]
        protocol_section = study.get('protocolSection', {})
        
        identification_module = protocol_section.get('identificationModule', {})
        nct_id = identification_module.get('nctId', 'N/A')
        title = identification_module.get('officialTitle') or identification_module.get('briefTitle', 'N/A')
        
        eligibility_module = protocol_section.get('eligibilityModule', {})
        
        trials_eligibility.append({
            'nct_id': nct_id,
            'title': title,
            'relevance_score': {
                'num_keywords': item['num_keywords'],
                'total_occurrences': item['total_occurrences'],
                'keywords_found': item['keywords_found']
            },
            'eligibility': {
                'criteria': eligibility_module.get('eligibilityCriteria', 'N/A'),
                'sex': eligibility_module.get('sex', 'N/A'),
                'minimum_age': eligibility_module.get('minimumAge', 'N/A'),
                'maximum_age': eligibility_module.get('maximumAge', 'N/A'),
                'healthy_volunteers': eligibility_module.get('healthyVolunteers', 'N/A')
            }
        })
    
    return trials_eligibility


async def generate_questions_for_trial(nct_id: str, title: str, criteria: str) -> EligibilityQuestions:
    """Generate eligibility questions for a trial"""
    async with AgentManager(max_retries=3, retry_delay=5.0) as manager:
        agent = manager.create_agent(
            agent_id=MISTRAL_AGENT_ID,
            name="QuestionGeneratorAgent",
            model=AgentModel.SMALL.value,
            response_format=ResponseFormat.JSON,
            response_model=EligibilityQuestions
        )
        
        prompt = f"""
        You are a medical research assistant. Generate clear, yes/no questions from clinical trial eligibility criteria for patients.

        Trial ID: {nct_id}
        Trial Title: {title}

        Eligibility Criteria:
        {criteria}

        Instructions:
        1. Read the eligibility criteria carefully.
        2. Identify INCLUSION criteria (what qualifies someone) and EXCLUSION criteria (what disqualifies someone).
        3. Generate simple, plain language yes/no questions for each criterion in a way that exclusion should be answered by no and inclusion by yes.
        4. Questions must be understandable by patients with no medical background.
        5. Avoid medical jargon. If a term is complex, rewrite it in simple words.
        6. Each question should address ONE specific criterion.
        7. Use short sentences (<15 words) and clear wording.
        8. Start questions with "Do you have...", "Have you ever...", or "Are you...".
        
        Important:
        - Do NOT include explanations, just the questions.
        - If a criterion is vague or ambiguous, skip it.
        - Ensure questions are relevant to the patient's perspective.
        - Keep the specific name if a condition is mentioned (e.g., "diabetes melitus", "Malignant hypertension ").
        - Limit to a maximum of 10 questions per category (inclusion/exclusion).

        Return a JSON object:
        
        {{"nct_id": "{nct_id}",
        "inclusion_questions": ["list of simplified yes/no questions for inclusion"],
        "exclusion_questions": ["list of simplified yes/no questions for exclusion"]}}

        Examples:
        - Inclusion: "Type 2 diabetes diagnosed within last 5 years"  
            Question: "Have you been diagnosed with type 2 diabetes in the last 5 years?"

        - Exclusion: "History of cancer"  
            Question: "Have you ever been diagnosed with cancer?"}}
        """
        
        response = await manager.chat_with_retry_async(
            agent_name="QuestionGeneratorAgent",
            message=prompt,
            response_model=EligibilityQuestions
        )
        
        return response


async def generate_all_questions(trials_eligibility: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Generate questions for all trials"""
    logger.info("📝 Generating eligibility questions...")
    
    trials_with_questions = []
    for trial in trials_eligibility:
        criteria = trial['eligibility']['criteria']
        if criteria == 'N/A' or not criteria.strip():
            continue
        
        try:
            questions = await generate_questions_for_trial(
                trial['nct_id'],
                trial['title'],
                criteria
            )
            
            # Structure questions with IDs
            inclusion_questions = {}
            for idx, question in enumerate(questions.inclusion_questions, start=1):
                q_id = f"{trial['nct_id']}_INC_{idx:03d}"
                inclusion_questions[q_id] = {"question": question, "response": None}
            
            exclusion_questions = {}
            for idx, question in enumerate(questions.exclusion_questions, start=1):
                q_id = f"{trial['nct_id']}_EXC_{idx:03d}"
                exclusion_questions[q_id] = {"question": question, "response": None}
            
            trials_with_questions.append({
                **trial,
                'questions': {
                    'inclusion': inclusion_questions,
                    'exclusion': exclusion_questions
                }
            })
            
            await asyncio.sleep(1)  # Rate limiting
            
        except Exception as e:
            logger.error(f"Error processing {trial['nct_id']}: {e}")
            continue
    
    return trials_with_questions


# ==================== FLASK ROUTES ====================

@app.route('/')
def home():
    """Home page"""
    return render_template('home.html')


@app.route('/start_workflow', methods=['POST'])
def start_workflow():
    """Initialize the workflow with user input"""
    data = request.json
    user_description = data.get('description', '')
    num_studies = data.get('num_studies', 10)
    
    session['user_description'] = user_description
    session['num_studies'] = num_studies
    session['workflow_started'] = True
    
    return jsonify({'success': True})


@app.route('/process_workflow', methods=['GET'])
def process_workflow():
    """Process the complete workflow"""
    async def run_workflow():
        user_description = session.get('user_description', '')
        num_studies = session.get('num_studies', 10)
        
        # Step 1: Analyze illness
        logger.info("Step 1: Analyzing illness...")
        illness_info = await get_illness_type_structured(user_description)
        
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
        filtered_trials = await filter_trials_by_keywords(illness_info, trials)
        
        if not filtered_trials:
            return {'error': 'No relevant trials found'}
        
        # Step 4: Extract eligibility
        trials_eligibility = extract_eligibility_criteria(filtered_trials)
        
        # Step 5: Generate questions
        trials_with_questions = await generate_all_questions(trials_eligibility)
        
        # ✅ FIX: Save to file instead of session
        temp_dir = tempfile.gettempdir()
        session_id = session.get('session_id') or secrets.token_hex(16)
        session['session_id'] = session_id
        
        data_file = os.path.join(temp_dir, f"trials_{session_id}.json")
        with open(data_file, 'w', encoding='utf-8') as f:
            json.dump({
                'trials_data': trials_with_questions,
                'current_trial_index': 0,
                'results': [],
                'user_responses': {},
                'inclusion_scores': {}
            }, f)
        
        # Only store minimal data in session
        session['data_file'] = data_file
        session['total_trials'] = len(trials_with_questions)
        session.modified = True
        
        return {'success': True, 'total_trials': len(trials_with_questions)}

    result = asyncio.run(run_workflow())
    
    if 'error' in result:
        return jsonify(result), 400
    
    return jsonify(result)


@app.route('/questionnaire')
def questionnaire():
    """Questionnaire page"""
    if not session.get('session_id'):
        return redirect(url_for('home'))
    
    return render_template('questionnaire.html', total_trials=session.get('total_trials', 0))


def load_session_data():
    """Helper function to load trial data from file"""
    data_file = session.get('data_file')
    if not data_file or not os.path.exists(data_file):
        return None
    
    with open(data_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_session_data(data):
    """Helper function to save trial data to file"""
    data_file = session.get('data_file')
    if data_file:
        with open(data_file, 'w', encoding='utf-8') as f:
            json.dump(data, f)


@app.route('/get_current_trial', methods=['GET'])
def get_current_trial():
    """Get current trial and first question"""
    data = load_session_data()
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
    
    return get_next_question_internal(data, trial['nct_id'])


@app.route('/submit_answer', methods=['POST'])
def submit_answer():
    """Submit answer and get next question"""
    request_data = request.json
    question_id = request_data.get('question_id')
    answer = request_data.get('answer')
    nct_id = request_data.get('nct_id')
    question_type = request_data.get('question_type')
    
    data = load_session_data()
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
        save_session_data(data)
        
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
    
    save_session_data(data)
    return get_next_question_internal(data, nct_id)


def get_next_question_internal(data, nct_id):
    """Get next question for trial"""
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
    save_session_data(data)
    
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


@app.route('/get_results', methods=['GET'])
def get_results():
    """Get final results"""
    data = load_session_data()
    if not data:
        return jsonify({'error': 'Session expired'}), 400
    
    results = data.get('results', [])
    sorted_results = sorted(results, key=lambda x: x.get('inclusion_percentage', 0), reverse=True)
    
    return jsonify({
        'total_trials': len(results),
        'eligible_trials': len([r for r in results if r['eligible']]),
        'results': sorted_results
    })


async def generate_explanation(nct_id: str, trial_data: Dict[str, Any], user_responses: Dict[str, bool]) -> str:
    """Generate AI explanation for trial results"""
    async with AgentManager(max_retries=3, retry_delay=5.0) as manager:
        agent = manager.create_agent(
            agent_id=MISTRAL_AGENT_ID,
            name="ExplanationAgent",
            model=AgentModel.SMALL.value,
            description="Medical results explanation specialist"
        )
        
        # Prepare questions and answers summary
        inclusion_qa = []
        exclusion_qa = []
        
        for q_id, q_data in trial_data['questions']['inclusion'].items():
            answer = user_responses.get(q_id, None)
            if answer is not None:
                inclusion_qa.append(f"- {q_data['question']}: {'Yes' if answer else 'No'}")
        
        for q_id, q_data in trial_data['questions']['exclusion'].items():
            answer = user_responses.get(q_id, None)
            if answer is not None:
                exclusion_qa.append(f"- {q_data['question']}: {'Yes' if answer else 'No'}")
        
        inclusion_text = "\n".join(inclusion_qa) if inclusion_qa else "No inclusion questions answered"
        exclusion_text = "\n".join(exclusion_qa) if exclusion_qa else "No exclusion questions answered"
        
        prompt = f"""
        You are a medical assistant explaining clinical trial eligibility results to a patient.
        
        **Trial Information:**
        - Trial ID: {trial_data['nct_id']}
        - Title: {trial_data['title']}
        
        **Patient's Responses to Exclusion Criteria:**
        {exclusion_text}
        
        **Patient's Responses to Inclusion Criteria:**
        {inclusion_text}
        
        **Task:**
        Provide a clear, empathetic explanation in 3-4 paragraphs covering:
        
        1. **Eligibility Summary**: Start by clearly stating if the patient is eligible, partially eligible, or not eligible.
        
        2. **Key Factors**: Explain which specific answers led to this result. Be specific about which criteria were met or not met.
        
        3. **What This Means**: Help the patient understand what these results mean for their participation in this trial.
        
        4. **Next Steps** (if applicable): If partially eligible or not eligible, briefly suggest what might help or what alternatives to consider.
        
        **Important Guidelines:**
        - Use simple, patient-friendly language
        - Be empathetic and encouraging
        - Avoid medical jargon
        - Keep it concise (150-200 words)
        - Do not give medical advice, only explain the assessment
        - Focus on the factual responses, not medical interpretation
        
        Generate the explanation now:
        """
        
        # ✅ FIX: Extract the text content from the response
        response = await manager.chat_with_retry_async(
            agent_name="ExplanationAgent",
            message=prompt
        )
        
        # Extract text from ChatCompletionResponse object
        if hasattr(response, 'choices') and len(response.choices) > 0:
            return response.choices[0].message.content
        elif hasattr(response, 'content'):
            return response.content
        elif isinstance(response, str):
            return response
        else:
            # Fallback: convert to string
            return str(response)


async def evaluate_explanation(explanation: str, trial_context: str) -> ExplanationEvaluation:
    """Evaluate if explanation is comprehensible enough"""
    async with AgentManager(max_retries=2, retry_delay=3.0) as manager:
        evaluator = manager.create_agent(
            agent_id=MISTRAL_AGENT_ID,
            name="ExplanationEvaluator",
            model=AgentModel.SMALL.value,
            response_format=ResponseFormat.JSON,
            response_model=ExplanationEvaluation,
            description="Evaluates medical explanations for patient comprehension"
        )
        
        eval_prompt = f"""
        You are an expert in medical communication. Evaluate the following explanation for patient comprehension.
        
        **Context:** {trial_context}
        
        **Explanation to evaluate:**
        {explanation}
        
        **Evaluation Criteria:**
        1. **Clarity** (0-25 points): Is the language simple and clear? No medical jargon?
        2. **Structure** (0-25 points): Is it well-organized? Easy to follow?
        3. **Completeness** (0-25 points): Does it address eligibility, key factors, and next steps?
        4. **Empathy** (0-25 points): Is it patient-friendly, encouraging, and respectful?
        
        **Scoring:**
        - 80-100: Excellent - Very easy to understand
        - 60-79: Good - Acceptable comprehension
        - 40-59: Fair - Needs improvement
        - 0-39: Poor - Hard to understand
        
        **Instructions:**
        1. Calculate comprehension_score (0-100)
        2. Set is_acceptable to true if score >= 60, false otherwise
        3. If score < 60, list specific issues (medical jargon, complex sentences, missing information, etc.)
        4. Provide specific suggestions for improvement
        
        Return a JSON object with: comprehension_score, is_acceptable, issues, suggestions
        """
        
        evaluation = await manager.chat_with_retry_async(
            agent_name="ExplanationEvaluator",
            message=eval_prompt,
            response_model=ExplanationEvaluation
        )
        
        return evaluation


async def generate_explanation_with_validation(
    nct_id: str, 
    trial_data: Dict[str, Any], 
    user_responses: Dict[str, bool],
    max_retries: int = 3
) -> Dict[str, Any]:
    """Generate explanation with automatic evaluation and rewriting if needed"""
    
    trial_context = f"Trial {trial_data['nct_id']}: {trial_data['title'][:100]}..."
    
    for attempt in range(max_retries):
        logger.info(f"Generating explanation (Attempt {attempt + 1}/{max_retries})...")
        
        # Generate explanation
        explanation = await generate_explanation(nct_id, trial_data, user_responses)
        
        # Evaluate explanation
        logger.info("Evaluating explanation comprehension...")
        evaluation = await evaluate_explanation(explanation, trial_context)
        
        logger.info(f"Comprehension score: {evaluation.comprehension_score}/100")
        
        # Check if acceptable
        if evaluation.is_acceptable:
            logger.info("✅ Explanation is comprehensible enough")
            return {
                'explanation': explanation,
                'comprehension_score': evaluation.comprehension_score,
                'attempts': attempt + 1,
                'evaluation': {
                    'score': evaluation.comprehension_score,
                    'is_acceptable': True
                }
            }
        
        # Log issues and retry
        logger.warning(f"⚠️ Explanation needs improvement (Score: {evaluation.comprehension_score}/100)")
        logger.warning(f"Issues: {', '.join(evaluation.issues)}")
        logger.info(f"Suggestions: {evaluation.suggestions}")
        
        if attempt < max_retries - 1:
            # Rewrite with feedback
            logger.info("Requesting rewrite with specific improvements...")
            explanation = await rewrite_explanation_with_feedback(
                nct_id, 
                trial_data, 
                user_responses, 
                explanation,
                evaluation
            )
    
    # If all retries failed, return last attempt with warning
    logger.error(f"❌ Failed to achieve acceptable comprehension after {max_retries} attempts")
    return {
        'explanation': explanation,
        'comprehension_score': evaluation.comprehension_score,
        'attempts': max_retries,
        'evaluation': {
            'score': evaluation.comprehension_score,
            'is_acceptable': False,
            'issues': evaluation.issues
        },
        'warning': 'Explanation may be difficult to understand'
    }


async def rewrite_explanation_with_feedback(
    nct_id: str,
    trial_data: Dict[str, Any],
    user_responses: Dict[str, bool],
    previous_explanation: str,
    evaluation: ExplanationEvaluation
) -> str:
    """Rewrite explanation based on evaluator feedback"""
    
    async with AgentManager(max_retries=3, retry_delay=5.0) as manager:
        agent = manager.create_agent(
            agent_id=MISTRAL_AGENT_ID,
            name="ExplanationRewriter",
            model=AgentModel.SMALL.value,
            description="Rewrites medical explanations based on feedback"
        )
        
        # Prepare Q&A summary
        inclusion_qa = []
        exclusion_qa = []
        
        for q_id, q_data in trial_data['questions']['inclusion'].items():
            answer = user_responses.get(q_id, None)
            if answer is not None:
                inclusion_qa.append(f"- {q_data['question']}: {'Yes' if answer else 'No'}")
        
        for q_id, q_data in trial_data['questions']['exclusion'].items():
            answer = user_responses.get(q_id, None)
            if answer is not None:
                exclusion_qa.append(f"- {q_data['question']}: {'Yes' if answer else 'No'}")
        
        inclusion_text = "\n".join(inclusion_qa) if inclusion_qa else "No inclusion questions answered"
        exclusion_text = "\n".join(exclusion_qa) if exclusion_qa else "No exclusion questions answered"
        
        issues_text = "\n".join([f"- {issue}" for issue in evaluation.issues])
        
        # ✅ Utilise la méthode helper
        suggestions_text = evaluation.get_suggestions_text() if hasattr(evaluation, 'get_suggestions_text') else str(evaluation.suggestions)
        
        rewrite_prompt = f"""
        You are a medical assistant. Your previous explanation was evaluated and needs improvement.
        
        **Trial Information:**
        - Trial ID: {trial_data['nct_id']}
        - Title: {trial_data['title']}
        
        **Patient's Responses:**
        
        Exclusion Criteria:
        {exclusion_text}
        
        Inclusion Criteria:
        {inclusion_text}
        
        **Your Previous Explanation:**
        {previous_explanation}
        
        **Evaluation Score:** {evaluation.comprehension_score}/100 (Below acceptable threshold)
        
        **Issues Identified:**
        {issues_text}
        
        **Improvement Suggestions:**
        {suggestions_text}
        
        **Task:**
        Rewrite the explanation addressing ALL the issues mentioned above. Focus on:
        
        1. **Use simpler language** - Replace any complex medical terms with everyday words
        2. **Shorter sentences** - Break long sentences into shorter ones (max 15 words each)
        3. **Clear structure** - Use clear topic sentences for each paragraph
        4. **Be specific** - Mention exact criteria that were/weren't met
        5. **Be encouraging** - Show empathy and provide hope where appropriate
        
        **Format Requirements:**
        - 3-4 short paragraphs
        - 150-200 words total
        - Start with eligibility status
        - Explain key factors clearly
        - End with actionable next steps or encouragement
        
        Write the improved explanation now (do NOT include any meta-commentary or evaluation):
        """
        
        response = await manager.chat_with_retry_async(
            agent_name="ExplanationRewriter",
            message=rewrite_prompt
        )
        
        # Extract text
        if hasattr(response, 'choices') and len(response.choices) > 0:
            return response.choices[0].message.content
        elif hasattr(response, 'content'):
            return response.content
        elif isinstance(response, str):
            return response
        else:
            return str(response)


@app.route('/explain_result', methods=['POST'])
def explain_result():
    """Generate AI explanation for a specific trial result"""
    request_data = request.json
    nct_id = request_data.get('nct_id')
    
    if not nct_id:
        return jsonify({'error': 'Trial ID is required'}), 400
    
    data = load_session_data()
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
        return await generate_explanation_with_validation(nct_id, trial_data, user_responses)
    
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


if __name__ == '__main__':
    app.run(debug=True, port=5000)