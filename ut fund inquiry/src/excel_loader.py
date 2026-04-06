from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Set, Tuple

import pandas as pd

from src.config import (
    MASTERLIST_PATH,
    TAB_1,
    TAB_2,
    ISIN_COL,
    PREFIX_COL,
    FUND_NAME_COL,
    TRAILER_FEE_FIXED_COL,
    TRAILER_FEE_PCT_MGMT_COL,
)


@dataclass
class MasterData:
    prefixes: Set[str]
    isins: Set[str]
    prefix_to_isins: Dict[str, List[str]]
    isin_details: Dict[str, Dict[str, str]]


def _clean_str(x) -> str:
    if pd.isna(x):
        return ""
    return str(x).strip()


def _normalize_col_name(name: str) -> str:
    return " ".join(str(name).strip().lower().split())


def _find_column(df: pd.DataFrame, wanted: str, aliases: List[str] | None = None) -> str | None:
    aliases = aliases or []
    all_targets = [wanted] + aliases
    normalized_cols = {_normalize_col_name(col): col for col in df.columns}

    for item in all_targets:
        key = _normalize_col_name(item)
        if key in normalized_cols:
            return normalized_cols[key]
    return None


def _resolve_columns(df: pd.DataFrame, sheet_name: str) -> Tuple[str, str, str, str, str]:
    isin_actual = _find_column(
        df,
        ISIN_COL,
        aliases=["ISIN Code", "Fund ISIN", "ISIN No"],
    )
    prefix_actual = _find_column(
        df,
        PREFIX_COL,
        aliases=["ISIN Prefix", "ISIN prefix", "Prefix", "ISIN_Prefix"],
    )
    fund_name_actual = _find_column(
        df,
        FUND_NAME_COL,
        aliases=["Fund name", "Fund Name", "Name", "Fund", "Instrument Name"],
    )
    trailer_fee_fixed_actual = _find_column(
        df,
        TRAILER_FEE_FIXED_COL,
        aliases=[
            "Trailer Fee (If Fixed)",
            "Trailer fee (if fixed)",
            "Trailer Fee Fixed",
            "Trailer Fixed",
        ],
    )
    trailer_fee_pct_mgmt_actual = _find_column(
        df,
        TRAILER_FEE_PCT_MGMT_COL,
        aliases=[
            "Trailer Fee (If Percentage of Management fee)",
            "Trailer Fee (If Percentage of Management fee)",
            "Trailer fee (if percentage of management fee)",
            "Trailer % of Management Fee",
            "Trailer Fee % of Management Fee",
        ],
    )

    missing = []
    if isin_actual is None:
        missing.append(ISIN_COL)
    if prefix_actual is None:
        missing.append(PREFIX_COL)
    if fund_name_actual is None:
        missing.append(FUND_NAME_COL)
    if trailer_fee_fixed_actual is None:
        missing.append(TRAILER_FEE_FIXED_COL)
    if trailer_fee_pct_mgmt_actual is None:
        missing.append(TRAILER_FEE_PCT_MGMT_COL)

    if missing:
        raise ValueError(
            f"Missing required columns {missing} in sheet '{sheet_name}'. "
            f"Actual columns are: {list(df.columns)}"
        )

    return (
        isin_actual,
        prefix_actual,
        fund_name_actual,
        trailer_fee_fixed_actual,
        trailer_fee_pct_mgmt_actual,
    )


def _decimal_to_pct_string(d: Decimal) -> str:
    pct = d * Decimal("100")

    s = format(pct, "f")
    if "." in s:
        s = s.rstrip("0").rstrip(".")

    if "." not in s:
        s = s + ".00"
    else:
        decimals = len(s.split(".", 1)[1])
        if decimals < 2:
            s = s + ("0" * (2 - decimals))

    return s + "%"


