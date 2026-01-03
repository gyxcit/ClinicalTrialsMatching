"""Service for filtering clinical trials based on keywords"""
from typing import List, Dict, Any, Tuple
from ..response_models import IllnessInfo
from ..logger import logger
import asyncio


class TrialFilter:
    """Filters clinical trials based on illness keywords and relevance"""
    
    @staticmethod
    def contains_keywords(study: Dict[str, Any], keywords: List[str]) -> Tuple[int, int, List[str]]:
        """
        Check if trial contains keywords and calculate relevance score.
        
        Args:
            study (Dict[str, Any]): Clinical trial data
            keywords (List[str]): Keywords to search for
            
        Returns:
            Tuple[int, int, List[str]]: (num_keywords_found, total_occurrences, keywords_found)
        """
        protocol_section = study.get("protocolSection", {})
        texts_to_search = []
        
        # Extract relevant texts
        identification = protocol_section.get("identificationModule", {})
        title = identification.get("officialTitle") or identification.get("briefTitle") or ""
        texts_to_search.append(title)
        
        description_module = protocol_section.get("descriptionModule", {})
        texts_to_search.extend([
            description_module.get("briefSummary") or "",
            description_module.get("detailedDescription") or ""
        ])
        
        combined_text = " ".join(texts_to_search).lower()
        
        # Calculate scores
        total_occurrences = 0
        keywords_found = []
        for keyword in keywords:
            keyword_lower = keyword.lower()
            count = combined_text.count(keyword_lower)
            if count > 0:
                total_occurrences += count
                keywords_found.append(keyword)
        
        return len(keywords_found), total_occurrences, keywords_found
    
    async def filter_by_keywords(self, illness_info: IllnessInfo, trials: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filter trials based on illness keywords and relevance.
        
        Args:
            illness_info (IllnessInfo): Structured illness information
            trials (List[Dict[str, Any]]): List of clinical trials
            
        Returns:
            List[Dict[str, Any]]: Filtered trials with relevance scores
        """
        logger.info("🔍 Filtering trials by relevance...")
        
        keywords = self._extract_keywords(illness_info)
        
        if not keywords:
            logger.warning("No keywords available for filtering")
            return trials
        
        # Remove universal keywords
        filtered_keywords = self._remove_universal_keywords(keywords, trials)
        
        if not filtered_keywords:
            logger.warning("All keywords are universal")
            return trials
        
        # Filter and score trials
        filtered_studies = []
        for study in trials:
            num_keywords, total_occurrences, keywords_found = self.contains_keywords(study, filtered_keywords)
            if num_keywords > 0:
                filtered_studies.append({
                    "study": study,
                    "num_keywords": num_keywords,
                    "total_occurrences": total_occurrences,
                    "keywords_found": keywords_found
                })
        
        # Sort by relevance
        filtered_studies.sort(key=lambda x: (x["num_keywords"], x["total_occurrences"]), reverse=True)
        
        logger.info(f"Filtered {len(filtered_studies)}/{len(trials)} trials")
        return filtered_studies
    
    def _extract_keywords(self, illness_info: IllnessInfo) -> List[str]:
        """Extract all keywords from illness info"""
        keywords = []
        
        if illness_info.keywords:
            keywords.extend(illness_info.keywords)
        if illness_info.type:
            keywords.append(illness_info.type)
        if illness_info.organ_touched:
            keywords.extend(illness_info.organ_touched)
        if illness_info.anatomical_location:
            keywords.extend(illness_info.anatomical_location)
        if illness_info.affected_systems:
            keywords.extend(illness_info.affected_systems)
        
        return list(set([word.lower() for word in keywords if word]))
    
    def _remove_universal_keywords(self, keywords: List[str], trials: List[Dict[str, Any]]) -> List[str]:
        """Remove keywords that appear in all trials"""
        keyword_presence = {keyword: 0 for keyword in keywords}
        
        for study in trials:
            _, _, keywords_found = self.contains_keywords(study, keywords)
            for keyword in keywords_found:
                keyword_presence[keyword] += 1
        
        universal_keywords = [kw for kw, count in keyword_presence.items() if count == len(trials)]
        return [kw for kw in keywords if kw not in universal_keywords]
    
    @staticmethod
    def extract_eligibility_criteria(filtered_trials: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Extract eligibility criteria from filtered trials.
        
        Args:
            filtered_trials (List[Dict[str, Any]]): Filtered trials with scores
            
        Returns:
            List[Dict[str, Any]]: Trials with extracted eligibility information
        """
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