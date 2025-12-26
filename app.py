"""
Flask Main App - Unify management of three Streamlit apps
"""

import os
import sys
import subprocess
import time
import threading
from datetime import datetime
from queue import Queue
from flask import Flask, render_template, request, jsonify, Response
from flask_socketio import SocketIO, emit
import atexit
import requests
from loguru import logger
import importlib
from pathlib import Path

# Import ReportEngine
try:
    logger.info(f"Python Executable: {sys.executable}")
    from ReportEngine.flask_interface import report_bp, initialize_report_engine
    REPORT_ENGINE_AVAILABLE = True
except ImportError as e:
    logger.error(f"ReportEngine import failed: {e}")
    REPORT_ENGINE_AVAILABLE = False

app = Flask(__name__) # initializes the Flask app.
app.config['SECRET_KEY'] = 'Dedicated-to-creating-a-concise-and-versatile-public-opinion-analysis-platform' # random key
socketio = SocketIO(app, cors_allowed_origins="*") # initializes the SocketIO app.

# Register ReportEngine Blueprint
if REPORT_ENGINE_AVAILABLE:
    # 'report_engine' is NOT part of the URL
    app.register_blueprint(report_bp, url_prefix='/api/report') # registers the ReportEngine blueprint with the Flask app.
    logger.info("ReportEngine interface registered")
else:
    logger.info("ReportEngine unavailable, skipping interface registration")

# Set UTF-8 encoding environment (Tell the operating system that this process now has an environment variable called PYTHONIOENCODING)
os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['PYTHONUTF8'] = '1'

# Create log directory if doesn't already exist
LOG_DIR = Path('logs')
LOG_DIR.mkdir(exist_ok=True)

# coming from Configuration file config.py
CONFIG_MODULE_NAME = 'config'
CONFIG_FILE_PATH = Path(__file__).resolve().parent / 'config.py'
CONFIG_KEYS = [
    'DB_DIALECT',
    'DB_HOST',
    'DB_PORT',
    'DB_USER',
    'DB_PASSWORD',
    'DB_NAME',
    'DB_CHARSET',
    'INSIGHT_ENGINE_API_KEY',
    'INSIGHT_ENGINE_BASE_URL',
    'INSIGHT_ENGINE_MODEL_NAME',
    'MEDIA_ENGINE_API_KEY',
    'MEDIA_ENGINE_BASE_URL',
    'MEDIA_ENGINE_MODEL_NAME',
    'QUERY_ENGINE_API_KEY',
    'QUERY_ENGINE_BASE_URL',
    'QUERY_ENGINE_MODEL_NAME',
    'REPORT_ENGINE_API_KEY',
    'REPORT_ENGINE_BASE_URL',
    'REPORT_ENGINE_MODEL_NAME',
    'FORUM_HOST_API_KEY',
    'FORUM_HOST_BASE_URL',
    'FORUM_HOST_MODEL_NAME',
    'KEYWORD_OPTIMIZER_API_KEY',
    'KEYWORD_OPTIMIZER_BASE_URL',
    'KEYWORD_OPTIMIZER_MODEL_NAME',
    'TAVILY_API_KEY',
    'BOCHA_WEB_SEARCH_API_KEY'
]


def _load_config_module():
    """Load or reload the config module to ensure latest values are available."""
    importlib.invalidate_caches()
    module = sys.modules.get(CONFIG_MODULE_NAME)
    try:
        if module is None:
            module = importlib.import_module(CONFIG_MODULE_NAME)
        else:
            module = importlib.reload(module)
    except ModuleNotFoundError:
        return None
    return module


def read_config_values():
    """Return the current configuration values that are exposed to the frontend."""
    try:
        # Reload config module to get latest Settings instance
        importlib.invalidate_caches()
        if CONFIG_MODULE_NAME in sys.modules:
            importlib.reload(sys.modules[CONFIG_MODULE_NAME])
        else:
            importlib.import_module(CONFIG_MODULE_NAME)
        
        # Get settings instance from config module
        config_module = sys.modules[CONFIG_MODULE_NAME]
        if not hasattr(config_module, 'settings'):
            logger.error("settings instance not found in config module")
            return {}
        
        settings = config_module.settings
        values = {}
        for key in CONFIG_KEYS:
            # Read value from Pydantic Settings instance
            value = getattr(settings, key, None)
            # Convert to string for uniform handling on the frontend.
            if value is None:
                values[key] = ''
            else:
                values[key] = str(value)
        return values
    except Exception as exc:
        logger.exception(f"Failed to read config: {exc}")
        return {}


