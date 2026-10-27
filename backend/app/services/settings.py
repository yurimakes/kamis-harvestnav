"""Read only the server credential from the repository's private .env file."""
import os
from pathlib import Path
import re

ENV_FILE = Path(__file__).resolve().parents[3] / ".env"
KEY_NAME = "DATA_GO_KR_SERVICE_KEY"


def service_key():
    value = os.environ.get(KEY_NAME)
    if value is None:
        try:
            lines = ENV_FILE.read_text(encoding="utf-8-sig").splitlines()
        except (OSError, UnicodeError):
            return ""
        values = []
        for line in lines:
            match = re.fullmatch(r"\s*(?:export\s+)?DATA_GO_KR_SERVICE_KEY\s*=\s*(.*?)\s*", line)
            if not match:
                continue
            entry = match[1]
            if entry.startswith(('"', "'")):
                if len(entry) < 2 or entry[-1] != entry[0]:
                    return ""
                entry = entry[1:-1]
            values.append(entry)
        if len(values) != 1:
            return ""
        value = values[0]
    value = value.strip()
    if not value or value.startswith("EXAMPLE_") or re.search(r"\s", value):
        return ""
    return value
