"""Test the workflow with structured responses"""
import asyncio
import json
from typing import List, Dict, Any
from src.agent_manager import AgentManager, AgentModel, ResponseFormat
from src.response_models import IllnessInfo, EligibilityQuestions
from src.config import MISTRAL_AGENT_ID
from src.logger import logger
from src.trials import fetch_trials_async


async def get_illness_type_structured(user_illness: str):
    """Get illness type with structured response."""
    logger.info("=" * 60)
    logger.info("🏥 GET ILLNESS TYPE (STRUCTURED)")
    logger.info("=" * 60)
    
    async with AgentManager(max_retries=3, retry_delay=5.0) as manager:
        # Create an agent with structured response format
        agent = manager.create_agent(
            agent_id=MISTRAL_AGENT_ID,
            name="IllnessTypeAgent",
            model=AgentModel.SMALL.value,
            response_format=ResponseFormat.JSON,
            response_model=IllnessInfo  # Define expected structure
        )
        
        prompt = f"""
        The response MUST be in English.
        Analyze the following patient description and return a JSON object compatible with the IllnessInfo model.
        Patient input: {user_illness}
        
        Rules:
        - illness_name: general illness name only (no types, subtypes, stages, variants, or anatomical locations). 
            If it contains numbers, stages, or variants, replace with the general term.
        - type: specific type or subtype if mentioned, else null
        - subtype: specific variant if mentioned, else null
        - stage: disease stage if explicitly mentioned (e.g., early, late, stage IV), else null
        - anatomical_location: primary affected body part or system if mentioned, else null
        - organ_touched: specific organ or tissue affected if mentioned, else null
        - category: medical category (e.g., chronic, acute, infectious, genetic, autoimmune)
        - severity: mild/moderate/severe if mentioned, else null
        - affected_systems: list affected body systems (e.g., urinary, nervous, visual)
        - keywords: include any types, stages, variants, organs, or other relevant terms
        - confidence_score: optional numeric confidence if applicable, else null
        - Use null for unknown fields.
        - Output must be valid JSON only; do not add explanations or extra text.

        
        Normalization rules:
        - All returned medical terms MUST be in canonical singular form.
        - Use medical concept singulars, not grammatical corrections.
        Examples:
        - "diabetes" → "diabetes"
        - "kidneys" → "kidney"
        - "eyes" → "eye"
        - "ulcers" → "ulcer"
        - Do NOT invent or transform medical terms.
        """
        
        # Get structured response
        response = await manager.chat_with_retry_async(
            agent_name="IllnessTypeAgent",
            message=prompt,
            response_model=IllnessInfo  # Override if needed
        )
        
        logger.info(f"Structured Illness Info: {response}")
        return response


async def get_illness(user_input: str = None):
    """Compare different response formats."""
    # Test structured format
    structured_result = await get_illness_type_structured(user_input)
    print("\n" + "=" * 60)
    print("STRUCTURED FORMAT RESULT:")
    if isinstance(structured_result, IllnessInfo):
        print(f"Illness Name: {structured_result.illness_name}")
        print(f"Type: {structured_result.type}")
        print(f"Subtype: {structured_result.subtype}")
        print(f"Stage: {structured_result.stage}")
        print(f"Anatomical Location: {structured_result.anatomical_location}")
        print(f"Organ Touched: {structured_result.organ_touched}")
        print(f"Category: {structured_result.category}")
        print(f"Affected Systems: {', '.join(structured_result.affected_systems)}")
        print(f"Keywords: {', '.join(structured_result.keywords)}")
    else:
        print(structured_result)
    print("=" * 60)
    return structured_result


async def get_trials_for_illness(illness_: str):
    """Fetch clinical trials for a given illness (async).
    
    Args:
        illness_name (str): Name of the illness to search trials for.
    """
    logger.info("=" * 60)
    logger.info(f"🔍 FETCH CLINICAL TRIALS FOR: {illness_}")
    logger.info("=" * 60)
    
    trials = await fetch_trials_async(  # Changed to async version
        condition=illness_,
        max_studies=100,
        return_status=True,
        json_output=True,
        output_name=f"trials_for_{illness_.replace(' ', '_')}.json",
        timeout=10,
    )
    
    logger.info(f"Found {len(trials) if trials else 0} trials for {illness_}")
    if trials:
        study=0
        logger.info("Sample trials:")
        for trial in trials[:5]:
            study+=1
            logger.info(f"Trial {study}:")
            protocol = trial.get('protocolSection', {})
            identification = protocol.get('identificationModule', {})
            status_module = protocol.get('statusModule', {})
            
            title = identification.get('briefTitle', 'N/A')
            status = status_module.get('overallStatus', 'N/A')
            
            logger.info(f"- {title} (Status: {status})")
    
    return trials