def _serialize_config_value(value):
    """Serialize Python values back to a config.py assignment-friendly string."""
    if isinstance(value, bool):
        return 'True' if value else 'False'
    if isinstance(value, (int, float)):
        return str(value)
    if value is None:
        return 'None'

    value_str = str(value)
    escaped = value_str.replace('\\', '\\\\').replace('"', '\\"')
    return f'"{escaped}"'


def write_config_values(updates):
    """Persist configuration updates to .env file (Pydantic Settings source)."""
    from pathlib import Path
    
    # Determine .env file path (consistent with config.py logic)
    project_root = Path(__file__).resolve().parent
    cwd_env = Path.cwd() / ".env"
    env_file_path = cwd_env if cwd_env.exists() else (project_root / ".env")
    
    # Read existing .env file content
    env_lines = []
    env_key_indices = {}  # Record index of each key in file
    if env_file_path.exists():
        env_lines = env_file_path.read_text(encoding='utf-8').splitlines()
        # Extract existing keys and their indices
        for i, line in enumerate(env_lines):
            line_stripped = line.strip()
            if line_stripped and not line_stripped.startswith('#'):
                if '=' in line_stripped:
                    key = line_stripped.split('=')[0].strip()
                    env_key_indices[key] = i
    
    # Update or add configuration items
    for key, raw_value in updates.items():
        # Format value for .env file (no quotes needed unless string with spaces)
        if raw_value is None or raw_value == '':
            env_value = ''
        elif isinstance(raw_value, (int, float)):
            env_value = str(raw_value)
        elif isinstance(raw_value, bool):
            env_value = 'True' if raw_value else 'False'
        else:
            value_str = str(raw_value)
            # Quotes needed if containing spaces or special characters
            if ' ' in value_str or '\n' in value_str or '#' in value_str:
                escaped = value_str.replace('\\', '\\\\').replace('"', '\\"')
                env_value = f'"{escaped}"'
            else:
                env_value = value_str
        
        # Update or add configuration items
        if key in env_key_indices:
            # Update existing line
            env_lines[env_key_indices[key]] = f'{key}={env_value}'
        else:
            # Add new line to end of file
            env_lines.append(f'{key}={env_value}')
    
    # Write to .env file
    env_file_path.parent.mkdir(parents=True, exist_ok=True)
    env_file_path.write_text('\n'.join(env_lines) + '\n', encoding='utf-8')
    
    # Reload config module (this re-reads .env file and creates new Settings instance)
    _load_config_module()


system_state_lock = threading.Lock()
system_state = {
    'started': False,
    'starting': False
}


def _set_system_state(*, started=None, starting=None):
    """Safely update the cached system state flags."""
    with system_state_lock:
        if started is not None:
            system_state['started'] = started
        if starting is not None:
            system_state['starting'] = starting


def _get_system_state():
    """Return a shallow copy of the system state flags."""
    with system_state_lock:
        return system_state.copy()


def _prepare_system_start():
    """Mark the system as starting if it is not already running or starting."""
    with system_state_lock:
        if system_state['started']:
            return False, 'System already started'
        if system_state['starting']:
            return False, 'System is starting'
        system_state['starting'] = True
        return True, None


