import os
import re
import html
import base64
from email.mime.text import MIMEText

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from src.config import SCOPES, TOKEN_PATH


def get_gmail_service():
    creds = None

    token_dir = os.path.dirname(TOKEN_PATH)
    if token_dir:
        os.makedirs(token_dir, exist_ok=True)

    if os.path.exists(TOKEN_PATH) and os.path.getsize(TOKEN_PATH) > 0:
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists("credentials.json") or os.path.getsize("credentials.json") == 0:
                raise FileNotFoundError("credentials.json is missing or empty")
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)

        with open(TOKEN_PATH, "w", encoding="utf-8") as token:
            token.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)


def ensure_label(service, label_name: str) -> str:
    labels = service.users().labels().list(userId="me").execute().get("labels", [])
    for label in labels:
        if label["name"] == label_name:
            return label["id"]

    created = service.users().labels().create(
        userId="me",
        body={
            "name": label_name,
            "labelListVisibility": "labelShow",
            "messageListVisibility": "show",
        },
    ).execute()
    return created["id"]


def search_messages(service, query: str):
    result = service.users().messages().list(userId="me", q=query, maxResults=20).execute()
    msgs = result.get("messages", [])
    return [m["id"] for m in msgs]


def get_message(service, msg_id: str):
    return service.users().messages().get(userId="me", id=msg_id, format="full").execute()


def _decode_part_data(data: str) -> str:
    if not data:
        return ""
    try:
        decoded_bytes = base64.urlsafe_b64decode(data.encode("utf-8"))
        return decoded_bytes.decode("utf-8", errors="ignore")
    except Exception:
        return ""


def _extract_plain_email(from_header: str) -> str:
    if not from_header:
        return ""
    m = re.search(r"<([^>]+)>", from_header)
    if m:
        return m.group(1).strip()
    return from_header.strip()


def _html_to_text(s: str) -> str:
    if not s:
        return ""
    s = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", s)
    s = re.sub(r"(?i)<br\s*/?>", "\n", s)
    s = re.sub(r"(?i)</p>", "\n", s)
    s = re.sub(r"(?s)<[^>]+>", " ", s)
    s = html.unescape(s)
    s = s.replace("\r", "\n")
    s = re.sub(r"\n{3,}", "\n\n", s)
    s = re.sub(r"[ \t]+", " ", s)
    return s.strip()


def _walk_parts_for_text(part, plain_chunks, html_chunks):
    mime_type = part.get("mimeType", "")
    body = part.get("body", {}) or {}
    data = body.get("data", "")

    if mime_type == "text/plain" and data:
        txt = _decode_part_data(data)
        if txt.strip():
            plain_chunks.append(txt)

    elif mime_type == "text/html" and data:
        txt = _decode_part_data(data)
        if txt.strip():
            html_chunks.append(txt)

    for child in part.get("parts", []) or []:
        _walk_parts_for_text(child, plain_chunks, html_chunks)


def extract_subject_and_body(message):
    payload = message.get("payload", {})
    headers = payload.get("headers", [])

    subject = ""
    from_header = ""

    for h in headers:
        name = h.get("name", "").lower()
        if name == "subject":
            subject = h.get("value", "")
        elif name == "from":
            from_header = h.get("value", "")

    plain_chunks = []
    html_chunks = []

    _walk_parts_for_text(payload, plain_chunks, html_chunks)

    body = "\n".join(x for x in plain_chunks if x.strip()).strip()

    if not body:
        html_text = "\n".join(x for x in html_chunks if x.strip()).strip()
        body = _html_to_text(html_text)

    if not body:
        data = payload.get("body", {}).get("data", "")
        raw = _decode_part_data(data)
        body = raw if raw.strip() else _html_to_text(raw)

    from_email = _extract_plain_email(from_header)
    return subject, body, from_email


def send_message(service, to_email: str, subject: str, body: str, thread_id=None, is_html=False):
    subtype = "html" if is_html else "plain"
    msg = MIMEText(body, subtype, "utf-8")
    msg["to"] = to_email
    msg["subject"] = subject

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
    payload = {"raw": raw}
    if thread_id:
        payload["threadId"] = thread_id

    return service.users().messages().send(userId="me", body=payload).execute()


def modify_labels(service, msg_id: str, add_label_ids=None, remove_label_ids=None):
    body = {
        "addLabelIds": add_label_ids or [],
        "removeLabelIds": remove_label_ids or [],
    }
    return service.users().messages().modify(userId="me", id=msg_id, body=body).execute()
