'''import os.path
from flask import Flask, request, jsonify
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
# <<< MODIFICATION 1: Import the correct uploader class >>>
from googleapiclient.http import MediaIoBaseUpload
import io

# --- Configuration ---
SCOPES = ['https://www.googleapis.com/auth/drive']
AUTH_TOKEN = os.environ.get("GOOGLE_DRIVE_SERVER_AUTH_TOKEN", "abhi21dad")

app = Flask(__name__)

# --- Google Authentication Helper (Unchanged) ---
def get_drive_service():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    
    try:
        service = build('drive', 'v3', credentials=creds)
        return service
    except HttpError as error:
        print(f"An error occurred building the service: {error}")
        return None

# --- Server Endpoints (Unchanged except for /write) ---
@app.before_request
def check_auth():
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400
    data = request.get_json()
    if data.get('token') != AUTH_TOKEN:
        return jsonify({"error": "Unauthorized"}), 401

@app.route('/list', methods=['POST'])
def list_drive_files():
    # ... (This function is unchanged) ...
    service = get_drive_service()
    if not service:
        return jsonify({"error": "Could not connect to Google Drive service"}), 500
    
    try:
        results = service.files().list(
            pageSize=20, fields="nextPageToken, files(id, name, mimeType)").execute()
        items = results.get('files', [])
        return jsonify({"files": items})
    except HttpError as error:
        return jsonify({"error": f"An error occurred: {error}"}), 500

@app.route('/write', methods=['POST'])
def write_drive_file():
    service = get_drive_service()
    if not service:
        return jsonify({"error": "Could not connect to Google Drive service"}), 500

    data = request.get_json()
    filename = data.get('filename')
    content = data.get('content', '')
    if not filename:
        return jsonify({"error": "Missing 'filename' in request body"}), 400

    try:
        query = f"name='{filename}' and trashed=false"
        results = service.files().list(q=query, fields="files(id)").execute()
        items = results.get('files', [])
        
        file_metadata = {'name': filename}
        fh = io.BytesIO(content.encode('utf-8'))
        
        # <<< MODIFICATION 2: Use MediaIoBaseUpload instead of MediaFileUpload >>>
        media = MediaIoBaseUpload(fh, mimetype='text/plain', resumable=True)

        if items:
            file_id = items[0]['id']
            file = service.files().update(fileId=file_id, media_body=media).execute()
            message = f"File '{filename}' updated successfully."
        else:
            file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
            message = f"File '{filename}' created successfully."

        return jsonify({"success": True, "message": message, "file_id": file.get('id')})
    except HttpError as error:
        return jsonify({"error": f"An error occurred: {error}"}), 500

if __name__ == '__main__':
    print("Google Drive Command Server is running!")
    print("If this is the first run, a browser window will open for authentication.")
    app.run(host='0.0.0.0', port=5003, debug=True)

'''

'''import os.path
from flask import Flask, request, jsonify
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload # <<< MODIFIED: Added MediaIoBaseDownload
import io
import PyPDF2 # Required for reading PDFs

    # --- Configuration ---
SCOPES = ['https://www.googleapis.com/auth/drive']
AUTH_TOKEN = os.environ.get("GOOGLE_DRIVE_SERVER_AUTH_TOKEN", "abhi21dad")
app = Flask(__name__)

    # --- Google Authentication Helper ---
def get_drive_service():
        creds = None
        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)
            with open('token.json', 'w') as token:
                token.write(creds.to_json())
        try:
            service = build('drive', 'v3', credentials=creds)
            return service
        except HttpError as error:
            print(f"An error occurred building the service: {error}")
            return None

    # --- Server Endpoints ---
@app.before_request
def check_auth():
        if not request.is_json:
            return jsonify({"error": "Request must be JSON"}), 400
        data = request.get_json()
        if data.get('token') != AUTH_TOKEN:
            return jsonify({"error": "Unauthorized"}), 401

@app.route('/read', methods=['POST'])
def read_drive_file():
        """Reads content from a file in Google Drive, with PDF support."""
        service = get_drive_service()
        if not service:
            return jsonify({"error": "Could not connect to Google Drive service"}), 500

        data = request.get_json()
        filename = data.get('filename')
        if not filename:
            return jsonify({"error": "Missing 'filename' in request body"}), 400

        try:
            query = f"name='{filename}' and trashed=false"
            results = service.files().list(q=query, fields="files(id, name, mimeType)").execute()
            items = results.get('files', [])
            if not items:
                return jsonify({"error": f"File '{filename}' not found in Google Drive."}), 404
            
            file_item = items[0]
            file_id = file_item['id']
            mime_type = file_item['mimeType']

            request_file = service.files().get_media(fileId=file_id)
            fh = io.BytesIO()
            
            # <<< MODIFIED: Replaced incorrect download logic with the correct protocol ---
            downloader = MediaIoBaseDownload(fh, request_file)
            done = False
            while done is False:
                status, done = downloader.next_chunk()
            # --- END MODIFICATION ---

            file_content_bytes = fh.getvalue()

            if mime_type == 'application/pdf':
                pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_content_bytes))
                text = ""
                for page in pdf_reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text
                return jsonify({"filename": filename, "content": text or "PDF contained no extractable text."})
            elif 'text' in mime_type:
                return jsonify({"filename": filename, "content": file_content_bytes.decode('utf-8')})
            else:
                return jsonify({"error": f"Unsupported file type ('{mime_type}'). Can only read text and PDF files."}), 400

        except HttpError as error:
            return jsonify({"error": f"An API error occurred: {error}"}), 500
        except Exception as e:
            return jsonify({"error": f"A general error occurred: {str(e)}"}), 500

@app.route('/list', methods=['POST'])
def list_drive_files():
        service = get_drive_service()
        if not service: return jsonify({"error": "Could not connect to Google Drive service"}), 500
        try:
            results = service.files().list(pageSize=20, fields="nextPageToken, files(id, name, mimeType)").execute()
            items = results.get('files', [])
            return jsonify({"files": items})
        except HttpError as error: return jsonify({"error": f"An error occurred: {error}"}), 500

@app.route('/write', methods=['POST'])
def write_drive_file():
        service = get_drive_service()
        if not service: return jsonify({"error": "Could not connect to Google Drive service"}), 500
        data = request.get_json()
        filename = data.get('filename')
        content = data.get('content', '')
        if not filename: return jsonify({"error": "Missing 'filename' in request body"}), 400
        try:
            query = f"name='{filename}' and trashed=false"
            results = service.files().list(q=query, fields="files(id)").execute()
            items = results.get('files', [])
            file_metadata = {'name': filename}
            fh = io.BytesIO(content.encode('utf-8'))
            media = MediaIoBaseUpload(fh, mimetype='text/plain', resumable=True)
            if items:
                file_id = items[0]['id']
                file = service.files().update(fileId=file_id, media_body=media).execute()
                message = f"File '{filename}' updated successfully."
            else:
                file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
                message = f"File '{filename}' created successfully."
            return jsonify({"success": True, "message": message, "file_id": file.get('id')})
        except HttpError as error: return jsonify({"error": f"An error occurred: {error}"}), 500

if __name__ == '__main__':
        print("Google Drive Command Server is running!")
        app.run(host='0.0.0.0', port=5003, debug=True)
'''
import os.path
from flask import Flask, request, jsonify
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload
import io
import PyPDF2 


