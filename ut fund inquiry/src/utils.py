import html


def _preserve_value(value) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _normalize_fee_pair(fixed_value: str, pct_mgmt_value: str) -> tuple[str, str]:
    fixed_value = _preserve_value(fixed_value)
    pct_mgmt_value = _preserve_value(pct_mgmt_value)

    # if both populated, leave fixed blank
    if fixed_value not in {"", "-"} and pct_mgmt_value not in {"", "-"}:
        fixed_value = ""

    return fixed_value, pct_mgmt_value


def build_reply_rows(extracted_isins: list[str], master) -> tuple[list[dict], bool]:
    rows = []
    has_pending = False

    for isin in extracted_isins:
        detail = master.isin_details.get(isin)

        # ISIN not found in masterlist
        if detail is None:
            rows.append(
                {
                    "isin": isin,
                    "fund_name": "Pending manual confirmation",
                    "trailer_fee_fixed": "-",
                    "trailer_fee_pct_mgmt": "-",
                    "can_trade_now": "-",
                    "is_pending": True,
                }
            )
            has_pending = True
            continue

        # ISIN found in masterlist
        fund_name_raw = detail.get("fund_name", "")
        trailer_fee_fixed_raw = detail.get("trailer_fee_fixed", "")
        trailer_fee_pct_mgmt_raw = detail.get("trailer_fee_pct_mgmt", "")

        fund_name = _preserve_value(fund_name_raw)
        trailer_fee_fixed = _preserve_value(trailer_fee_fixed_raw)
        trailer_fee_pct_mgmt = _preserve_value(trailer_fee_pct_mgmt_raw)

        trailer_fee_fixed, trailer_fee_pct_mgmt = _normalize_fee_pair(
            trailer_fee_fixed,
            trailer_fee_pct_mgmt,
        )

        rows.append(
            {
                "isin": isin,
                "fund_name": fund_name,
                "trailer_fee_fixed": trailer_fee_fixed,
                "trailer_fee_pct_mgmt": trailer_fee_pct_mgmt,
                "can_trade_now": "Yes",
                "is_pending": False,
            }
        )

    if not rows:
        rows.append(
            {
                "isin": "No valid ISIN detected",
                "fund_name": "Pending manual confirmation",
                "trailer_fee_fixed": "-",
                "trailer_fee_pct_mgmt": "-",
                "can_trade_now": "-",
                "is_pending": True,
            }
        )
        has_pending = True

    # sort: Yes first, pending bottom
    rows = sorted(
        rows,
        key=lambda r: (
            1 if r["is_pending"] else 0,
            r["isin"],
        ),
    )

    return rows, has_pending


def _build_html_table_rows(rows: list[dict]) -> str:
    non_pending_rows = [row for row in rows if not row.get("is_pending")]
    pending_rows = [row for row in rows if row.get("is_pending")]

    html_rows = []

    # normal rows first
    for row in non_pending_rows:
        html_rows.append(
            "<tr>"
            f"<td>{html.escape(str(row['isin']))}</td>"
            f"<td>{html.escape(str(row['fund_name']))}</td>"
            f"<td>{html.escape(str(row['can_trade_now']))}</td>"
            f"<td>{html.escape(str(row['trailer_fee_fixed']))}</td>"
            f"<td>{html.escape(str(row['trailer_fee_pct_mgmt']))}</td>"
            "</tr>"
        )

    # pending rows at bottom, merge cols 2-5 vertically
    if pending_rows:
        rowspan = len(pending_rows)

        for i, row in enumerate(pending_rows):
            if i == 0:
                html_rows.append(
                    "<tr>"
                    f"<td>{html.escape(str(row['isin']))}</td>"
                    f"<td rowspan=\"{rowspan}\" style=\"text-align:center; vertical-align:middle;\">"
                    f"{html.escape(str(row['fund_name']))}"
                    "</td>"
                    f"<td rowspan=\"{rowspan}\" style=\"text-align:center; vertical-align:middle;\">"
                    f"{html.escape(str(row['can_trade_now']))}"
                    "</td>"
                    f"<td rowspan=\"{rowspan}\" style=\"text-align:center; vertical-align:middle;\">"
                    f"{html.escape(str(row['trailer_fee_fixed']))}"
                    "</td>"
                    f"<td rowspan=\"{rowspan}\" style=\"text-align:center; vertical-align:middle;\">"
                    f"{html.escape(str(row['trailer_fee_pct_mgmt']))}"
                    "</td>"
                    "</tr>"
                )
            else:
                html_rows.append(
                    "<tr>"
                    f"<td>{html.escape(str(row['isin']))}</td>"
                    "</tr>"
                )

    return "".join(html_rows)


