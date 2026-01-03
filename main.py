# main.py
"""
Main Flask application for Clinical Trial Matching
Modular architecture following SOLID principles
"""
import secrets
from flask import Flask

from src.routes.workflow_routes import workflow_bp
from src.routes.questionnaire_routes import questionnaire_bp
from src.routes.results_routes import results_bp
from src.routes.monitoring_routes import monitoring_bp, set_manager_instance
from src.agent_manager import AgentManager


def create_app():
    """Application factory"""
    app = Flask(__name__)
    app.secret_key = secrets.token_hex(16)
    
    # Initialize agent manager with memory and error handling
    manager = AgentManager()
    set_manager_instance(manager)
    
    # Register blueprints
    app.register_blueprint(workflow_bp)
    app.register_blueprint(questionnaire_bp)
    app.register_blueprint(results_bp)
    app.register_blueprint(monitoring_bp)
    
    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=5000)