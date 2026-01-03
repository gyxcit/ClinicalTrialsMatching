import json

# Charger les données
with open('trials_with_questions_diabetes.json', 'r', encoding='utf-8') as f:
    trials_data = json.load(f)

# Restructurer les données
restructured_trials = []

for trial in trials_data:
    nct_id = trial['nct_id']
    
    # Restructurer les questions d'inclusion
    inclusion_questions = {}
    for idx, question in enumerate(trial['questions']['inclusion'], start=1):
        question_id = f"{nct_id}_INC_{idx:03d}"
        inclusion_questions[question_id] = {
            "question": question,
            "response": None  # None par défaut, à remplir par le patient
        }
    
    # Restructurer les questions d'exclusion
    exclusion_questions = {}
    for idx, question in enumerate(trial['questions']['exclusion'], start=1):
        question_id = f"{nct_id}_EXC_{idx:03d}"
        exclusion_questions[question_id] = {
            "question": question,
            "response": None  # None par défaut, à remplir par le patient
        }
    
    # Construire le trial restructuré
    restructured_trial = {
        "nct_id": nct_id,
        "title": trial['title'],
        "relevance_score": trial.get('relevance_score'),
        "eligibility": trial.get('eligibility'),
        "questions": {
            "inclusion": inclusion_questions,
            "exclusion": exclusion_questions
        }
    }
    
    restructured_trials.append(restructured_trial)

# Sauvegarder le nouveau format
output_file = 'trials_questions_structured.json'
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(restructured_trials, f, indent=2, ensure_ascii=False)

print(f"✅ Restructured data saved to '{output_file}'")
print(f"\nTotal trials: {len(restructured_trials)}")

# Afficher un exemple
print("\n" + "="*80)
print("EXEMPLE DE STRUCTURE")
print("="*80)

if restructured_trials:
    example = restructured_trials[0]
    print(f"\nTrial: {example['nct_id']}")
    print(f"Title: {example['title'][:80]}...")
    
    print(f"\nINCLUSION QUESTIONS ({len(example['questions']['inclusion'])}):")
    for q_id, q_data in list(example['questions']['inclusion'].items())[:3]:
        print(f"  {q_id}:")
        print(f"    Question: {q_data['question']}")
        print(f"    Response: {q_data['response']}")
    
    print(f"\nEXCLUSION QUESTIONS ({len(example['questions']['exclusion'])}):")
    for q_id, q_data in list(example['questions']['exclusion'].items())[:3]:
        print(f"  {q_id}:")
        print(f"    Question: {q_data['question']}")
        print(f"    Response: {q_data['response']}")

print("\n" + "="*80)
print("STATISTIQUES")
print("="*80)

total_inclusion = sum(len(t['questions']['inclusion']) for t in restructured_trials)
total_exclusion = sum(len(t['questions']['exclusion']) for t in restructured_trials)

print(f"Total inclusion questions: {total_inclusion}")
print(f"Total exclusion questions: {total_exclusion}")
print(f"Total questions: {total_inclusion + total_exclusion}")

