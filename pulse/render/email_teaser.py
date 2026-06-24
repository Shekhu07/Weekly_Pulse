"""Email teaser builder — Phase 3.

Builds a short stakeholder notification email with theme
headlines and a deep link to the Google Doc section.

Output: EmailTeaser with subject, html_body, text_body, recipients.
"""

from __future__ import annotations

import html as html_lib
from datetime import datetime, timezone

from pulse.ingestion.models import EmailTeaser, PulseReport, RunContext


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def build_email_teaser(
    report: PulseReport,
    run_context: RunContext,
    doc_url: str = "",
) -> EmailTeaser:
    """Build an email teaser from a PulseReport.

    Email structure:
        Subject: {Product} Weekly Review Pulse — {iso_week}
        Body: 3–5 bullet theme headlines + one-line context
        CTA: Read full report → {doc_url}
        Footer: timestamp, window, doc link

    Args:
        report: Completed pulse analysis report.
        run_context: Current run parameters.
        doc_url: URL to the Doc section (from Docs MCP). May be empty
                 when building a preview before Phase 4 runs.

    Returns:
        EmailTeaser with subject, html_body, text_body, recipients.
    """
    display_name = run_context.product.capitalize()
    subject = f"{display_name} Weekly Review Pulse — {run_context.iso_week}"
    idempotency_key = f"{run_context.product}-{run_context.iso_week}-email"

    # Generation timestamp
    try:
        gen_dt = datetime.fromisoformat(report.generated_at.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        gen_dt = datetime.now(timezone.utc)
    gen_str = gen_dt.strftime("%Y-%m-%d %H:%M IST")

    # Use up to 5 themes for the email body
    top_themes = report.themes[:5]

    cta_url = doc_url or "#"
    cta_label = "Read full report →"

    # ── Plain-text body ───────────────────────────────────────────────────────
    text_body = _build_text_body(
        display_name=display_name,
        iso_week=run_context.iso_week,
        window_weeks=report.window_weeks,
        review_count=report.review_count,
        top_themes=top_themes,
        cta_url=cta_url,
        cta_label=cta_label,
        gen_str=gen_str,
        doc_url=doc_url,
    )

    # ── HTML body ─────────────────────────────────────────────────────────────
    html_body = _build_html_body(
        display_name=display_name,
        iso_week=run_context.iso_week,
        window_weeks=report.window_weeks,
        review_count=report.review_count,
        top_themes=top_themes,
        cta_url=cta_url,
        cta_label=cta_label,
        gen_str=gen_str,
        doc_url=doc_url,
    )

    return EmailTeaser(
        subject=subject,
        html_body=html_body,
        text_body=text_body,
        recipients=[],          # populated by delivery layer from product config
        idempotency_key=idempotency_key,
    )


# ---------------------------------------------------------------------------
# Plain-text renderer
# ---------------------------------------------------------------------------


def _build_text_body(
    *,
    display_name: str,
    iso_week: str,
    window_weeks: int,
    review_count: int,
    top_themes: list,
    cta_url: str,
    cta_label: str,
    gen_str: str,
    doc_url: str,
) -> str:
    lines: list[str] = []

    lines.append(f"{display_name} Weekly Review Pulse — {iso_week}")
    lines.append("=" * 50)
    lines.append("")
    lines.append(
        f"Here are this week's top themes from {review_count} Play Store reviews "
        f"(rolling {window_weeks}-week window):"
    )
    lines.append("")

    if top_themes:
        for i, theme in enumerate(top_themes, 1):
            lines.append(f"  {i}. {theme.theme_name}")
            lines.append(f"     {theme.summary}")
            lines.append("")
    else:
        lines.append("  No themes identified this week.")
        lines.append("")

    lines.append("-" * 50)
    lines.append(f"{cta_label}  {cta_url}")
    lines.append("-" * 50)
    lines.append("")
    lines.append(f"Generated: {gen_str}")
    lines.append(f"Review window: Last {window_weeks} weeks · Source: Google Play Store")
    if doc_url:
        lines.append(f"Full report: {doc_url}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# HTML renderer
# ---------------------------------------------------------------------------


def _build_html_body(
    *,
    display_name: str,
    iso_week: str,
    window_weeks: int,
    review_count: int,
    top_themes: list,
    cta_url: str,
    cta_label: str,
    gen_str: str,
    doc_url: str,
) -> str:
    def esc(s: str) -> str:
        return html_lib.escape(str(s))

    theme_bullets = ""
    if top_themes:
        items = ""
        for theme in top_themes:
            items += (
                f"<li style='margin-bottom:10px;'>"
                f"<strong>{esc(theme.theme_name)}</strong><br>"
                f"<span style='color:#555;'>{esc(theme.summary)}</span>"
                f"</li>"
            )
        theme_bullets = f"<ul style='padding-left:20px;'>{items}</ul>"
    else:
        theme_bullets = "<p style='color:#777;'>No themes identified this week.</p>"

    cta_section = (
        f"<p style='margin:24px 0;'>"
        f"<a href='{esc(cta_url)}' "
        f"style='background:#1a73e8;color:#fff;padding:12px 24px;"
        f"border-radius:6px;text-decoration:none;font-weight:bold;'>"
        f"{esc(cta_label)}</a></p>"
    )

    footer_doc_link = ""
    if doc_url:
        footer_doc_link = (
            f" · <a href='{esc(doc_url)}' style='color:#888;'>Full report</a>"
        )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{esc(display_name)} Weekly Review Pulse — {esc(iso_week)}</title>
</head>
<body style="margin:0;padding:0;background:#f5f5f5;font-family:Arial,Helvetica,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f5f5f5;padding:32px 0;">
    <tr>
      <td align="center">
        <table width="600" cellpadding="0" cellspacing="0"
               style="background:#ffffff;border-radius:8px;overflow:hidden;
                      box-shadow:0 2px 8px rgba(0,0,0,.08);">

          <!-- Header -->
          <tr>
            <td style="background:#1a73e8;padding:28px 32px;">
              <h1 style="margin:0;color:#fff;font-size:20px;font-weight:700;">
                {esc(display_name)} Weekly Review Pulse
              </h1>
              <p style="margin:6px 0 0;color:#d0e4ff;font-size:14px;">{esc(iso_week)}</p>
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td style="padding:28px 32px;">
              <p style="margin:0 0 16px;color:#333;font-size:15px;">
                Here are this week's top themes from
                <strong>{esc(str(review_count))} Play Store reviews</strong>
                (rolling {esc(str(window_weeks))}-week window):
              </p>

              {theme_bullets}

              {cta_section}
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="background:#f9f9f9;padding:16px 32px;border-top:1px solid #eee;">
              <p style="margin:0;color:#999;font-size:12px;">
                Generated: {esc(gen_str)} ·
                Review window: Last {esc(str(window_weeks))} weeks ·
                Source: Google Play Store{footer_doc_link}
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""

    return html
