import json
import logging
import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

_BASE = os.path.dirname(os.path.abspath(__file__))
_TOKEN_FILE = os.path.join(_BASE, "../../google_token.json")
_CREDS_FILE = os.path.join(_BASE, "../../credentials.json")


def get_drive_service():
    creds = None

    # Production: token via environment variable (base64-encoded JSON)
    token_env = os.environ.get("GOOGLE_TOKEN_JSON")
    if token_env:
        creds = Credentials.from_authorized_user_info(json.loads(token_env), SCOPES)

    # Local dev: token file
    if not creds and os.path.exists(_TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(_TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            logger.info("Google token renovado")
        else:
            if not os.path.exists(_CREDS_FILE):
                raise FileNotFoundError(
                    f"credentials.json não encontrado em {_CREDS_FILE}. "
                    "Baixe do Google Cloud Console e coloque na raiz do projeto."
                )
            flow = InstalledAppFlow.from_client_secrets_file(_CREDS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
            logger.info("Google OAuth concluído")

        with open(_TOKEN_FILE, "w") as f:
            f.write(creds.to_json())

    return build("drive", "v3", credentials=creds)