def initialize_system_components():
    """Start all dependent components (Streamlit sub-apps, ForumEngine, ReportEngine)."""
    logs = []
    errors = []

    try:
        stop_forum_engine()
        logs.append("Stopped ForumEngine monitor to avoid file conflicts")
    except Exception as exc:  # pragma: no cover - safe catch
        message = f"Exception occurred while stopping ForumEngine: {exc}"
        logs.append(message)
        logger.exception(message)

    processes['forum']['status'] = 'stopped'

    for app_name, script_path in STREAMLIT_SCRIPTS.items():
        logs.append(f"Checking file: {script_path}")
        if os.path.exists(script_path):
            success, message = start_streamlit_app(app_name, script_path, processes[app_name]['port'])
            logs.append(f"{app_name}: {message}")
            if success:
                startup_success, startup_message = wait_for_app_startup(app_name, 30)
                logs.append(f"{app_name} Startup check: {startup_message}")
                if not startup_success:
                    errors.append(f"{app_name} Startup failed: {startup_message}")
            else:
                errors.append(f"{app_name} Startup failed: {message}")
        else:
            msg = f"File not found: {script_path}"
            logs.append(f"Error: {msg}")
            errors.append(f"{app_name}: {msg}")

    forum_started = False
    try:
        start_forum_engine()
        processes['forum']['status'] = 'running'
        logs.append("ForumEngine startup complete")
        forum_started = True
    except Exception as exc:  # pragma: no cover - fallback catch
        error_msg = f"ForumEngine startup failed: {exc}"
        logs.append(error_msg)
        errors.append(error_msg)

    if REPORT_ENGINE_AVAILABLE:
        try:
            if initialize_report_engine():
                logs.append("ReportEngine initialized successfully")
            else:
                msg = "ReportEngine initialization failed"
                logs.append(msg)
                errors.append(msg)
        except Exception as exc:  # pragma: no cover
            msg = f"ReportEngine initialization exception: {exc}"
            logs.append(msg)
            errors.append(msg)

    if errors:
        cleanup_processes()
        processes['forum']['status'] = 'stopped'
        if forum_started:
            try:
                stop_forum_engine()
            except Exception:  # pragma: no cover
                logger.exception("Failed to stop ForumEngine")
        return False, logs, errors

    return True, logs, []

# Initialize ForumEngine forum.log file
def init_forum_log():
    """Initialize forum.log file"""
    try:
        forum_log_file = LOG_DIR / "forum.log" # / is to join path here inside log_dir we will create forum.log file 
        # Create if not exists and write start, otherwise clear and write start

        if not forum_log_file.exists():
            # with is for auto operation (file/db) open and close
            with open(forum_log_file, 'w', encoding='utf-8') as f: # w is for write
                start_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                f.write(f"=== ForumEngine System Initialization - {start_time} ===\n") # f"" is just like `${}` in js
            logger.info(f"ForumEngine: forum.log initialized")
        else:
            with open(forum_log_file, 'w', encoding='utf-8') as f:
                start_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                f.write(f"=== ForumEngine System Initialization - {start_time} ===\n")
            logger.info(f"ForumEngine: forum.log initialized")
    except Exception as e:
        logger.exception(f"ForumEngine: Failed to initialize forum.log: {e}")

# Initialize forum.log
init_forum_log()

# Start ForumEngine Intelligent Monitoring
def start_forum_engine():
    """Start ForumEngine Forum"""
    try:
        from ForumEngine.monitor import start_forum_monitoring
        logger.info("ForumEngine: Starting forum...")
        success = start_forum_monitoring()
        if not success:
            logger.info("ForumEngine: Forum start failed")
    except Exception as e:
        logger.exception(f"ForumEngine: Failed to start forum: {e}")

# Stop ForumEngine Intelligent Monitoring
def stop_forum_engine():
    """Stop ForumEngine Forum"""
    try:
        from ForumEngine.monitor import stop_forum_monitoring
        logger.info("ForumEngine: Stopping forum...")
        stop_forum_monitoring()
        logger.info("ForumEngine: Forum stopped")
    except Exception as e:
        logger.exception(f"ForumEngine: Failed to stop forum: {e}")

def parse_forum_log_line(line):
    """Parse forum.log line content, extract dialogue info"""
    import re
    
    # Match format: [Time] [Source] Content
    pattern = r'\[(\d{2}:\d{2}:\d{2})\]\s*\[([A-Z]+)\]\s*(.*)'
    match = re.match(pattern, line)
    
    if match:
        timestamp, source, content = match.groups()
        
        # Filter out system messages and empty content
        if source == 'SYSTEM' or not content.strip():
            return None
        
        # Only process messages from the three Engines
        if source not in ['QUERY', 'INSIGHT', 'MEDIA']:
            return None
        
        # Determine message type and sender based on source
        message_type = 'agent'
        sender = f'{source} Engine'
        
        return {
            'type': message_type,
            'sender': sender,
            'content': content.strip(),
            'timestamp': timestamp,
            'source': source
        }
    
    return None