def trial_contains_keywords(study: Dict[str, Any], keywords: List[str]) -> tuple:
    """Vérifie si un trial contient au moins un mot-clé et calcule un score"""
    protocol_section = study.get("protocolSection", {})
    
    # Extraire tous les textes pertinents
    texts_to_search = []
    
    # Titre
    identification = protocol_section.get("identificationModule", {})
    title = identification.get("officialTitle") or identification.get("briefTitle") or ""
    texts_to_search.append(title)
    
    # Description
    description_module = protocol_section.get("descriptionModule", {})
    brief_summary = description_module.get("briefSummary") or ""
    detailed_description = description_module.get("detailedDescription") or ""
    texts_to_search.extend([brief_summary, detailed_description])
    
    # Arm descriptions
    arms_module = protocol_section.get("armsInterventionsModule", {})
    arm_groups = arms_module.get("armGroups", [])
    for arm in arm_groups:
        arm_desc = arm.get("description") or ""
        arm_label = arm.get("label") or ""
        texts_to_search.extend([arm_desc, arm_label])
    
    # Intervention descriptions
    interventions = arms_module.get("interventions", [])
    for intervention in interventions:
        int_desc = intervention.get("description") or ""
        int_name = intervention.get("name") or ""
        texts_to_search.extend([int_desc, int_name])
    
    # Conditions
    conditions_module = protocol_section.get("conditionsModule", {})
    conditions = conditions_module.get("conditions", [])
    texts_to_search.extend(conditions)
    
    # Combiner tous les textes et convertir en minuscules
    combined_text = " ".join(texts_to_search).lower()
    
    # Calculer le score: nombre d'occurrences de chaque mot-clé
    total_occurrences = 0
    keywords_found = []
    for keyword in keywords:
        keyword_lower = keyword.lower()
        count = combined_text.count(keyword_lower)
        if count > 0:
            total_occurrences += count
            keywords_found.append(keyword)
    
    # Nombre de mots-clés différents trouvés (critère principal)
    num_keywords_found = len(keywords_found)
    
    return num_keywords_found, total_occurrences, keywords_found