def _format_percentage_value(x) -> str:
    if pd.isna(x):
        return ""

    # numeric cell from Excel
    if isinstance(x, (int, float)):
        try:
            d = Decimal(str(x))
            return _decimal_to_pct_string(d)
        except (InvalidOperation, ValueError):
            return str(x).strip()

    s = str(x).strip()
    if s == "":
        return ""

    # keep dashes / NA-like text unchanged
    if s in {"-", "N/A", "n/a", "NA", "na"}:
        return s

    # already contains %
    if "%" in s:
        raw = s.replace("%", "").replace(",", "").strip()
        try:
            d = Decimal(raw)
            return _decimal_to_pct_string(d / Decimal("100"))
        except (InvalidOperation, ValueError):
            return s

    # plain numeric string like 0.5 / 0.25 / 0.00875
    raw = s.replace(",", "")
    try:
        d = Decimal(raw)
        return _decimal_to_pct_string(d)
    except (InvalidOperation, ValueError):
        return s


def _read_and_standardize_sheet(xls: pd.ExcelFile, sheet_name: str) -> pd.DataFrame:
    df = pd.read_excel(xls, sheet_name=sheet_name)

    (
        isin_actual,
        prefix_actual,
        fund_name_actual,
        trailer_fee_fixed_actual,
        trailer_fee_pct_mgmt_actual,
    ) = _resolve_columns(df, sheet_name)

    out = df[
        [
            isin_actual,
            prefix_actual,
            fund_name_actual,
            trailer_fee_fixed_actual,
            trailer_fee_pct_mgmt_actual,
        ]
    ].copy()

    out.columns = [
        ISIN_COL,
        PREFIX_COL,
        FUND_NAME_COL,
        TRAILER_FEE_FIXED_COL,
        TRAILER_FEE_PCT_MGMT_COL,
    ]

    out[ISIN_COL] = out[ISIN_COL].map(lambda x: _clean_str(x).upper())
    out[PREFIX_COL] = out[PREFIX_COL].map(lambda x: _clean_str(x).upper())
    out[FUND_NAME_COL] = out[FUND_NAME_COL].map(_clean_str)

    # convert fraction values to exact percentage strings
    out[TRAILER_FEE_FIXED_COL] = out[TRAILER_FEE_FIXED_COL].map(_format_percentage_value)
    out[TRAILER_FEE_PCT_MGMT_COL] = out[TRAILER_FEE_PCT_MGMT_COL].map(_format_percentage_value)

    out = out[(out[ISIN_COL] != "") & (out[PREFIX_COL] != "")]
    out = out.drop_duplicates()

    return out


def load_master_data() -> MasterData:
    xls = pd.ExcelFile(MASTERLIST_PATH)

    df1 = _read_and_standardize_sheet(xls, TAB_1)
    df2 = _read_and_standardize_sheet(xls, TAB_2)

    combined = pd.concat([df1, df2], ignore_index=True).drop_duplicates()

    prefixes = set(combined[PREFIX_COL].tolist())
    isins = set(combined[ISIN_COL].tolist())

    prefix_to_isins: Dict[str, List[str]] = {}
    isin_details: Dict[str, Dict[str, str]] = {}

    for _, row in combined.iterrows():
        prefix = row[PREFIX_COL]
        isin = row[ISIN_COL]
        fund_name = row[FUND_NAME_COL]
        trailer_fee_fixed = row[TRAILER_FEE_FIXED_COL]
        trailer_fee_pct_mgmt = row[TRAILER_FEE_PCT_MGMT_COL]

        prefix_to_isins.setdefault(prefix, []).append(isin)

        if isin not in isin_details:
            isin_details[isin] = {
                "fund_name": fund_name,
                "trailer_fee_fixed": trailer_fee_fixed,
                "trailer_fee_pct_mgmt": trailer_fee_pct_mgmt,
            }

    for k in prefix_to_isins:
        prefix_to_isins[k] = sorted(set(prefix_to_isins[k]))

    return MasterData(
        prefixes=prefixes,
        isins=isins,
        prefix_to_isins=prefix_to_isins,
        isin_details=isin_details,
    )
