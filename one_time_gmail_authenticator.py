import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

# This scope requests permission to send emails on your behalf.
SCOPES = ['https://www.googleapis.com/auth/gmail.send']

def main():
    """
    Runs the one-time authentication flow to get the user's permission
    and creates the token_gmail.json file.
    """
    creds = None
    
    # Check if the token already exists.
    if os.path.exists('token_gmail.json'):
        print("✅ 'token_gmail.json' already exists.")
        print("Authorization is complete. You can now run the main gmail_command_server.py.")
        print("If you have issues, delete 'token_gmail.json' and run this script again.")
        return

    # If no valid credentials exist, start the user login flow.
    print("🚀 Starting one-time authentication for Gmail...")
    print("Your browser will open for you to log in and grant permission.")
    
    # This part was causing the deadlock in the old server.
    # It requires the credentials.json file you downloaded from Google Cloud.
    flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
    creds = flow.run_local_server(port=0)

    # Save the credentials for the main server to use.
    with open('token_gmail.json', 'w') as token:
        token.write(creds.to_json())
    
    print("\n✅ Authentication successful! 'token_gmail.json' has been created.")
    print("You can now start the `gmail_command_server.py` and use the chatbot.")

if __name__ == '__main__':
    main()