def build_reply_html(rows: list[dict], has_pending: bool, products_team_email: str) -> str:
    table_rows = _build_html_table_rows(rows)

    ending = (
        '<p>&nbsp;</p>'
        '<p>Pending manual confirmation items will be reverted once confirmed.</p>'
        if has_pending
        else
        f'<p>&nbsp;</p>'
        f'<p>For any queries, please contact the Products Team '
        f'{html.escape(products_team_email)}</p>'
    )

    return f"""\
<html>
  <body>
    <p>Hi,</p>
    <p>Please find below the details:</p>

    <table border="1" cellspacing="0" cellpadding="6" style="border-collapse: collapse;">
      <tr>
        <th>ISIN</th>
        <th>Fund Name</th>
        <th>Can Trade Now?</th>
        <th>Trailer Fee (If Fixed)</th>
        <th>Trailer Fee (If Percentage of Management fee)</th>
      </tr>
      {table_rows}
    </table>

    {ending}
  </body>
</html>
"""


def build_reply_plain(rows: list[dict], has_pending: bool, products_team_email: str) -> str:
    lines = []
    lines.append("Hi,")
    lines.append("")
    lines.append("Please find below the details:")
    lines.append("")
    lines.append(
        "ISIN | Fund Name | Can Trade Now? | Trailer Fee (If Fixed) | Trailer Fee (If Percentage of Management fee)"
    )
    lines.append("-" * 150)

    non_pending_rows = [row for row in rows if not row.get("is_pending")]
    pending_rows = [row for row in rows if row.get("is_pending")]

    for row in non_pending_rows:
        lines.append(
            f"{row['isin']} | {row['fund_name']} | {row['can_trade_now']} | "
            f"{row['trailer_fee_fixed']} | {row['trailer_fee_pct_mgmt']}"
        )

    # plain text cannot really merge cells, so simulate it:
    if pending_rows:
        first = pending_rows[0]
        lines.append(
            f"{first['isin']} | {first['fund_name']} | {first['can_trade_now']} | "
            f"{first['trailer_fee_fixed']} | {first['trailer_fee_pct_mgmt']}"
        )
        for row in pending_rows[1:]:
            lines.append(f"{row['isin']} |  |  |  | ")

    lines.append("")

    if has_pending:
        lines.append("Pending manual confirmation items will be reverted once confirmed.")
    else:
        lines.append(
            f"For any queries, please contact the Products Team {products_team_email}"
        )

    return "\n".join(lines)


def build_internal_forward_html(
    original_from: str,
    original_subject: str,
    original_body: str,
    reply_html: str,
) -> str:
    original_body_escaped = html.escape(original_body).replace("\n", "<br>")

    return f"""\
<html>
  <body>
    <p>Hi,</p>
    <p>Please see below the original incoming email and the auto-reply sent to the sender.</p>

    <p><b>Original incoming email</b></p>
    <p>
      <b>From:</b> {html.escape(original_from)}<br>
      <b>Subject:</b> {html.escape(original_subject)}
    </p>
    <div style="border:1px solid #ccc; padding:10px; margin-bottom:16px;">
      {original_body_escaped}
    </div>

    <p><b>Auto-reply sent</b></p>
    <div style="border:1px solid #ccc; padding:10px;">
      {reply_html}
    </div>
  </body>
</html>
"""