# Forum Log Listener
def monitor_forum_log():
    """Monitor forum.log changes and push to frontend"""
    import time
    from pathlib import Path
    
    forum_log_file = LOG_DIR / "forum.log"
    last_position = 0
    processed_lines = set()  # Track processed lines to avoid duplicates
    
    # If file exists, get initial position
    if forum_log_file.exists():
        with open(forum_log_file, 'r', encoding='utf-8', errors='ignore') as f:
            # Read all existing lines on init to avoid duplicates
            existing_lines = f.readlines()
            for line in existing_lines:
                line_hash = hash(line.strip())
                processed_lines.add(line_hash)
            last_position = f.tell()
    
    while True:
        try:
            if forum_log_file.exists():
                with open(forum_log_file, 'r', encoding='utf-8', errors='ignore') as f:
                    f.seek(last_position)
                    new_lines = f.readlines()
                    
                    if new_lines:
                        for line in new_lines:
                            line = line.rstrip('\n\r')
                            if line.strip():
                                line_hash = hash(line.strip())
                                
                                # Avoid duplicate processing of the same line
                                if line_hash in processed_lines:
                                    continue
                                
                                processed_lines.add(line_hash)
                                
                                # Parse log line and send forum message
                                parsed_message = parse_forum_log_line(line)
                                if parsed_message:
                                    socketio.emit('forum_message', parsed_message)
                                
                                # Only send console message when forum is displayed in console
                                timestamp = datetime.now().strftime('%H:%M:%S')
                                formatted_line = f"[{timestamp}] {line}"
                                socketio.emit('console_output', {
                                    'app': 'forum',
                                    'line': formatted_line
                                })
                        
                        last_position = f.tell()
                        
                        # Cleanup processed_lines set to avoid memory leak (keep last 1000 line hashes)
                        if len(processed_lines) > 1000:
                            processed_lines.clear()
            
            time.sleep(1)  # Check every second
        except Exception as e:
            logger.error(f"Forum log monitor error: {e}")
            time.sleep(5)

# Start Forum log monitor thread (Run monitor_forum_log() in the background, at the same time as the rest of the program.)
forum_monitor_thread = threading.Thread(target=monitor_forum_log, daemon=True)
forum_monitor_thread.start()

# Global variable to store process info (it run STREAMLIT_SCRIPTS this on different ports)
processes = {
    'insight': {'process': None, 'port': 8501, 'status': 'stopped', 'output': [], 'log_file': None},
    'media': {'process': None, 'port': 8502, 'status': 'stopped', 'output': [], 'log_file': None},
    'query': {'process': None, 'port': 8503, 'status': 'stopped', 'output': [], 'log_file': None},
    'forum': {'process': None, 'port': None, 'status': 'stopped', 'output': [], 'log_file': None}  # marked as running after start
}

STREAMLIT_SCRIPTS = {
    'insight': 'SingleEngineApp/insight_engine_streamlit_app.py', # python package used for frontend design
    'media': 'SingleEngineApp/media_engine_streamlit_app.py', # python package used for frontend design
    'query': 'SingleEngineApp/query_engine_streamlit_app.py' # python package used for frontend design
}

# Output queues (provide a way to store output from different processes)
output_queues = {
    'insight': Queue(),
    'media': Queue(),
    'query': Queue(),
    'forum': Queue()
}

def write_log_to_file(app_name, line):
    """Write log to file"""
    try:
        log_file_path = LOG_DIR / f"{app_name}.log"
        with open(log_file_path, 'a', encoding='utf-8') as f:
            f.write(line + '\n')
            f.flush()
    except Exception as e:
        logger.error(f"Error writing log for {app_name}: {e}")

