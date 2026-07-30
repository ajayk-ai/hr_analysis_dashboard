import os

import gspread
from google.oauth2.service_account import Credentials

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def get_sheets_client() -> gspread.Client:
    credentials_path = os.environ["GOOGLE_SERVICE_ACCOUNT_FILE"]
    delegated_user = os.environ["GOOGLE_DELEGATED_USER"]
    credentials = Credentials.from_service_account_file(credentials_path, scopes=SCOPES)
    credentials = credentials.with_subject(delegated_user)
    return gspread.authorize(credentials)
