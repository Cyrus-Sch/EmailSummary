from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from http.server import BaseHTTPRequestHandler, HTTPServer

# Replace with the scope of access you need
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
# Replace with the IP address and port number of the server
SERVER_ADDRESS = ('127.0.0.1', 5002)

class AuthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Extract the authorization code from the request path
        code = self.path.split('code=')[1]

        # Set up the OAuth2 flow
        flow = InstalledAppFlow.from_client_secrets_file(
            'credentials.json', # Replace with the path to your client secret file
            SCOPES
        )

        # Exchange the authorization code for access and refresh tokens
        flow.fetch_token(code=code)

        # Extract the access token from the credentials and send it in the response
        credentials = flow.credentials
        access_token = credentials.token
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(access_token.encode())

def get_auth_url():
    flow = InstalledAppFlow.from_client_secrets_file(
        'credentials.json',
        SCOPES,
        redirect_uri=f"https://emailsummary.herokuapp.com/oauth2callback/"
    )

    auth_url, _ = flow.authorization_url(access_type='offline', prompt='consent')
    return auth_url


def get_gmail_token():
    flow = InstalledAppFlow.from_client_secrets_file(
        'credentials.json',  # Replace with the path to your client secret file
        SCOPES,
        redirect_uri="https://emailsummary.herokuapp.com/oauth2callback/"
    )

    auth_url, _ = flow.authorization_url(access_type='offline', prompt='consent')

    print(f'Please visit the following URL to authorize access:\n{auth_url}')

# Example usage
if __name__ == '__main__':
    access_token = get_gmail_token()
    print('Access token:', access_token)
