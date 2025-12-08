"""Configuration for clinical trials API, Agent and application settings."""
from typing import List

# Clinical Trials API Configuration
CLINICAL_TRIALS_BASE_URL: str = "https://clinicaltrials.gov/api/v2/studies"
"""Base URL to fetch clinical trials data from clinicaltrials.gov API."""

CLINICAL_TRIALS_PAGE_SIZE_LIMIT: int = 100
"""Maximum number of studies to fetch per API request."""

CLINICAL_TRIALS_STATUSES_FILTER: List[str] = [
    "RECRUITING",
    "NOT_YET_RECRUITING",
    "ENROLLING_BY_INVITATION",
    "ACTIVE_NOT_RECRUITING"
]
"""List of clinical trial statuses to filter the search results."""

# API Request Configuration
DEFAULT_PAGE_SIZE: int = 100
"""Default number of studies to fetch per request."""

REQUEST_TIMEOUT: int = 30
"""Default timeout for API requests in seconds."""



