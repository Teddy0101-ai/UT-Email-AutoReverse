import os
import time
import traceback

from src.config import (
    GMAIL_QUERY,
    POLL_SECONDS,
    PROCESSED_LABEL,
    NEEDS_CONFIRM_LABEL,
    AVAILABLE_LABEL,
    LOG_PATH,
)
from src.gmail_client import get_gmail_service, ensure_label, search_messages
from src.excel_loader import load_master_data
from src.processor import process_one_message


def write_log(message: str) -> None:
    try:
        log_dir = os.path.dirname(LOG_PATH)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(message + "\n")
    except Exception:
        pass


def main() -> None:
    service = get_gmail_service()
    master = load_master_data()

    label_ids = {
        PROCESSED_LABEL: ensure_label(service, PROCESSED_LABEL),
        NEEDS_CONFIRM_LABEL: ensure_label(service, NEEDS_CONFIRM_LABEL),
        AVAILABLE_LABEL: ensure_label(service, AVAILABLE_LABEL),
    }

    print("Started Gmail fund checker...")
    print(f"Polling every {POLL_SECONDS} seconds")
    write_log("Started Gmail fund checker...")

    while True:
        try:
            master = load_master_data()
            msg_ids = search_messages(service, GMAIL_QUERY)

            if msg_ids:
                print(f"Found {len(msg_ids)} message(s)")
                write_log(f"Found {len(msg_ids)} message(s)")

            for msg_id in msg_ids:
                try:
                    process_one_message(service, msg_id, label_ids, master)
                except Exception as e:
                    print(f"Error processing message {msg_id}: {e}")
                    write_log(f"Error processing message {msg_id}: {e}")
                    traceback.print_exc()

        except Exception as e:
            print(f"Loop error: {e}")
            write_log(f"Loop error: {e}")
            traceback.print_exc()

        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()