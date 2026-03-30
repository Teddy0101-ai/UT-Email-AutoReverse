from dotenv import load_dotenv
import os

load_dotenv()

GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS", "uobkh.ut.inquiry@gmail.com")
POLL_SECONDS = int(os.getenv("POLL_SECONDS", "10"))

MASTERLIST_PATH = os.getenv("MASTERLIST_PATH", "masterlist.xlsx")
TOKEN_PATH = os.getenv("TOKEN_PATH", "data/token.json")
PROCESSED_IDS_PATH = os.getenv("PROCESSED_IDS_PATH", "data/processed_ids.txt")
LOG_PATH = os.getenv("LOG_PATH", "logs/app.log")

TAB_1 = os.getenv("TAB_1", "Allfunds")
TAB_2 = os.getenv("TAB_2", "Fund Master List")

ISIN_COL = os.getenv("ISIN_COL", "ISIN")
PREFIX_COL = os.getenv("PREFIX_COL", "ISIN prefix")
FUND_NAME_COL = os.getenv("FUND_NAME_COL", "Instrument Name")
TRAILER_FEE_COL = os.getenv("TRAILER_FEE_COL", "Trailer Fee")

PRODUCTS_TEAM_EMAIL = os.getenv(
    "PRODUCTS_TEAM_EMAIL",
    "GRP_SG_PWM_PROD_TEAM@uobkayhian.com",
)

FORWARD_TO = [x.strip() for x in os.getenv("FORWARD_TO", "").split(",") if x.strip()]

ALLOWED_SENDER_DOMAINS = [
    x.strip().lower()
    for x in os.getenv(
        "ALLOWED_SENDER_DOMAINS",
        "uobkayhian.com,uobkayhian.com.hk,uobkayhian.com.tw",
    ).split(",")
    if x.strip()
]

PROCESSED_LABEL = os.getenv("PROCESSED_LABEL", "UT_PROCESSED")
NEEDS_CONFIRM_LABEL = os.getenv("NEEDS_CONFIRM_LABEL", "UT_NEEDS_CONFIRM")
AVAILABLE_LABEL = os.getenv("AVAILABLE_LABEL", "UT_AVAILABLE")

GMAIL_QUERY = os.getenv("GMAIL_QUERY", "is:unread in:inbox -label:UT_PROCESSED")

SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.send",
]