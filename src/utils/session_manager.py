# src/utils/session_manager.py
"""
Session management utilities for file-based storage
"""
import json
import os
import tempfile
import secrets
from typing import Dict, Any, Optional
from flask import session


class SessionManager:
    """Manage session data stored in temporary files"""

    @staticmethod
    def get_temp_dir() -> str:
        """Get temporary directory path"""
        return tempfile.gettempdir()

    @staticmethod
    def initialize_session() -> str:
        """
        Initialize a new session with unique ID

        Returns:
            session_id: Unique session identifier
        """
        session_id = session.get("session_id") or secrets.token_hex(16)
        session["session_id"] = session_id
        session.modified = True
        return session_id

    @staticmethod
    def get_data_file_path(session_id: str) -> str:
        """
        Get file path for session data
        """
        temp_dir = SessionManager.get_temp_dir()
        return os.path.join(temp_dir, f"trials_{session_id}.json")

    @staticmethod
    def save_data(data: Dict[str, Any]) -> None:
        """
        Save session data to file
        """
        data_file = session.get("data_file")

        # fallback: reconstruire data_file si manquant mais session_id présent
        if not data_file and session.get("session_id"):
            candidate = SessionManager.get_data_file_path(session["session_id"])
            if os.path.exists(candidate):
                data_file = candidate
                session["data_file"] = data_file
                session.modified = True

        if data_file:
            with open(data_file, "w", encoding="utf-8") as f:
                json.dump(data, f)

    @staticmethod
    def load_data() -> Optional[Dict[str, Any]]:
        """
        Load session data from file

        Returns:
            Dictionary containing session data, or None if not found
        """
        data_file = session.get("data_file")

        # ✅ fallback: si data_file absent mais session_id présent -> on reconstruit
        if not data_file and session.get("session_id"):
            candidate = SessionManager.get_data_file_path(session["session_id"])
            if os.path.exists(candidate):
                data_file = candidate
                session["data_file"] = data_file
                session.modified = True

        if not data_file or not os.path.exists(data_file):
            return None

        with open(data_file, "r", encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def create_data_file(session_id: str, initial_data: Dict[str, Any]) -> str:
        """
        Create new data file with initial content

        Returns:
            Path to created data file
        """
        data_file = SessionManager.get_data_file_path(session_id)
        with open(data_file, "w", encoding="utf-8") as f:
            json.dump(initial_data, f)

        session["data_file"] = data_file
        session.modified = True
        return data_file

    @staticmethod
    def cleanup_session() -> None:
        """Clean up session data file"""
        data_file = session.get("data_file")
        if data_file and os.path.exists(data_file):
            try:
                os.remove(data_file)
            except Exception:
                pass  # Ignore cleanup errors
                