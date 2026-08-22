import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import markdown

from .config_loader import env

EMAIL_TEMPLATE = """<!DOCTYPE html>
<html>
<body style="margin:0;padding:0;background:#f4f4f7;font-family:Arial,Helvetica,sans-serif;">
  <table role="presentation" width="100%%" cellpadding="0" cellspacing="0" style="background:#f4f4f7;padding:24px 0;">
    <tr><td align="center">
      <table role="presentation" width="640" cellpadding="0" cellspacing="0"
             style="background:#ffffff;border-radius:8px;overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,0.08);">
        <tr>
          <td style="background:#1a1a2e;color:#ffffff;padding:20px 32px;">
            <h1 style="margin:0;font-size:20px;">📄 Daily Research Digest</h1>
            <p style="margin:4px 0 0;font-size:13px;color:#a0a0c0;">{domain} &middot; {date}</p>
          </td>
        </tr>
        <tr>
          <td style="padding:24px 32px;">
            <h2 style="margin:0 0 4px;font-size:18px;line-height:1.3;color:#111;">{title}</h2>
            <p style="margin:0 0 16px;font-size:12px;color:#666;">{authors}</p>
            <div style="font-size:14px;line-height:1.65;color:#333;">
              {body}
            </div>
            <p style="margin:24px 0 0;font-size:13px;">
              🔗 <a href="{url}" style="color:#4361ee;">Read the full paper on arXiv</a>
              &nbsp;&middot;&nbsp;
              <a href="{pdf_url}" style="color:#4361ee;">PDF</a>
            </p>
          </td>
        </tr>
        <tr>
          <td style="background:#fafafa;border-top:1px solid #eee;padding:14px 32px;font-size:11px;color:#999;">
            Curated automatically by your research digest agent &middot; Powered by arXiv + OpenRouter
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""


def render_html(paper, breakdown_md, domain_name):
    body = markdown.markdown(
        breakdown_md, extensions=["extra", "sane_lists"]
    )
    date = paper.published.strftime("%d %b %Y") if paper.published else ""
    return EMAIL_TEMPLATE.format(
        domain=domain_name,
        date=date,
        title=paper.title,
        authors=", ".join(paper.authors[:6]) + (" et al." if len(paper.authors) > 6 else ""),
        body=body,
        url=paper.url,
        pdf_url=paper.pdf_url,
    )


def send_email(to_address, subject, html_body):
    smtp_host = "smtp.gmail.com"
    smtp_port = 465
    from_addr = env("GMAIL_ADDRESS", required=True)
    password = env("GMAIL_APP_PASSWORD", required=True)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"Research Digest <{from_addr}>"
    msg["To"] = to_address
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    with smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=30) as server:
        server.login(from_addr, password)
        server.sendmail(from_addr, [to_address], msg.as_string())
