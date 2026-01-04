import secrets
from flask import Flask
from src.agent_manager import AgentManager
from src.routes.monitoring_routes import monitoring_bp, set_manager_instance

# Agent workflow
from src.routes.workflow_routes import workflow_bp
from src.routes.questionnaire_routes import questionnaire_bp
from src.routes.results_routes import results_bp

# UI
from src.routes.ui_home_routes import home_bp
from src.routes.ui_patient_routes import patient_bp
from src.routes.ui_trials_routes import trials_bp
from src.routes.ui_favorites_routes import favorites_bp
from src.routes.ui_reports_routes import reports_bp
from src.routes.ui_settings_routes import settings_bp

def create_app():
    app = Flask(__name__)
    app.secret_key = secrets.token_hex(16)

    manager = AgentManager()
    set_manager_instance(manager)
    app.config["AGENT_MANAGER"] = manager

    # UI blueprints (no prefix needed if routes are unique)
    app.register_blueprint(home_bp)
    app.register_blueprint(patient_bp)
    app.register_blueprint(trials_bp)
    app.register_blueprint(favorites_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(settings_bp)

    # Agent blueprints (optionnel prefix si tu veux éviter conflits)
    app.register_blueprint(workflow_bp, url_prefix="/workflow")
    app.register_blueprint(questionnaire_bp, url_prefix="/questionnaire")
    app.register_blueprint(results_bp, url_prefix="/results")
    app.register_blueprint(monitoring_bp, url_prefix="/monitoring")

    return app

if __name__ == "__main__":
    create_app().run(debug=True, port=5000)