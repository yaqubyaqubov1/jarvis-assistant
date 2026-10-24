"""Connect your Gmail account to local JARVIS using Google's desktop OAuth.

Before running:
1. Create/select a Google Cloud project and enable Gmail API.
2. Configure the OAuth consent screen/test user if required.
3. Download a DESKTOP OAuth client JSON from Google Cloud.
4. python setup_gmail.py C:\path\to\client_secret.json

Tokens are stored by Windows Credential Manager through keyring.
Never commit or paste the client JSON, access tokens, or refresh tokens.
"""
from pathlib import Path
import sys

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
]


def main():
    if len(sys.argv) != 2:
        print('Usage: python setup_gmail.py "PATH_TO_GOOGLE_DESKTOP_OAUTH_CLIENT_JSON"')
        return 2
    path = Path(sys.argv[1]).expanduser().resolve()
    if not path.is_file():
        print("OAuth client JSON not found:", path)
        return 2
    try:
        import keyring
        from google_auth_oauthlib.flow import InstalledAppFlow
        flow = InstalledAppFlow.from_client_secrets_file(str(path), scopes=SCOPES)
        creds = flow.run_local_server(port=0, open_browser=True)
        if not creds or not creds.valid:
            raise RuntimeError("OAuth login did not finish.")
        keyring.set_password("JARVIS-Gmail-OAuth", "default", creds.to_json())
        print("Gmail connected. OAuth token stored in OS credential storage.")
        print("JARVIS can read your Gmail and prepare email drafts.")
        print("Sending an email always requires explicit GUI confirmation.")
        return 0
    except Exception as exc:
        print(f"Gmail connection failed: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