SCOPES = ['https://www.googleapis.com/auth/drive']
AUTH_TOKEN = os.environ.get("GOOGLE_DRIVE_SERVER_AUTH_TOKEN", "abhi21dad")
app = Flask(__name__)

def get_drive_service():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    try:
        service = build('drive', 'v3', credentials=creds)
        return service
    except HttpError as error:
        print(f"An error occurred building the service: {error}")
        return None


@app.before_request
def check_auth():
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400
    data = request.get_json()
    if data.get('token') != AUTH_TOKEN:
        return jsonify({"error": "Unauthorized"}), 401

@app.route('/read', methods=['POST'])
def read_drive_file():
    """Reads content from a file in Google Drive, with PDF and IPYNB support."""
    service = get_drive_service()
    if not service:
        return jsonify({"error": "Could not connect to Google Drive service"}), 500

    data = request.get_json()
    filename = data.get('filename')
    if not filename:
        return jsonify({"error": "Missing 'filename' in request body"}), 400

    try:
        query = f"name='{filename}' and trashed=false"
        results = service.files().list(q=query, fields="files(id, name, mimeType)").execute()
        items = results.get('files', [])
        if not items:
            return jsonify({"error": f"File '{filename}' not found in Google Drive."}), 404
        
        file_item = items[0]
        file_id = file_item['id']
        mime_type = file_item['mimeType']

        request_file = service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        
        downloader = MediaIoBaseDownload(fh, request_file)
        done = False
        while done is False:
            status, done = downloader.next_chunk()

        file_content_bytes = fh.getvalue()

        if mime_type == 'application/pdf':
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_content_bytes))
            text = ""
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text
            return jsonify({"filename": filename, "content": text or "PDF contained no extractable text."})
      
        elif 'text' in mime_type or 'json' in mime_type:
            return jsonify({"filename": filename, "content": file_content_bytes.decode('utf-8')})
        else:
            return jsonify({"error": f"Unsupported file type ('{mime_type}'). Can only read text, PDF, and ipynb files."}), 400

    except HttpError as error:
        return jsonify({"error": f"An API error occurred: {error}"}), 500
    except Exception as e:
        return jsonify({"error": f"A general error occurred: {str(e)}"}), 500

@app.route('/list', methods=['POST'])
def list_drive_files():
    service = get_drive_service()
    if not service: return jsonify({"error": "Could not connect to Google Drive service"}), 500
    try:
        results = service.files().list(pageSize=20, fields="nextPageToken, files(id, name, mimeType)").execute()
        items = results.get('files', [])
        return jsonify({"files": items})
    except HttpError as error: return jsonify({"error": f"An error occurred: {error}"}), 500

@app.route('/write', methods=['POST'])
def write_drive_file():
    service = get_drive_service()
    if not service: return jsonify({"error": "Could not connect to Google Drive service"}), 500
    data = request.get_json()
    filename = data.get('filename')
    content = data.get('content', '')
    if not filename: return jsonify({"error": "Missing 'filename' in request body"}), 400
    try:
        query = f"name='{filename}' and trashed=false"
        results = service.files().list(q=query, fields="files(id)").execute()
        items = results.get('files', [])
        file_metadata = {'name': filename}
        fh = io.BytesIO(content.encode('utf-8'))
        media = MediaIoBaseUpload(fh, mimetype='text/plain', resumable=True)
        if items:
            file_id = items[0]['id']
            file = service.files().update(fileId=file_id, media_body=media).execute()
            message = f"File '{filename}' updated successfully."
        else:
            file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
            message = f"File '{filename}' created successfully."
        return jsonify({"success": True, "message": message, "file_id": file.get('id')})
    except HttpError as error: return jsonify({"error": f"An error occurred: {error}"}), 500

if __name__ == '__main__':
    print("Google Drive Command Server is running!")
    app.run(host='0.0.0.0', port=5003, debug=True)


