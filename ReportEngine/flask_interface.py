"""
Report Engine Flask Interface
Provides HTTP API for report generation
"""

import os
import json
import threading
import time
from datetime import datetime
from flask import Blueprint, request, jsonify, Response
from typing import Dict, Any
from loguru import logger
from .agent import ReportAgent, create_agent
from .utils.config import settings


# Create Blueprint
report_bp = Blueprint('report_engine', __name__)

# Global variables
report_agent = None
current_task = None
task_lock = threading.Lock()


def initialize_report_engine():
    """Initialize Report Engine"""
    global report_agent
    try:
        report_agent = create_agent()
        logger.info("Report Engine successfully initialized")
        return True
    except Exception as e:
        logger.exception(f"Report Engine initialization failed: {str(e)}")
        return False


class ReportTask:
    """Report Generation Task"""

    def __init__(self, query: str, task_id: str, custom_template: str = ""):
        self.task_id = task_id
        self.query = query
        self.custom_template = custom_template
        self.status = "pending"  # pending, running, completed, error
        self.progress = 0
        self.result = None
        self.error_message = ""
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.html_content = ""

    def update_status(self, status: str, progress: int = None, error_message: str = ""):
        """Update task status"""
        self.status = status
        if progress is not None:
            self.progress = progress
        if error_message:
            self.error_message = error_message
        self.updated_at = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format"""
        return {
            'task_id': self.task_id,
            'query': self.query,
            'status': self.status,
            'progress': self.progress,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'has_result': bool(self.html_content)
        }


def check_engines_ready() -> Dict[str, Any]:
    """Check if all three sub-engines have new files"""
    directories = {
        'insight': 'insight_engine_streamlit_reports',
        'media': 'media_engine_streamlit_reports',
        'query': 'query_engine_streamlit_reports'
    }

    forum_log_path = 'logs/forum.log'

    if not report_agent:
        return {
            'ready': False,
            'error': 'Report Engine not initialized'
        }

    return report_agent.check_input_files(
        directories['insight'],
        directories['media'],
        directories['query'],
        forum_log_path
    )


def run_report_generation(task: ReportTask, query: str, custom_template: str = ""):
    """Run report generation in background thread"""
    global current_task

    try:
        task.update_status("running", 10)

        # Check input files
        check_result = check_engines_ready()
        if not check_result['ready']:
            task.update_status("error", 0, f"Input files not ready: {check_result.get('missing_files', [])}")
            return

        task.update_status("running", 30)

        # Load input files
        content = report_agent.load_input_files(check_result['latest_files'])

        task.update_status("running", 50)

        # Generate report
        html_report = report_agent.generate_report(
            query=query,
            reports=content['reports'],
            forum_logs=content['forum_logs'],
            custom_template=custom_template,
            save_report=True
        )

        task.update_status("running", 90)

        # Save result
        task.html_content = html_report
        task.update_status("completed", 100)

    except Exception as e:
        task.update_status("error", 0, str(e))
        # Do NOT clear task on error, so UI can fetch the error message
        logger.error(f"Task {task.task_id} failed: {str(e)}")


@report_bp.route('/status', methods=['GET'])
def get_status():
    """Get Report Engine status"""
    try:
        engines_status = check_engines_ready()

        return jsonify({
            'success': True,
            'initialized': report_agent is not None,
            'engines_ready': engines_status['ready'],
            'files_found': engines_status.get('files_found', []),
            'missing_files': engines_status.get('missing_files', []),
            'current_task': current_task.to_dict() if current_task else None
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@report_bp.route('/generate', methods=['POST'])
def generate_report():
    """Start report generation"""
    global current_task

    try:
        # Check if task is running
        with task_lock:
            if current_task and current_task.status == "running":
                return jsonify({
                    'success': False,
                    'error': 'A report generation task is already running',
                    'current_task': current_task.to_dict()
                }), 400

            # Clean up completed task
            if current_task and current_task.status in ["completed", "error"]:
                current_task = None

        # Get request parameters
        data = request.get_json() or {}
        query = data.get('query', 'Intelligent Public Opinion Analysis Report')
        custom_template = data.get('custom_template', '')

        # Clear log file
        clear_report_log()

        # Check if Report Engine is initialized
        if not report_agent:
            return jsonify({
                'success': False,
                'error': 'Report Engine not initialized'
            }), 500

        # Check if input files are ready
        engines_status = check_engines_ready()
        if not engines_status['ready']:
            return jsonify({
                'success': False,
                'error': 'Input files not ready',
                'missing_files': engines_status.get('missing_files', [])
            }), 400

        # Create new task
        task_id = f"report_{int(time.time())}"
        task = ReportTask(query, task_id, custom_template)

        with task_lock:
            current_task = task

        # Run report generation in background thread
        thread = threading.Thread(
            target=run_report_generation,
            args=(task, query, custom_template),
            daemon=True
        )
        thread.start()

        return jsonify({
            'success': True,
            'task_id': task_id,
            'message': 'Report generation started',
            'task': task.to_dict()
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@report_bp.route('/progress/<task_id>', methods=['GET'])
def get_progress(task_id: str):
    """Get report generation progress"""
    try:
        # If the task no longer exists (e.g., after cleanup), assume it's completed
        if not current_task or current_task.task_id != task_id:
            return jsonify({
                'success': True,
                'task': {
                    'task_id': task_id,
                    'status': 'completed',
                    'progress': 100,
                    'error_message': '',
                    'has_result': True,
                    'html_content': None
                }
            })
        # Return current task state
        response = {'success': True, 'task': current_task.to_dict()}
        # If completed, attach the generated HTML so frontend can display it directly
        if current_task.status == 'completed':
            response['task']['html_content'] = current_task.html_content
        return jsonify(response)
    except Exception as e:
        logger.exception(f"Failed to get report generation progress: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@report_bp.route('/result/<task_id>', methods=['GET'])
def get_result(task_id: str):
    """Get report generation result"""
    try:
        if not current_task or current_task.task_id != task_id:
            return jsonify({
                'success': False,
                'error': 'Task does not exist'
            }), 404

        if current_task.status != "completed":
            return jsonify({
                'success': False,
                'error': 'Report not yet completed',
                'task': current_task.to_dict()
            }), 400

        return Response(
            current_task.html_content,
            mimetype='text/html'
        )

    except Exception as e:
        logger.exception(f"Failed to get report generation result: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@report_bp.route('/result/<task_id>/json', methods=['GET'])
def get_result_json(task_id: str):
    """Get report generation result (JSON format)"""
    try:
        if not current_task or current_task.task_id != task_id:
            return jsonify({
                'success': False,
                'error': 'Task does not exist'
            }), 404

        if current_task.status != "completed":
            return jsonify({
                'success': False,
                'error': 'Report not yet completed',
                'task': current_task.to_dict()
            }), 400

        return jsonify({
            'success': True,
            'task': current_task.to_dict(),
            'html_content': current_task.html_content
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@report_bp.route('/cancel/<task_id>', methods=['POST'])
def cancel_task(task_id: str):
    """Cancel report generation task"""
    global current_task

    try:
        with task_lock:
            if current_task and current_task.task_id == task_id:
                if current_task.status == "running":
                    current_task.update_status("cancelled", 0, "User cancelled task")
                current_task = None

                return jsonify({
                    'success': True,
                    'message': 'Task cancelled'
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Task does not exist or cannot be cancelled'
                }), 404

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@report_bp.route('/templates', methods=['GET'])
def get_templates():
    """Get available templates list"""
    try:
        if not report_agent:
            return jsonify({
                'success': False,
                'error': 'Report Engine not initialized'
            }), 500

        template_dir = settings.TEMPLATE_DIR
        templates = []

        if os.path.exists(template_dir):
            for filename in os.listdir(template_dir):
                if filename.endswith('.md'):
                    template_path = os.path.join(template_dir, filename)
                    try:
                        with open(template_path, 'r', encoding='utf-8') as f:
                            content = f.read()

                        templates.append({
                            'name': filename.replace('.md', ''),
                            'filename': filename,
                            'description': content.split('\n')[0] if content else 'No description',
                            'size': len(content)
                        })
                    except Exception as e:
                        logger.exception(f"Failed to read template {filename}: {str(e)}")

        return jsonify({
            'success': True,
            'templates': templates,
            'template_dir': template_dir
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# Error handling
@report_bp.errorhandler(404)
def not_found(error):
    return jsonify({
        'success': False,
        'error': 'API endpoint does not exist'
    }), 404


@report_bp.errorhandler(500)
def internal_error(error):
    return jsonify({
        'success': False,
        'error': 'Internal server error'
    }), 500


def clear_report_log():
    """Clear report.log file"""
    try:
        log_file = settings.LOG_FILE
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write('')
        logger.info(f"Cleared log file: {log_file}")
    except Exception as e:
        logger.exception(f"Failed to clear log file: {str(e)}")


@report_bp.route('/log', methods=['GET'])
def get_report_log():
    """Get report.log content"""
    try:
        log_file = settings.LOG_FILE
        
        if not os.path.exists(log_file):
            return jsonify({
                'success': True,
                'log_lines': []
            })
        
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Clean up trailing newlines
        log_lines = [line.rstrip('\n\r') for line in lines if line.strip()]
        
        return jsonify({
            'success': True,
            'log_lines': log_lines
        })
        
    except Exception as e:
        logger.exception(f"Failed to read log: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Failed to read log: {str(e)}'
        }), 500


@report_bp.route('/log/clear', methods=['POST'])
def clear_log():
    """Manually clear log"""
    try:
        clear_report_log()
        return jsonify({
            'success': True,
            'message': 'Log cleared'
        })
    except Exception as e:
        logger.exception(f"Failed to clear log: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Failed to clear log: {str(e)}'
        }), 500