def read_log_from_file(app_name, tail_lines=None):
    """Read log from file"""
    try:
        log_file_path = LOG_DIR / f"{app_name}.log"
        if not log_file_path.exists():
            return []
        
        with open(log_file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            lines = [line.rstrip('\n\r') for line in lines if line.strip()]
            
            if tail_lines:
                return lines[-tail_lines:]
            return lines
    except Exception as e:
        logger.exception(f"Error reading log for {app_name}: {e}")
        return []

def read_process_output(process, app_name):
    """Read process output and write to file"""
    import select
    import sys
    
    while True:
        try:
            if process.poll() is not None:
                # Process ended, read remaining output
                remaining_output = process.stdout.read()
                if remaining_output:
                    lines = remaining_output.decode('utf-8', errors='replace').split('\n')
                    for line in lines:
                        line = line.strip()
                        if line:
                            timestamp = datetime.now().strftime('%H:%M:%S')
                            formatted_line = f"[{timestamp}] {line}"
                            write_log_to_file(app_name, formatted_line)
                            socketio.emit('console_output', {
                                'app': app_name,
                                'line': formatted_line
                            })
                break
            
            # Use non-blocking read
            if sys.platform == 'win32':
                # Use different method on Windows
                output = process.stdout.readline()
                if output:
                    line = output.decode('utf-8', errors='replace').strip()
                    if line:
                        timestamp = datetime.now().strftime('%H:%M:%S')
                        formatted_line = f"[{timestamp}] {line}"
                        
                        # Write to log file
                        write_log_to_file(app_name, formatted_line)
                        
                        # Send to frontend
                        socketio.emit('console_output', {
                            'app': app_name,
                            'line': formatted_line
                        })
                else:
                    # Sleep briefly when no output
                    time.sleep(0.1)
            else:
                # Use select on Unix systems
                ready, _, _ = select.select([process.stdout], [], [], 0.1)
                if ready:
                    output = process.stdout.readline()
                    if output:
                        line = output.decode('utf-8', errors='replace').strip()
                        if line:
                            timestamp = datetime.now().strftime('%H:%M:%S')
                            formatted_line = f"[{timestamp}] {line}"
                            
                            # Write to log file
                            write_log_to_file(app_name, formatted_line)
                            
                            # Send to frontend
                            socketio.emit('console_output', {
                                'app': app_name,
                                'line': formatted_line
                            })
                            
        except Exception as e:
            logger.exception(f"Error reading output for {app_name}: {e}")
            write_log_to_file(app_name, f"[{datetime.now().strftime('%H:%M:%S')}] {e}")
            break

def start_streamlit_app(app_name, script_path, port):
    """Start Streamlit application"""
    try:
        if processes[app_name]['process'] is not None:
            return False, "Application already running"
        
        # Check if file exists
        if not os.path.exists(script_path):
            return False, f"File does not exist: {script_path}"
        
        # Clear previous log file
        log_file_path = LOG_DIR / f"{app_name}.log"
        if log_file_path.exists():
            log_file_path.unlink()
        
        # Create startup log
        start_msg = f"[{datetime.now().strftime('%H:%M:%S')}] Starting {app_name} application..."
        write_log_to_file(app_name, start_msg)
        
        cmd = [
            sys.executable, '-m', 'streamlit', 'run',
            script_path,
            '--server.port', str(port),
            '--server.headless', 'true',
            '--browser.gatherUsageStats', 'false',
            # '--logger.level', 'debug',  # Increase log verbosity
            '--logger.level', 'info',
            '--server.enableCORS', 'false'
        ]
        
        # Set env vars to ensure UTF-8 and reduce buffering
        env = os.environ.copy()
        env.update({
            'PYTHONIOENCODING': 'utf-8',
            'PYTHONUTF8': '1',
            'LANG': 'en_US.UTF-8',
            'LC_ALL': 'en_US.UTF-8',
            'PYTHONUNBUFFERED': '1',  # Disable Python buffering
            'STREAMLIT_BROWSER_GATHER_USAGE_STATS': 'false'
        })
        
        # Use current working directory instead of script directory
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=0,  # No buffering
            universal_newlines=False,
            cwd=os.getcwd(),
            env=env,
            encoding=None,  # Handle encoding manually
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
        )
        
        processes[app_name]['process'] = process
        processes[app_name]['status'] = 'starting'
        processes[app_name]['output'] = []
        
        # Start output reading thread
        output_thread = threading.Thread(
            target=read_process_output,
            args=(process, app_name),
            daemon=True
        )
        output_thread.start()
        
        return True, f"{app_name} Application starting..."
        
    except Exception as e:
        error_msg = f"Start failed: {str(e)}"
        write_log_to_file(app_name, f"[{datetime.now().strftime('%H:%M:%S')}] {error_msg}")
        return False, error_msg

