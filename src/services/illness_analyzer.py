"""
Service for analyzing patient illness descriptions
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
import json
import re

from ..agent_manager import AgentManager, AgentModel, ResponseFormat
from ..response_models import IllnessInfo
from ..config import MISTRAL_AGENT_ID
from ..logger import logger


class IllnessAnalyzer:
    """Analyzes patient descriptions to extract structured illness information"""

    def __init__(self, agent_id: str = MISTRAL_AGENT_ID):
        self.agent_id = agent_id

    async def analyze(self, user_description: str) -> IllnessInfo:
        """
        Analyze patient description and extract structured illness info.

        Always returns a valid IllnessInfo (fills required fields like category).
        """
        logger.info("🏥 Analyzing patient description...")

        user_description = (user_description or "").strip()
        if not user_description:
            return self._fallback_model({"illness_name": "Unknown", "category": "unknown"})

        async with AgentManager(max_retries=3, retry_delay=5.0) as manager:
            manager.create_agent(
                agent_id=self.agent_id,
                name="IllnessTypeAgent",
                model=AgentModel.SMALL.value,
                response_format=ResponseFormat.JSON,
                response_model=IllnessInfo,
            )

            prompt = self._build_analysis_prompt(user_description)

            raw = await manager.chat_with_retry_async(
                agent_name="IllnessTypeAgent",
                message=prompt,
                response_model=IllnessInfo,
            )

            return self._coerce_to_illnessinfo(raw, user_description=user_description)

    # -----------------------------
    # Helpers: type normalization
    # -----------------------------
    def _ensure_list_or_none(self, value: Any) -> Optional[List[str]]:
        """
        Normalize value to Optional[List[str]]:
        - None / "" -> None
        - "lung" -> ["lung"]
        - "a, b" -> ["a", "b"]
        - ["lung"] -> ["lung"]
        """
        if value is None:
            return None
        if isinstance(value, list):
            cleaned = [str(x).strip() for x in value if str(x).strip()]
            return cleaned if cleaned else None
        if isinstance(value, str):
            v = value.strip()
            if not v:
                return None
            if "," in v:
                parts = [s.strip() for s in v.split(",") if s.strip()]
                return parts if parts else None
            return [v]
        s = str(value).strip()
        return [s] if s else None

    def _ensure_list(self, value: Any) -> List[str]:
        """
        Normalize value to List[str] (never None)
        - None -> []
        - "x" -> ["x"]
        - ["x"] -> ["x"]
        """
        if value is None:
            return []
        if isinstance(value, list):
            return [str(x).strip() for x in value if str(x).strip()]
        if isinstance(value, str):
            v = value.strip()
            if not v:
                return []
            if "," in v:
                return [s.strip() for s in v.split(",") if s.strip()]
            return [v]
        s = str(value).strip()
        return [s] if s else []

    def _normalize_types(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fix schema issues to match your IllnessInfo model.
        """
        out = dict(data or {})

        # Required fields
        if not out.get("illness_name"):
            out["illness_name"] = "Unknown"
        if not out.get("category"):
            out["category"] = "unknown"

        # Optional list fields (Optional[List[str]])
        out["anatomical_location"] = self._ensure_list_or_none(out.get("anatomical_location"))
        out["organ_touched"] = self._ensure_list_or_none(out.get("organ_touched"))

        # Always-list fields
        out["affected_systems"] = self._ensure_list(out.get("affected_systems"))
        out["keywords"] = self._ensure_list(out.get("keywords"))

        # Optional scalars
        out.setdefault("type", None)
        out.setdefault("subtype", None)
        out.setdefault("stage", None)
        out.setdefault("severity", None)

        # Optional confidence
        out.setdefault("confidence_score", None)

        return out

    # -----------------------------
    # Robust parsing + fallback
    # -----------------------------
    def _fallback_model(self, partial: Dict[str, Any]) -> IllnessInfo:
        """
        Builds a valid IllnessInfo even if the LLM response is messy or incomplete.
        """
        data = self._normalize_types(partial or {})
        return IllnessInfo(**data)

    def _extract_json_object(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Extract a JSON object from messy text.
        """
        if not text:
            return None

        s = text.strip()

        # direct JSON
        if s.startswith("{") and s.endswith("}"):
            try:
                obj = json.loads(s)
                return obj if isinstance(obj, dict) else None
            except Exception:
                pass

        # find first {...}
        m = re.search(r"\{.*\}", s, flags=re.DOTALL)
        if m:
            block = m.group(0)
            try:
                obj = json.loads(block)
                return obj if isinstance(obj, dict) else None
            except Exception:
                return None

        return None

    def _coerce_to_illnessinfo(self, raw: Any, user_description: str) -> IllnessInfo:
        """
        Convert raw agent response into IllnessInfo reliably.
        """
        # already model
        if isinstance(raw, IllnessInfo):
            try:
                data = raw.model_dump()
            except Exception:
                data = getattr(raw, "__dict__", {}) or {}
            return self._fallback_model(data)

        # dict
        if isinstance(raw, dict):
            data = dict(raw)

            # illness_name may contain JSON
            ill = data.get("illness_name")
            if isinstance(ill, str):
                embedded = self._extract_json_object(ill)
                if embedded:
                    data = embedded

            # any field might contain JSON
            for k, v in list(data.items()):
                if isinstance(v, str):
                    embedded = self._extract_json_object(v)
                    if embedded and "illness_name" in embedded:
                        data = embedded
                        break

            return self._fallback_model(data)

        # string
        if isinstance(raw, str):
            embedded = self._extract_json_object(raw)
            if embedded:
                return self._fallback_model(embedded)

            # plain string -> illness_name
            return self._fallback_model(
                {
                    "illness_name": raw.strip() or "Unknown",
                    "category": "unknown",
                    "keywords": [user_description] if user_description else [],
                }
            )

        # unknown
        return self._fallback_model({"illness_name": "Unknown", "category": "unknown"})

    # -----------------------------
    # Prompt
    # -----------------------------
    def _build_analysis_prompt(self, user_description: str) -> str:
        return f"""
The response MUST be in English.
Return ONLY a JSON object compatible with the IllnessInfo model (no markdown, no extra text).

Patient input: {user_description}

CRITICAL TYPE RULES (MUST FOLLOW):
- anatomical_location MUST be either null OR a JSON array of strings. Example: ["thorax"] or null
- organ_touched MUST be either null OR a JSON array of strings. Example: ["lung"] or null
- affected_systems MUST be a JSON array of strings (can be empty list)
- keywords MUST be a JSON array of strings (can be empty list)
- category is REQUIRED. If unknown, set "unknown".

Rules:
- illness_name: general illness name only (no types, subtypes, stages, variants, or anatomical locations)
- type: specific type or subtype if mentioned, else null
- subtype: specific variant if mentioned, else null
- stage: disease stage if explicitly mentioned, else null
- severity: mild/moderate/severe if mentioned, else null
- confidence_score: optional float between 0 and 1 if you can estimate, else null

Normalization:
- Use canonical singular terms
- Return valid JSON ONLY
""".strip()
