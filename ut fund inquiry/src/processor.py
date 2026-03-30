from __future__ import annotations

import os
import re

from src.gmail_client import get_message, extract_subject_and_body, send_message, modify_labels
from src.utils import (
    build_reply_rows,
    build_reply_html,
    build_reply_plain,
    build_internal_forward_html,
)
from src.config import (
    FORWARD_TO,
    PROCESSED_LABEL,
    NEEDS_CONFIRM_LABEL,
    AVAILABLE_LABEL,
    PROCESSED_IDS_PATH,
    GMAIL_ADDRESS,
    PRODUCTS_TEAM_EMAIL,
    ALLOWED_SENDER_DOMAINS,
)
from src.excel_loader import MasterData


ISIN_PATTERN = r"\b[A-Z]{2}[A-Z0-9]{10}\b"


def _load_processed_ids() -> set[str]:
    try:
        with open(PROCESSED_IDS_PATH, "r", encoding="utf-8") as f:
            return {line.strip() for line in f if line.strip()}
    except FileNotFoundError:
        return set()


def _save_processed_id(msg_id: str) -> None:
    processed_dir = os.path.dirname(PROCESSED_IDS_PATH)
    if processed_dir:
        os.makedirs(processed_dir, exist_ok=True)

    with open(PROCESSED_IDS_PATH, "a", encoding="utf-8") as f:
        f.write(msg_id + "\n")


def _extract_isin_candidates(text: str) -> list[str]:
    text = (text or "").upper()
    found = re.findall(ISIN_PATTERN, text)

    seen = set()
    ordered = []
    for x in found:
        if x not in seen:
            seen.add(x)
            ordered.append(x)
    return ordered


def _has_known_prefix_plus_digit(token: str, prefixes: set[str]) -> bool:
    token = token.upper()
    for prefix in prefixes:
        prefix = prefix.upper()
        if token.startswith(prefix) and len(token) > len(prefix) and token[len(prefix)].isdigit():
            return True
    return False


def _extract_domain(email_address: str) -> str:
    if not email_address or "@" not in email_address:
        return ""
    return email_address.rsplit("@", 1)[1].strip().lower()


def _is_allowed_sender_domain(email_address: str) -> bool:
    domain = _extract_domain(email_address)
    return domain in ALLOWED_SENDER_DOMAINS


def process_one_message(service, msg_id: str, label_ids: dict[str, str], master: MasterData):
    processed_ids = _load_processed_ids()
    if msg_id in processed_ids:
        print(f"Skipping already processed message: {msg_id}")
        return

    message = get_message(service, msg_id)
    subject, body, from_email = extract_subject_and_body(message)
    thread_id = message.get("threadId")
    email_text = f"{subject}\n{body}"

    print("=" * 80)
    print(f"Processing message: {msg_id}")
    print(f"From: {from_email}")
    print(f"Subject: {subject}")
    print("Body preview:", repr(body[:1000]))

    if from_email and from_email.lower() == GMAIL_ADDRESS.lower():
        print("Skipped because sender is the same mailbox.")
        modify_labels(
            service,
            msg_id,
            add_label_ids=[label_ids[PROCESSED_LABEL]],
            remove_label_ids=["UNREAD"],
        )
        _save_processed_id(msg_id)
        return

    if not _is_allowed_sender_domain(from_email):
        print(f"Skipped because sender domain is not allowed: {_extract_domain(from_email)}")
        modify_labels(
            service,
            msg_id,
            add_label_ids=[label_ids[PROCESSED_LABEL]],
            remove_label_ids=["UNREAD"],
        )
        _save_processed_id(msg_id)
        return

    raw_candidates = _extract_isin_candidates(email_text)
    print(f"Raw 12-char ISIN-like candidates: {raw_candidates}")

    filtered_candidates = [
        x for x in raw_candidates
        if _has_known_prefix_plus_digit(x, master.prefixes)
    ]
    print(f"Filtered by known prefix+digit: {filtered_candidates}")

    rows, has_pending = build_reply_rows(filtered_candidates, master)
    reply_html = build_reply_html(rows, has_pending, PRODUCTS_TEAM_EMAIL)
    reply_plain = build_reply_plain(rows, has_pending, PRODUCTS_TEAM_EMAIL)

    print(f"Reply rows: {rows}")
    print(f"Has pending: {has_pending}")

    if from_email:
        reply_result = send_message(
            service=service,
            to_email=from_email,
            subject=f"Re: {subject}",
            body=reply_html,
            thread_id=thread_id,
            is_html=True,
        )
        print(f"Auto-reply sent to sender. Gmail message id: {reply_result.get('id')}")

    internal_html = build_internal_forward_html(
        original_from=from_email,
        original_subject=subject,
        original_body=body,
        reply_html=reply_html,
    )

    if FORWARD_TO:
        for recipient in FORWARD_TO:
            result = send_message(
                service=service,
                to_email=recipient,
                subject=f"[Fund Check Forward] {subject}",
                body=internal_html,
                thread_id=None,
                is_html=True,
            )
            print(f"Internal forward sent to {recipient}. Gmail message id: {result.get('id')}")

    add_labels = [label_ids[PROCESSED_LABEL]]
    if has_pending:
        add_labels.append(label_ids[NEEDS_CONFIRM_LABEL])
    else:
        add_labels.append(label_ids[AVAILABLE_LABEL])

    modify_labels(
        service,
        msg_id,
        add_label_ids=add_labels,
        remove_label_ids=["UNREAD"],
    )
    _save_processed_id(msg_id)