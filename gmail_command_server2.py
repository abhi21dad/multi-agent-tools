import os.path
import base64
from email.mime.text import MIMEText
from flask import Flask, request, jsonify
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import traceback
from logger import get_logger

# Initialize logger
logger = get_logger('gmail_server')

SCOPES = ['https://www.googleapis.com/auth/gmail.send', 'https://www.googleapis.com/auth/gmail.readonly']
AUTH_TOKEN = os.environ.get("GMAIL_SERVER_AUTH_TOKEN", "GmailPass123!@#")
app = Flask(__name__)

# Request counter for metrics
request_counter = {'total': 0, 'success': 0, 'errors': 0}


def get_gmail_service():
    """Builds and returns a Gmail service object after authenticating."""
    creds = None
    if not os.path.exists('token_gmail.json'): 
        logger.error("token_gmail.json not found. Please run the authenticator script.")
        return None
    try:
        creds = Credentials.from_authorized_user_file('token_gmail.json', SCOPES)
       
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                logger.info("Refreshing expired Gmail credentials")
                creds.refresh(Request())
                # Save the credentials for the next run
                with open('token_gmail.json', 'w') as token:
                    token.write(creds.to_json())
                logger.info("Gmail credentials refreshed successfully")
            else:
                logger.error("Credentials are not valid and cannot be refreshed. Please re-run the authenticator.")
                return None
        return build('gmail', 'v1', credentials=creds)
    except Exception as e:
        logger.error(f"Error building Gmail service: {str(e)}\n{traceback.format_exc()}")
        return None

def get_email_body(payload):
    """
    Parses the payload of an email to find the plain text body.
    Handles various email structures.
    """
    if 'parts' in payload:
        for part in payload['parts']:
            if part['mimeType'] == 'text/plain':
                data = part['body'].get('data')
                if data:
                    return base64.urlsafe_b64decode(data.encode('ASCII')).decode('utf-8')
    elif 'body' in payload:
        data = payload['body'].get('data')
        if data:
            return base64.urlsafe_b64decode(data.encode('ASCII')).decode('utf-8')
    # Return a default message if no plain text body is found
    return "Email body could not be extracted in plain text format."

# --- Server Endpoints ---
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
    # Check if Gmail service is available
    service_healthy = os.path.exists('token_gmail.json')
    
    return jsonify({
        "status": "healthy" if service_healthy else "degraded",
        "service": "gmail_server",
        "gmail_token_exists": service_healthy,
        "metrics": request_counter
    }), 200 if service_healthy else 503

@app.route('/send', methods=['POST'])
def send_email_route():
    """Endpoint to send an email."""
    service = get_gmail_service()
    if not service:
        logger.error("Failed to connect to Gmail service")
        request_counter['errors'] += 1
        return jsonify({"error": "Could not connect to Gmail service"}), 500
    
    data = request.get_json()
    recipient, subject, body = data.get('recipient'), data.get('subject'), data.get('body')
    
    if not all([recipient, subject, body]):
        logger.warning("Send email request missing required fields")
        request_counter['errors'] += 1
        return jsonify({"error": "Missing 'recipient', 'subject', or 'body'"}), 400
    
    try:
        message = MIMEText(body)
        message['to'] = recipient
        message['subject'] = subject
        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        create_message = {'raw': encoded_message}
        send_message = (service.users().messages().send(userId="me", body=create_message).execute())
        
        logger.info(f"Email sent successfully to {recipient} with subject: {subject}")
        request_counter['success'] += 1
        return jsonify({"success": True, "message_id": send_message['id']})
    except Exception as e:
        logger.error(f"Error sending email: {str(e)}\n{traceback.format_exc()}")
        request_counter['errors'] += 1
        return jsonify({"error": str(e)}), 500

@app.route('/list_emails', methods=['POST'])
def list_emails_route():
    """Endpoint to list recent emails."""
    service = get_gmail_service()
    if not service: 
        return jsonify({"error": "Could not connect to Gmail service"}), 500
    try:
        results = service.users().messages().list(userId='me', labelIds=['INBOX'], maxResults=10).execute()
        messages = results.get('messages', [])
        email_list = []
        if not messages: 
            return jsonify({"emails": [], "message": "No new messages found."})
        for message in messages:
            msg = service.users().messages().get(userId='me', id=message['id']).execute()
            headers = msg['payload']['headers']
            email_data = {
                'from': next((h['value'] for h in headers if h['name'] == 'From'), 'N/A'),
                'subject': next((h['value'] for h in headers if h['name'] == 'Subject'), 'N/A'),
                'snippet': msg['snippet']
            }
            email_list.append(email_data)
        return jsonify({"emails": email_list})
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

@app.route('/read_email', methods=['POST'])
def read_email_route():
    """Endpoint to search for and read a specific email."""
    service = get_gmail_service()
    if not service:
        return jsonify({"error": "Could not connect to Gmail service"}), 500

    data = request.get_json()
    search_query = data.get('search_query')
    if not search_query:
        return jsonify({"error": "Missing 'search_query' parameter"}), 400

    try:
        results = service.users().messages().list(userId='me', q=search_query, maxResults=1).execute()
        messages = results.get('messages', [])
        
        if not messages:
            return jsonify({"error": f"No email found matching the query: '{search_query}'"})

        message_id = messages[0]['id']
        msg = service.users().messages().get(userId='me', id=message_id, format='full').execute()
        
        body_content = get_email_body(msg['payload'])
        
        return jsonify({"success": True, "content": body_content})
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

if __name__ == '__main__':
    logger.info("Starting Gmail Command Server on port 5004...")
    logger.info(f"Gmail token exists: {os.path.exists('token_gmail.json')}")
    logger.info(f"Authentication: {'Enabled' if AUTH_TOKEN else 'Disabled'}")
    
    try:
        app.run(host='0.0.0.0', port=5004, debug=False)
    except KeyboardInterrupt:
        logger.info("Gmail Command Server stopped by user")
    except Exception as e:
        logger.critical(f"Fatal error starting server: {str(e)}")
