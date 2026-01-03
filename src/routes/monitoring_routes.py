"""Routes for system monitoring and diagnostics"""
from flask import Blueprint, jsonify
from src.logger import logger


monitoring_bp = Blueprint('monitoring', __name__)

# Global manager instance for monitoring
_manager_instance = None


def set_manager_instance(manager):
    """Set the global manager instance"""
    global _manager_instance
    _manager_instance = manager


@monitoring_bp.route('/system/status', methods=['GET'])
def get_system_status():
    """Get overall system status"""
    if not _manager_instance:
        return jsonify({'error': 'System not initialized'}), 503
    
    try:
        status = _manager_instance.get_system_status()
        return jsonify(status)
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        return jsonify({'error': str(e)}), 500


@monitoring_bp.route('/agent/<agent_name>/context', methods=['GET'])
def get_agent_context(agent_name: str):
    """Get context for specific agent"""
    if not _manager_instance:
        return jsonify({'error': 'System not initialized'}), 503
    
    try:
        context = _manager_instance.get_agent_context(agent_name)
        return jsonify(context)
    except Exception as e:
        logger.error(f"Error getting agent context: {e}")
        return jsonify({'error': str(e)}), 500


@monitoring_bp.route('/memory/export', methods=['GET'])
def export_memory():
    """Export all memories"""
    if not _manager_instance:
        return jsonify({'error': 'System not initialized'}), 503
    
    try:
        memories = _manager_instance.memory.export_memories()
        return memories, 200, {'Content-Type': 'application/json'}
    except Exception as e:
        logger.error(f"Error exporting memory: {e}")
        return jsonify({'error': str(e)}), 500