async def filter_trials_by_information(illness_info: IllnessInfo, trials: List[Dict[str, Any]]):
    """Filter clinical trials based on detailed illness information.
    
    Args:
        illness_info (IllnessInfo): Structured illness information.
        trials (List[Dict[str, Any]]): List of clinical trials to filter.
    
    Returns:
        List of filtered and scored trials.
    """
    logger.info("=" * 60)
    logger.info(f"🔍 FILTER CLINICAL TRIALS FOR: {illness_info.illness_name}")
    logger.info("=" * 60)
    
    # Construire la liste de mots-clés à partir de l'IllnessInfo
    list_of_words = []
    
    # Ajouter les mots-clés fournis
    if illness_info.keywords:
        list_of_words.extend(illness_info.keywords)
    
    # Ajouter le type si présent
    if illness_info.type:
        list_of_words.append(illness_info.type)
    
    # Ajouter les organes touchés
    if illness_info.organ_touched:
        list_of_words.extend(illness_info.organ_touched)
    
    # Ajouter la localisation anatomique
    if illness_info.anatomical_location:
        list_of_words.extend(illness_info.anatomical_location)
    
    # Ajouter les systèmes affectés
    if illness_info.affected_systems:
        list_of_words.extend(illness_info.affected_systems)
    
    # Enlever les doublons et convertir en minuscules
    list_of_words = list(set([word.lower() for word in list_of_words if word]))
    
    logger.info(f"Keywords to filter: {list_of_words}")
    
    if not list_of_words:
        logger.warning("No keywords available for filtering")
        return trials
    
    # Étape 1: Identifier les mots-clés universels
    logger.info("Analyzing universal keywords...")
    keyword_presence = {keyword: 0 for keyword in list_of_words}
    
    for study in trials:
        _, _, keywords_found = trial_contains_keywords(study, list_of_words)
        for keyword in keywords_found:
            keyword_presence[keyword] += 1
    
    # Mots-clés présents dans tous les trials
    universal_keywords = [kw for kw, count in keyword_presence.items() if count == len(trials)]
    filtered_keywords = [kw for kw in list_of_words if kw not in universal_keywords]
    
    logger.info(f"Total trials: {len(trials)}")
    for keyword, count in keyword_presence.items():
        logger.info(f"  '{keyword}': present in {count}/{len(trials)} trials")
    
    if universal_keywords:
        logger.warning(f"Universal keywords excluded: {universal_keywords}")
    else:
        logger.info("No universal keywords detected")
    
    logger.info(f"Keywords used for filtering: {filtered_keywords}")
    
    if not filtered_keywords:
        logger.warning("All keywords are universal, returning all trials")
        return trials
    
    # Étape 2: Filtrer les studies avec les mots-clés non-universels
    filtered_studies_with_scores = []
    
    for study in trials:
        num_keywords, total_occurrences, keywords_found = trial_contains_keywords(study, filtered_keywords)
        if num_keywords > 0:
            filtered_studies_with_scores.append({
                "study": study,
                "num_keywords": num_keywords,
                "total_occurrences": total_occurrences,
                "keywords_found": keywords_found
            })
    
    # Trier par nombre de mots-clés différents (priorité 1), puis par occurrences totales (priorité 2)
    filtered_studies_with_scores.sort(key=lambda x: (x["num_keywords"], x["total_occurrences"]), reverse=True)
    
    logger.info(f"Filtered trials: {len(filtered_studies_with_scores)}/{len(trials)}")
    
    # Afficher les top 10
    logger.info("\n--- Top 10 trials by relevance ---")
    for i, item in enumerate(filtered_studies_with_scores[:10]):
        study = item["study"]
        num_keywords = item["num_keywords"]
        total_occurrences = item["total_occurrences"]
        keywords = item["keywords_found"]
        
        protocol = study.get("protocolSection", {})
        nct_id = protocol.get("identificationModule", {}).get("nctId", "N/A")
        title = protocol.get("identificationModule", {}).get("officialTitle") or \
                protocol.get("identificationModule", {}).get("briefTitle", "N/A")
        
        logger.info(f"\n{i+1}. {nct_id}")
        logger.info(f"   Keywords found: {num_keywords}/{len(filtered_keywords)} ({', '.join(keywords)})")
        logger.info(f"   Total occurrences: {total_occurrences}")
        logger.info(f"   Title: {title[:100]}...")
    
    # Sauvegarder les résultats filtrés
    filtered_trials = {
        "studies": [item["study"] for item in filtered_studies_with_scores],
        "metadata": {
            "original_keywords": list_of_words,
            "filtered_keywords": filtered_keywords,
            "universal_keywords": universal_keywords,
            "total_trials": len(trials),
            "filtered_trials": len(filtered_studies_with_scores)
        }
    }
    
    output_filename = f"filtered_trials_{illness_info.illness_name.replace(' ', '_')}.json"
    with open(output_filename, 'w', encoding='utf-8') as f:
        json.dump(filtered_trials, f, indent=2, ensure_ascii=False)
    
    logger.info(f"\nFiltered results saved to '{output_filename}'")
    
    return filtered_studies_with_scores


