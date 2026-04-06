from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Set

from src.excel_loader import MasterData


@dataclass
class ParseResult:
    active_prefixes: Set[str]
    found_isins: Set[str]
    raw_prefix_digit_hits: Set[str]


def normalize_text(text: str) -> str:
    if not text:
        return ""
    text = text.upper()
    text = text.replace("\r", " ").replace("\n", " ")
    return text


def detect_active_prefixes(text: str, master: MasterData):
    active_prefixes: Set[str] = set()
    raw_hits: Set[str] = set()

    for prefix in master.prefixes:
        pattern = rf"(?<![A-Z0-9])({re.escape(prefix)}\d)"
        matches = re.findall(pattern, text)
        if matches:
            active_prefixes.add(prefix)
            raw_hits.update(matches)

    return active_prefixes, raw_hits


def detect_full_isins(text: str, master: MasterData, active_prefixes: Set[str]) -> Set[str]:
    found: Set[str] = set()

    for prefix in active_prefixes:
        for isin in master.prefix_to_isins.get(prefix, []):
            pattern = rf"(?<![A-Z0-9]){re.escape(isin)}(?![A-Z0-9])"
            if re.search(pattern, text):
                found.add(isin)

    return found


def parse_email_for_isins(subject: str, body: str, master: MasterData) -> ParseResult:
    text = normalize_text(f"{subject} {body}")
    active_prefixes, raw_hits = detect_active_prefixes(text, master)
    found_isins = detect_full_isins(text, master, active_prefixes)
    return ParseResult(
        active_prefixes=active_prefixes,
        found_isins=found_isins,
        raw_prefix_digit_hits=raw_hits,
    )
