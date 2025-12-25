""" 
TRIALS FETCHER
---------------
Module to fetch clinical trials data from an external API based on medical conditions 
and filter by clinical statuses.

"""
import json
import logging
from typing import List, Dict, Any, Optional, Union
import requests
import pandas as pd
import asyncio
from concurrent.futures import ThreadPoolExecutor

from .config import (
    CLINICAL_TRIALS_BASE_URL, 
    CLINICAL_TRIALS_STATUSES_FILTER, 
    CLINICAL_TRIALS_PAGE_SIZE_LIMIT
)

logger = logging.getLogger(__name__)


def fetch_trials(
    condition: str,
    max_studies: int = 1000,
    return_status: bool = True,
    json_output: bool = False,
    output_name: str = "output",
    timeout: int = 30
) -> Optional[Union[List[Dict[str, Any]], pd.DataFrame]]:
    """Fetch clinical trials data based on condition and filter by clinical statuses.
    
    Args:
        condition: Medical condition to search for
        max_studies: Maximum number of studies to fetch (default: 1000)
        return_status: If True, return data; if False, save to file
        json_output: If True and return_status=False, save as JSON; else CSV
        output_name: Base name for output file (without extension)
        timeout: Request timeout in seconds (default: 30)
        
    Returns:
        List of studies if return_status=True, None if saved to file
        
    Raises:
        requests.RequestException: If the API request fails
        ValueError: If condition is empty or max_studies is invalid
    """
    # Validate inputs
    if not condition or not condition.strip():
        raise ValueError("Condition cannot be empty")
    
    if max_studies <= 0:
        raise ValueError("max_studies must be positive")
    
    # Prepare request parameters
    params = {
        "query.cond": condition.strip(),
        "filter.overallStatus": ",".join(CLINICAL_TRIALS_STATUSES_FILTER),
        "pageSize": min(max_studies, CLINICAL_TRIALS_PAGE_SIZE_LIMIT),  # API limit
        "format": "json"
    }
    
    try:
        logger.info(f"Fetching trials for condition: {condition}")
        
        # Make the request
        resp = requests.get(CLINICAL_TRIALS_BASE_URL, params=params, timeout=timeout)
        resp.raise_for_status()
        
        # Parse the response
        data = resp.json()
        studies = data.get("studies", [])
        
        logger.info(f"Successfully fetched {len(studies)} studies")

        if json_output:
            output_file = f"{output_name}.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved data to {output_file}")
        else:
            output_file = f"{output_name}.csv"
            pd.DataFrame(studies).to_csv(output_file, index=False)
            logger.info(f"Saved data to {output_file}")
            
        # Return or save the data
        if return_status:
            return studies
            
    except requests.RequestException as e:
        logger.error(f"Error fetching trials: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise

async def fetch_trials_async(
    condition: str,
    max_studies: int = 1000,
    return_status: bool = True,
    json_output: bool = False,
    output_name: str = "output",
    timeout: int = 30
) -> Optional[Union[List[Dict[str, Any]], pd.DataFrame]]:
    """Async wrapper for fetch_trials.
    
    Args:
        Same as fetch_trials
        
    Returns:
        Same as fetch_trials
    """
    loop = asyncio.get_event_loop()
    
    # Run the synchronous function in a thread pool
    return await loop.run_in_executor(
        None,
        lambda: fetch_trials(
            condition=condition,
            max_studies=max_studies,
            return_status=return_status,
            json_output=json_output,
            output_name=output_name,
            timeout=timeout
        )
    )

if __name__ == "__main__":
    illness="Type-2 Diabetes"
    fetch_trials(illness, max_studies=1,return_status=False ,json_output=True, output_name="diabetes_trials_3")