def stop_streamlit_app(app_name):
    """Stop Streamlit application"""
    try:
        if processes[app_name]['process'] is None:
            return False, "Application not running"
        
        process = processes[app_name]['process']
        process.terminate()
        
        # Wait for process to end
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        
        processes[app_name]['process'] = None
        processes[app_name]['status'] = 'stopped'
        
        return True, f"{app_name} Application stopped"
        
    except Exception as e:
        return False, f"Stop failed: {str(e)}"

def check_app_status():
    """Check application status"""
    for app_name, info in processes.items(): # processes key:value => app_name:info
        if info['process'] is not None:
            if info['process'].poll() is None: # check if process is running
                # Process still running, check if port is accessible
                try:
                    response = requests.get(f"http://localhost:{info['port']}", timeout=2)
                    if response.status_code == 200:
                        info['status'] = 'running'
                    else:
                        info['status'] = 'starting'
                except requests.exceptions.RequestException:
                    info['status'] = 'starting'
                except Exception:
                    info['status'] = 'starting'
            else:
                # Process ended
                info['process'] = None
                info['status'] = 'stopped'

def wait_for_app_startup(app_name, max_wait_time=30):
    """Wait for application startup to complete"""
    import time
    start_time = time.time()
    while time.time() - start_time < max_wait_time:
        info = processes[app_name]
        if info['process'] is None:
            return False, "Process stopped"
        
        if info['process'].poll() is not None:
            return False, "Process start failed"
        
        try:
            response = requests.get(f"http://localhost:{info['port']}", timeout=2)
            if response.status_code == 200:
                info['status'] = 'running'
                return True, "Startup success"
        except:
            pass
        
        time.sleep(1)
    
    return False, "Startup timeout"

# When the program exits (normally or unexpectedly), everything is shut down cleanly.
def cleanup_processes():
    """Cleanup all processes"""
    for app_name in STREAMLIT_SCRIPTS:
        stop_streamlit_app(app_name) # function to terminate the STREAMLIT_SCRIPTS

    processes['forum']['status'] = 'stopped' # only because others are covered in STREAMLIT_SCRIPTS
    try:
        stop_forum_engine()
    except Exception:  # pragma: no cover
        logger.exception("Failed to stop ForumEngine")
    _set_system_state(started=False, starting=False)

# When Python is about to exit, run this function.
atexit.register(cleanup_processes)

@app.route('/')
def index():
    """Home Page"""
    return render_template('index.html')

@app.route('/api/status')
def get_status():
    """Get all application statuses"""
    check_app_status()
    return jsonify({
        app_name: {
            'status': info['status'],
            'port': info['port'],
            'output_lines': len(info['output'])
        }
        for app_name, info in processes.items() # loop through all processes key:value => app_name:info
    })

@app.route('/api/start/<app_name>')
def start_app(app_name):
    """Start specified application"""
    if app_name not in processes: # check if app_name is in processes
        return jsonify({'success': False, 'message': 'Unknown application'})

    if app_name == 'forum': # remaining app_name check for forum only since its not STREAMLIT_SCRIPTS app
        try:
            start_forum_engine()
            processes['forum']['status'] = 'running'
            return jsonify({'success': True, 'message': 'ForumEngine started'})
        except Exception as exc:  # pragma: no cover
            logger.exception("Failed to manually start ForumEngine")
            return jsonify({'success': False, 'message': f'ForumEngine start failed: {exc}'})

    script_path = STREAMLIT_SCRIPTS.get(app_name)
    if not script_path:
        return jsonify({'success': False, 'message': 'App does not support start operation'})

    success, message = start_streamlit_app( # start_streamlit_app is python package which makes frontend easy to build
        app_name,
        script_path,
        processes[app_name]['port']
    )

    if success:
        # Wait for application startup
        startup_success, startup_message = wait_for_app_startup(app_name, 15)
        if not startup_success:
            message += f" but startup check failed: {startup_message}"
    
    return jsonify({'success': success, 'message': message})

