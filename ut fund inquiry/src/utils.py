import html


def _preserve_value(value) -> str:
    if value is None:
        return ""
    return str(value).strip()


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
                    "trailer_fee": "-",
                    "can_trade_now": "-",
                }
            )
            has_pending = True
            continue

        # ISIN found in masterlist
        fund_name_raw = detail.get("fund_name", "")
        trailer_fee_raw = detail.get("trailer_fee", "")

        fund_name = _preserve_value(fund_name_raw)
        trailer_fee = _preserve_value(trailer_fee_raw)

        rows.append(
            {
                "isin": isin,
                "fund_name": fund_name,
                "trailer_fee": trailer_fee,
                "can_trade_now": "Yes",
            }
        )

    if not rows:
        rows.append(
            {
                "isin": "No valid ISIN detected",
                "fund_name": "Pending manual confirmation",
                "trailer_fee": "-",
                "can_trade_now": "-",
            }
        )
        has_pending = True

    return rows, has_pending


def build_reply_html(rows: list[dict], has_pending: bool, products_team_email: str) -> str:
    table_rows = []
    for row in rows:
        table_rows.append(
            "<tr>"
            f"<td>{html.escape(str(row['isin']))}</td>"
            f"<td>{html.escape(str(row['fund_name']))}</td>"
            f"<td>{html.escape(str(row['trailer_fee']))}</td>"
            f"<td>{html.escape(str(row['can_trade_now']))}</td>"
            "</tr>"
        )

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
        <th>Trailer Fee</th>
        <th>Can Trade Now?</th>
      </tr>
      {''.join(table_rows)}
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
    lines.append("ISIN | Fund Name | Trailer Fee | Can Trade Now?")
    lines.append("-" * 90)

    for row in rows:
        lines.append(
            f"{row['isin']} | {row['fund_name']} | {row['trailer_fee']} | {row['can_trade_now']}"
        )

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