def extract_eligibility_criteria(filtered_trials: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Extract eligibility criteria from filtered trials.
    
    Args:
        filtered_trials (List[Dict[str, Any]]): List of filtered trials with scores.
    
    Returns:
        List of trials with extracted eligibility information.
    """
    logger.info("=" * 60)
    logger.info("📋 EXTRACTING ELIGIBILITY CRITERIA")
    logger.info("=" * 60)
    
    trials_eligibility = []
    
    for item in filtered_trials:
        study = item["study"]
        protocol_section = study.get('protocolSection', {})
        
        # Extraire l'ID du trial
        identification_module = protocol_section.get('identificationModule', {})
        nct_id = identification_module.get('nctId', 'N/A')
        
        # Extraire le titre pour référence
        title = identification_module.get('officialTitle') or identification_module.get('briefTitle', 'N/A')
        
        # Extraire les critères d'éligibilité
        eligibility_module = protocol_section.get('eligibilityModule', {})
        eligibility_criteria = eligibility_module.get('eligibilityCriteria', 'N/A')
        sex = eligibility_module.get('sex', 'N/A')
        minimum_age = eligibility_module.get('minimumAge', 'N/A')
        maximum_age = eligibility_module.get('maximumAge', 'N/A')
        healthy_volunteers = eligibility_module.get('healthyVolunteers', 'N/A')
        
        trial_info = {
            'nct_id': nct_id,
            'title': title,
            'relevance_score': {
                'num_keywords': item['num_keywords'],
                'total_occurrences': item['total_occurrences'],
                'keywords_found': item['keywords_found']
            },
            'eligibility': {
                'criteria': eligibility_criteria,
                'sex': sex,
                'minimum_age': minimum_age,
                'maximum_age': maximum_age,
                'healthy_volunteers': healthy_volunteers
            }
        }
        
        trials_eligibility.append(trial_info)
    
    logger.info(f"Extracted eligibility criteria for {len(trials_eligibility)} trials")
    
    # Afficher quelques exemples
    logger.info("\n--- Sample eligibility criteria (Top 3) ---")
    for i, trial in enumerate(trials_eligibility[:3]):
        logger.info(f"\n{i+1}. NCT ID: {trial['nct_id']}")
        logger.info(f"   Title: {trial['title'][:80]}...")
        logger.info(f"   Relevance: {trial['relevance_score']['num_keywords']} keywords ({', '.join(trial['relevance_score']['keywords_found'])})")
        logger.info(f"   Sex: {trial['eligibility']['sex']}")
        logger.info(f"   Age Range: {trial['eligibility']['minimum_age']} to {trial['eligibility']['maximum_age']}")
        logger.info(f"   Healthy Volunteers: {trial['eligibility']['healthy_volunteers']}")
        criteria = trial['eligibility']['criteria']
        if criteria != 'N/A':
            logger.info(f"   Criteria (first 200 chars): {criteria[:200]}...")
        else:
            logger.info(f"   Criteria: {criteria}")
    
    # Statistiques
    logger.info("\n--- Eligibility Statistics ---")
    
    sex_stats = {}
    for trial in trials_eligibility:
        sex = trial['eligibility']['sex']
        sex_stats[sex] = sex_stats.get(sex, 0) + 1
    
    logger.info("Distribution by sex:")
    for sex, count in sex_stats.items():
        logger.info(f"  {sex}: {count} trials")
    
    healthy_vol_stats = {}
    for trial in trials_eligibility:
        hv = trial['eligibility']['healthy_volunteers']
        healthy_vol_stats[hv] = healthy_vol_stats.get(hv, 0) + 1
    
    logger.info("\nHealthy volunteers accepted:")
    for hv, count in healthy_vol_stats.items():
        logger.info(f"  {hv}: {count} trials")
    
    with_criteria = sum(1 for t in trials_eligibility if t['eligibility']['criteria'] != 'N/A')
    without_criteria = len(trials_eligibility) - with_criteria
    
    logger.info(f"\nTrials with detailed criteria: {with_criteria}")
    logger.info(f"Trials without detailed criteria: {without_criteria}")
    
    return trials_eligibility


async def generate_eligibility_questions(trials_with_eligibility: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Generate inclusion and exclusion questions from eligibility criteria.
    
    Args:
        trials_with_eligibility (List[Dict[str, Any]]): Trials with eligibility criteria
    
    Returns:
        List of trials with generated questions
    """
    logger.info("=" * 60)
    logger.info("📝 GENERATING ELIGIBILITY QUESTIONS")
    logger.info("=" * 60)
    
    trials_with_questions = []
    
    for i, trial in enumerate(trials_with_eligibility):
        nct_id = trial['nct_id']
        title = trial['title']
        criteria = trial['eligibility']['criteria']
        
        if criteria == 'N/A' or not criteria.strip():
            logger.warning(f"Skipping {nct_id}: No eligibility criteria available")
            continue
        
        try:
            logger.info(f"Processing {i+1}/{len(trials_with_eligibility)}: {nct_id}")
            
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
                - Limit to a maximum of 10 questions per category (inclusion/exclusion).

                Return a JSON object:
                
                {{"nct_id": "{nct_id}",
                "inclusion_questions": ["list of simplified yes/no questions for inclusion"],
                "exclusion_questions": ["list of simplified yes/no questions for exclusion"]}}

                Examples:
                - Inclusion: "Type 2 diabetes diagnosed within last 5 years"  
                  Question: "Have you been diagnosed with type 2 diabetes in the last 5 years?"

                - Exclusion: "History of cancer"  
                  Question: "Have you ever been diagnosed with cancer?"
                """
                
                questions = await manager.chat_with_retry_async(
                    agent_name="QuestionGeneratorAgent",
                    message=prompt,
                    response_model=EligibilityQuestions
                )
            
            trial_with_questions = {
                **trial,
                'questions': {
                    'inclusion': questions.inclusion_questions,
                    'exclusion': questions.exclusion_questions
                }
            }
            
            trials_with_questions.append(trial_with_questions)
            logger.info(f"  ✓ Generated {len(questions.inclusion_questions)} inclusion and {len(questions.exclusion_questions)} exclusion questions")
            
            # Rate limiting
            await asyncio.sleep(1)
            
        except Exception as e:
            logger.error(f"  ✗ Error processing {nct_id}: {e}")
            continue
    
    logger.info(f"\nSuccessfully generated questions for {len(trials_with_questions)}/{len(trials_with_eligibility)} trials")
    
    # Display sample questions
    logger.info("\n--- Sample Questions (Top 3) ---")
    for i, trial in enumerate(trials_with_questions[:3]):
        logger.info(f"\n{i+1}. Trial: {trial['nct_id']}")
        logger.info(f"   Title: {trial['title'][:80]}...")
        
        logger.info(f"\n   INCLUSION QUESTIONS ({len(trial['questions']['inclusion'])}):")
        for j, question in enumerate(trial['questions']['inclusion'][:5], 1):
            logger.info(f"     {j}. {question}")
        
        logger.info(f"\n   EXCLUSION QUESTIONS ({len(trial['questions']['exclusion'])}):")
        for j, question in enumerate(trial['questions']['exclusion'][:5], 1):
            logger.info(f"     {j}. {question}")
    
    # Statistics
    total_inclusion = sum(len(t['questions']['inclusion']) for t in trials_with_questions)
    total_exclusion = sum(len(t['questions']['exclusion']) for t in trials_with_questions)
    
    logger.info("\n--- Question Generation Statistics ---")
    logger.info(f"Total inclusion questions: {total_inclusion}")
    logger.info(f"Total exclusion questions: {total_exclusion}")
    if trials_with_questions:
        logger.info(f"Average inclusion questions per trial: {total_inclusion / len(trials_with_questions):.1f}")
        logger.info(f"Average exclusion questions per trial: {total_exclusion / len(trials_with_questions):.1f}")
    
    return trials_with_questions


if __name__ == "__main__":
    txt = """
    I have diabetes type 2 with complications affecting my kidneys and eyes
    """
    
    async def main():
        # Étape 1: Extraire les informations de la maladie
        print("\nStep 1: Extracting illness information...\n")
        structured_result = await get_illness(user_input=txt)
        
        if isinstance(structured_result, IllnessInfo):
            # Étape 2: Récupérer les trials
            print("\nStep 2: Fetching clinical trials...\n")
            illness_name = structured_result.illness_name
            trials = await get_trials_for_illness(illness_=illness_name)
            
            if trials:
                # Étape 3: Filtrer les trials selon les informations détaillées
                print("\nStep 3: Filtering trials by detailed information...\n")
                filtered_trials = await filter_trials_by_information(
                    illness_info=structured_result,
                    trials=trials
                )
                
                if filtered_trials:
                    # Étape 4: Extraire les critères d'éligibilité
                    print("\nStep 4: Extracting eligibility criteria...\n")
                    trials_with_eligibility = extract_eligibility_criteria(filtered_trials)
                    
                    # Étape 5: Générer les questions d'éligibilité
                    print("\nStep 5: Generating eligibility questions...\n")
                    trials_with_questions = await generate_eligibility_questions(trials_with_eligibility)
                    
                    # Sauvegarder les résultats finaux
                    output_file = f"trials_with_questions_{structured_result.illness_name.replace(' ', '_')}.json"
                    with open(output_file, 'w', encoding='utf-8') as f:
                        json.dump(trials_with_questions, f, indent=2, ensure_ascii=False)
                    
                    logger.info(f"\n✅ Complete workflow data saved to '{output_file}'")
                    print(f"\n✅ Workflow complete! Generated questions for {len(trials_with_questions)} trials.")
                else:
                    print("\n⚠️  No trials passed the filtering criteria.")
            else:
                print("\n❌ No trials found.")
        else:
            print("\n❌ Failed to extract illness information.")
    
    asyncio.run(main())