@app.route('/api/stop/<app_name>')
def stop_app(app_name):
    """Stop specified application"""
    if app_name not in processes:
        return jsonify({'success': False, 'message': 'Unknown application'})

    if app_name == 'forum':
        try:
            stop_forum_engine()
            processes['forum']['status'] = 'stopped'
            return jsonify({'success': True, 'message': 'ForumEngine stopped'})
        except Exception as exc:  # pragma: no cover
            logger.exception("Failed to manually stop ForumEngine")
            return jsonify({'success': False, 'message': f'ForumEngine stop failed: {exc}'})

    success, message = stop_streamlit_app(app_name)
    return jsonify({'success': success, 'message': message})

@app.route('/api/output/<app_name>')
def get_output(app_name):
    """Get application output"""
    if app_name not in processes:
        return jsonify({'success': False, 'message': 'Unknown application'})
    
    # Special handling for Forum Engine
    if app_name == 'forum':
        try:
            forum_log_content = read_log_from_file('forum')
            return jsonify({
                'success': True,
                'output': forum_log_content,
                'total_lines': len(forum_log_content)
            })
        except Exception as e:
            return jsonify({'success': False, 'message': f'Failed to read forum log: {str(e)}'})
    
    # Read complete log from file
    output_lines = read_log_from_file(app_name)
    
    return jsonify({
        'success': True,
        'output': output_lines
    })

@app.route('/api/test_log/<app_name>')
def test_log(app_name):
    """Test log writing function"""
    if app_name not in processes:
        return jsonify({'success': False, 'message': 'Unknown application'})
    
    # Write test message
    test_msg = f"[{datetime.now().strftime('%H:%M:%S')}] Test log message - {datetime.now()}"
    write_log_to_file(app_name, test_msg)
    
    # Send via Socket.IO
    socketio.emit('console_output', {
        'app': app_name,
        'line': test_msg
    })
    
    return jsonify({
        'success': True,
        'message': f'Test message written to {app_name} log'
    })

