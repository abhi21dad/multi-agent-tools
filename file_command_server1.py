import os
import traceback
from flask import Flask, request, jsonify
from logger import get_logger
from dotenv import load_dotenv

load_dotenv()

# Initialize logger
logger = get_logger('file_server')

SANDBOX_DIRECTORY = os.path.abspath(os.path.join(os.getcwd(), "file_sandbox"))

# User's home directory
USER_HOME = os.path.expanduser("~")

# Allowed directories - sandbox + common user folders
ALLOWED_DIRECTORIES = [
    SANDBOX_DIRECTORY,
    os.path.join(USER_HOME, "Downloads"),
    os.path.join(USER_HOME, "Documents"),
    os.path.join(USER_HOME, "Desktop"),
]

AUTH_TOKEN = os.environ.get("FILE_SERVER_AUTH_TOKEN", "FilePass123!@#")

app = Flask(__name__)

# Request counter for metrics
request_counter = {'total': 0, 'success': 0, 'errors': 0}


def secure_path(path):
    """Validates that the requested file path is inside an allowed directory."""
    # Handle absolute paths (like ~/Downloads/file.txt or /Users/.../Downloads/file.txt)
    if path.startswith("~"):
        path = os.path.expanduser(path)
    
    # If it's already an absolute path, check if it's in allowed directories
    if os.path.isabs(path):
        normalized_path = os.path.normpath(path)
        for allowed_dir in ALLOWED_DIRECTORIES:
            if normalized_path.startswith(allowed_dir):
                return normalized_path
        return None  # Absolute path not in allowed directories
    
    # For relative paths, default to sandbox
    normalized_path = os.path.normpath(path)
    requested_path = os.path.abspath(os.path.join(SANDBOX_DIRECTORY, normalized_path))
    
    if not requested_path.startswith(SANDBOX_DIRECTORY):
        return None 
    return requested_path


@app.before_request
def check_auth():
    """Authenticates every incoming request."""
    request_counter['total'] += 1
    
    # Skip auth for health and favicon
    if request.path in ['/health', '/favicon.ico']:
        return
    
    if not request.is_json:
        logger.warning(f"Non-JSON request to {request.path} from {request.remote_addr}")
        request_counter['errors'] += 1
        return jsonify({"error": "Request must be JSON"}), 400
    
    data = request.get_json()
    if data.get('token') != AUTH_TOKEN:
        logger.warning(f"Unauthorized request to {request.path} from {request.remote_addr}")
        request_counter['errors'] += 1
        return jsonify({"error": "Unauthorized"}), 401
    
    logger.debug(f"Authenticated request to {request.path}")


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for monitoring and Docker."""
    return jsonify({
        "status": "healthy",
        "service": "file_server",
        "sandbox_directory": SANDBOX_DIRECTORY,
        "metrics": request_counter
    }), 200


@app.route('/write', methods=['POST'])
def write_local_file():
    """Endpoint to create, overwrite, or append to a local file."""
    data = request.get_json()
    path = data.get('path')
    content = data.get('content', '')
    mode = data.get('mode', 'overwrite')

    if not path:
        logger.warning("Write request missing 'path' parameter")
        request_counter['errors'] += 1
        return jsonify({"error": "Missing 'path' parameter"}), 400

    safe_path = secure_path(path)
    if not safe_path:
        logger.warning(f"Access denied for path: {path}")
        request_counter['errors'] += 1
        return jsonify({"error": "Access denied: Path is outside the secure sandbox."}), 403

    try:
        os.makedirs(os.path.dirname(safe_path), exist_ok=True)
        file_mode = 'a' if mode == 'append' else 'w'
        
        with open(safe_path, file_mode, encoding='utf-8') as f:
            f.write(content)

        logger.info(f"Successfully wrote to file: {path} (mode: {mode}, size: {len(content)} bytes)")
        request_counter['success'] += 1
        return jsonify({"success": True, "message": f"File '{path}' has been written successfully."})
    except Exception as e:
        logger.error(f"Error writing file {path}: {str(e)}\n{traceback.format_exc()}")
        request_counter['errors'] += 1
        return jsonify({"error": f"A server error occurred: {str(e)}"}), 500


@app.route('/read', methods=['POST'])
def read_local_file():
    data = request.get_json()
    path = data.get('path')
    
    if not path:
        logger.warning("Read request missing 'path' parameter")
        request_counter['errors'] += 1
        return jsonify({"error": "Missing 'path'"}), 400
    
    safe_path = secure_path(path)
    if not safe_path or not os.path.exists(safe_path):
        logger.warning(f"File not found or access denied: {path}")
        request_counter['errors'] += 1
        return jsonify({"error": "File not found or access denied."}), 404
    
    try:
        with open(safe_path, 'r', encoding='utf-8') as f:
            content = f.read()
        logger.info(f"Successfully read file: {path} (size: {len(content)} bytes)")
        request_counter['success'] += 1
        return jsonify({"success": True, "content": content})
    except Exception as e:
        logger.error(f"Error reading file {path}: {str(e)}")
        request_counter['errors'] += 1
        return jsonify({"error": str(e)}), 500

@app.route('/list', methods=['POST'])
def list_local_files():
    data = request.get_json()
    path = data.get('path', '.')
    safe_path = secure_path(path)
    
    if not safe_path:
        logger.warning(f"Access denied for list path: {path}")
        request_counter['errors'] += 1
        return jsonify({"error": "Access denied"}), 403
    
    try:
        items = os.listdir(safe_path)
        logger.info(f"Successfully listed directory: {path} ({len(items)} items)")
        request_counter['success'] += 1
        return jsonify({"success": True, "items": items})
    except Exception as e:
        logger.error(f"Error listing directory {path}: {str(e)}")
        request_counter['errors'] += 1
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    if not os.path.exists(SANDBOX_DIRECTORY):
        os.makedirs(SANDBOX_DIRECTORY)
        logger.info(f"Created sandbox directory at: {SANDBOX_DIRECTORY}")
    else:
        logger.info(f"Using existing sandbox directory: {SANDBOX_DIRECTORY}")
    
    logger.info("Starting File Command Server on port 5002...")
    logger.info(f"Authentication: {'Enabled' if AUTH_TOKEN else 'Disabled'}")
    
    try:
        app.run(host='0.0.0.0', port=5002, debug=False)
    except KeyboardInterrupt:
        logger.info("File Command Server stopped by user")
    except Exception as e:
        logger.critical(f"Fatal error starting server: {str(e)}")


