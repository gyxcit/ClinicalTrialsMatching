import json

data = "trials_for_diabetes.json"

with open(data, 'r', encoding='utf-8') as f:
    trials = json.load(f)

list_of_words = ["kidney", "eye", "diabete", "type 2"]

def trial_contains_keywords(study, keywords):
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

# Étape 1: Identifier les mots-clés qui apparaissent dans TOUS les trials
print("=== Analyse des mots-clés universels ===")
studies = trials.get("studies", [])
keyword_presence = {keyword: 0 for keyword in list_of_words}

for study in studies:
    _, _, keywords_found = trial_contains_keywords(study, list_of_words)
    for keyword in keywords_found:
        keyword_presence[keyword] += 1

# Mots-clés présents dans tous les trials
universal_keywords = [kw for kw, count in keyword_presence.items() if count == len(studies)]
filtered_keywords = [kw for kw in list_of_words if kw not in universal_keywords]

print(f"Nombre total de trials: {len(studies)}")
for keyword, count in keyword_presence.items():
    print(f"  '{keyword}': présent dans {count}/{len(studies)} trials")

if universal_keywords:
    print(f"\n⚠️  Mots-clés universels exclus du filtrage: {universal_keywords}")
else:
    print("\n✓ Aucun mot-clé universel détecté")

print(f"\nMots-clés utilisés pour le filtrage: {filtered_keywords}\n")

# Étape 2: Filtrer les studies avec les mots-clés non-universels
filtered_studies_with_scores = []

for study in studies:
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

print(f"Nombre de trials filtrés: {len(filtered_studies_with_scores)}")

# Sauvegarder les résultats filtrés avec scores
filtered_trials = {
    "studies": [item["study"] for item in filtered_studies_with_scores],
    "nextPageToken": trials.get("nextPageToken"),
    "metadata": {
        "original_keywords": list_of_words,
        "filtered_keywords": filtered_keywords,
        "universal_keywords": universal_keywords
    }
}

with open("filtered_trials_results.json", 'w', encoding='utf-8') as f:
    json.dump(filtered_trials, f, indent=2, ensure_ascii=False)

print("\nRésultats sauvegardés dans 'filtered_trials_results.json'")

# Afficher les exemples avec scores
print("\n--- Top 10 trials par pertinence ---")
for i, item in enumerate(filtered_studies_with_scores[:10]):
    study = item["study"]
    num_keywords = item["num_keywords"]
    total_occurrences = item["total_occurrences"]
    keywords = item["keywords_found"]
    
    protocol = study.get("protocolSection", {})
    nct_id = protocol.get("identificationModule", {}).get("nctId", "N/A")
    title = protocol.get("identificationModule", {}).get("officialTitle") or \
            protocol.get("identificationModule", {}).get("briefTitle", "N/A")
    
    print(f"\n{i+1}. {nct_id}")
    print(f"   Mots-clés trouvés: {num_keywords}/{len(filtered_keywords)} ({', '.join(keywords)})")
    print(f"   Occurrences totales: {total_occurrences}")
    print(f"   Title: {title[:100]}...")

# Statistiques par mot-clé (seulement les mots-clés filtrés)
if filtered_keywords:
    print("\n--- Statistiques par mot-clé ---")
    keyword_stats = {keyword: 0 for keyword in filtered_keywords}
    for item in filtered_studies_with_scores:
        for keyword in item["keywords_found"]:
            if keyword in keyword_stats:
                keyword_stats[keyword] += 1

    for keyword, count in keyword_stats.items():
        print(f"{keyword}: {count} trials")

    # Statistiques par nombre de mots-clés
    print("\n--- Distribution par nombre de mots-clés ---")
    distribution = {}
    for item in filtered_studies_with_scores:
        num = item["num_keywords"]
        distribution[num] = distribution.get(num, 0) + 1

    for num in sorted(distribution.keys(), reverse=True):
        count = distribution[num]
        print(f"{num} mots-clés: {count} trials")
else:
    print("\n⚠️  Tous les mots-clés sont universels, aucun filtrage possible")