@app.route('/api/forum/start')
def start_forum_monitoring_api():
    """Manually start ForumEngine Forum"""
    try:
        from ForumEngine.monitor import start_forum_monitoring
        success = start_forum_monitoring()
        if success:
            return jsonify({'success': True, 'message': 'ForumEngine Forum started'})
        else:
            return jsonify({'success': False, 'message': 'ForumEngine Forum start failed'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Failed to start forum: {str(e)}'})

@app.route('/api/forum/stop')
def stop_forum_monitoring_api():
    """Manually stop ForumEngine Forum"""
    try:
        from ForumEngine.monitor import stop_forum_monitoring
        stop_forum_monitoring()
        return jsonify({'success': True, 'message': 'ForumEngine Forum stopped'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Failed to stop forum: {str(e)}'})

@app.route('/api/forum/log')
def get_forum_log():
    """Get ForumEngine forum.log content"""
    try:
        forum_log_file = LOG_DIR / "forum.log"
        if not forum_log_file.exists():
            return jsonify({
                'success': True,
                'log_lines': [],
                'parsed_messages': [],
                'total_lines': 0
            })
        
        with open(forum_log_file, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
            lines = [line.rstrip('\n\r') for line in lines if line.strip()]
        
        # Parse each log line and extract dialogue info
        parsed_messages = []
        for line in lines:
            parsed_message = parse_forum_log_line(line)
            if parsed_message:
                parsed_messages.append(parsed_message)
        
        return jsonify({
            'success': True,
            'log_lines': lines,
            'parsed_messages': parsed_messages,
            'total_lines': len(lines)
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'Failed to read forum.log: {str(e)}'})

@app.route('/api/search', methods=['POST'])
def search():
    """Unified search interface"""
    data = request.get_json()
    query = data.get('query', '').strip()
    
    if not query:
        return jsonify({'success': False, 'message': 'Search query cannot be empty'})
    
    # ForumEngine already running in background, will auto-detect search activity
    # logger.info("ForumEngine: Search request received, forum will auto-detect log changes")
    
    # Check which apps are running
    check_app_status()
    running_apps = [name for name, info in processes.items() if info['status'] == 'running']
    
    if not running_apps:
        return jsonify({'success': False, 'message': 'No running applications'})
    
    # Send search request to running applications
    results = {}
    api_ports = {'insight': 8601, 'media': 8602, 'query': 8603}
    
    for app_name in running_apps:
        try:
            api_port = api_ports[app_name]
            # Call Streamlit app API endpoint
            response = requests.post(
                f"http://localhost:{api_port}/api/search",
                json={'query': query},
                timeout=10
            )
            if response.status_code == 200:
                results[app_name] = response.json()
            else:
                results[app_name] = {'success': False, 'message': 'API call failed'}
        except Exception as e:
            results[app_name] = {'success': False, 'message': str(e)}
    
    # After search, can choose to stop monitoring or let it continue to capture subsequent logs
    # We keep monitoring running here, user can manually stop via other interfaces
    
    return jsonify({
        'success': True,
        'query': query,
        'results': results
    })


@app.route('/api/config', methods=['GET'])
def get_config():
    """Expose selected configuration values to the frontend."""
    try:
        config_values = read_config_values()
        return jsonify({'success': True, 'config': config_values})
    except Exception as exc:
        logger.exception("Failed to read config")
        return jsonify({'success': False, 'message': f'Failed to read config: {exc}'}), 500


@app.route('/api/config', methods=['POST'])
def update_config():
    """Update configuration values and persist them to config.py."""
    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict) or not payload:
        return jsonify({'success': False, 'message': 'Request body cannot be empty'}), 400

    updates = {}
    for key, value in payload.items():
        if key in CONFIG_KEYS:
            updates[key] = value if value is not None else ''

    if not updates:
        return jsonify({'success': False, 'message': 'No configuration items to update'}), 400

    try:
        write_config_values(updates)
        updated_config = read_config_values()
        return jsonify({'success': True, 'config': updated_config})
    except Exception as exc:
        logger.exception("Failed to update config")
        return jsonify({'success': False, 'message': f'Failed to update config: {exc}'}), 500


@app.route('/api/system/status')
def get_system_status():
    """Return system startup status."""
    state = _get_system_state()
    return jsonify({
        'success': True,
        'started': state['started'],
        'starting': state['starting']
    })


@app.route('/api/system/start', methods=['POST'])
def start_system():
    """Start complete system upon request."""
    allowed, message = _prepare_system_start()
    if not allowed:
        return jsonify({'success': False, 'message': message}), 400

    try:
        success, logs, errors = initialize_system_components()
        if success:
            _set_system_state(started=True)
            return jsonify({'success': True, 'message': 'System startup success', 'logs': logs})

        _set_system_state(started=False)
        return jsonify({
            'success': False,
            'message': 'System startup failed',
            'logs': logs,
            'errors': errors
        }), 500
    except Exception as exc:  # pragma: no cover - catch all
        logger.exception("Exception during system startup")
        _set_system_state(started=False)
        return jsonify({'success': False, 'message': f'System startup exception: {exc}'}), 500
    finally:
        _set_system_state(starting=False)

@socketio.on('connect')
def handle_connect():
    """Client connected"""
    emit('status', 'Connected to Flask server')

@socketio.on('request_status')
def handle_status_request():
    """Request status update"""
    check_app_status()
    emit('status_update', {
        app_name: {
            'status': info['status'],
            'port': info['port']
        }
        for app_name, info in processes.items()
    })

if __name__ == '__main__':
    HOST = '0.0.0.0'
    PORT = 5001
    logger.info("Waiting for config confirmation, system will start components after frontend command...")
    logger.info(f"Flask server started, access at: http://{HOST}:{PORT}")
    
    try:
        socketio.run(app, host=HOST, port=PORT, debug=False)
    except KeyboardInterrupt:
        logger.info("\nClosing application...")
        cleanup_processes()
        
    
