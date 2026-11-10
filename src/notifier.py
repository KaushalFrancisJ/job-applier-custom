"""
Notification & Alert Dispatcher.
Handles urgent Cloudflare/anti-bot alerts and Action Required email notifications.
Supports Gmail SMTP (sending to self) and Windows desktop notification fallbacks.
"""
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import logging
from pathlib import Path
import smtplib
import sys
from typing import Optional

logger = logging.getLogger("notifier")


class AlertNotifier:
    def __init__(self, config: dict):
        self.config = config
        self.notif_cfg = config.get("notifications", {})
        self.email_enabled = self.notif_cfg.get("email_enabled", True)
        self.recipient_email = self.notif_cfg.get("recipient_email", "jkfrancis2003@gmail.com")
        self.sender_email = self.notif_cfg.get("sender_email", "jkfrancis2003@gmail.com")
        self.smtp_host = self.notif_cfg.get("smtp_host", "smtp.gmail.com")
        self.smtp_port = int(self.notif_cfg.get("smtp_port", 587))
        self.app_password = self.notif_cfg.get("smtp_app_password", "").strip()
        self.desktop_alert_enabled = self.notif_cfg.get("desktop_alert_enabled", True)

    def trigger_desktop_alert(self, title: str, message: str):
        """Emits an audible beep and prints a high-visibility terminal banner."""
        try:
            import winsound
            winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
        except Exception:
            sys.stdout.write("\a")
            sys.stdout.flush()

        print("\n" + "!" * 70)
        print(f"🚨 ALERT: {title}")
        print(f"   {message}")
        print("!" * 70 + "\n")

    def send_email(self, subject: str, body_text: str, body_html: Optional[str] = None) -> bool:
        """
        Sends email via Gmail SMTP to self.
        Requires a 16-character Google App Password.
        """
        if not self.email_enabled:
            return False

        if not self.app_password:
            logger.warning(
                "[Notifier] smtp_app_password is not set in config.json. "
                "To enable email alerts, generate an App Password at: https://myaccount.google.com/apppasswords"
            )
            return False

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"Job Applier Watcher <{self.sender_email}>"
            msg["To"] = self.recipient_email
            msg["Date"] = datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0530")

            part1 = MIMEText(body_text, "plain", "utf-8")
            msg.attach(part1)

            if body_html:
                part2 = MIMEText(body_html, "html", "utf-8")
                msg.attach(part2)

            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=15) as server:
                server.starttls()
                server.login(self.sender_email, self.app_password)
                server.sendmail(self.sender_email, [self.recipient_email], msg.as_string())

            logger.info(f"[Notifier] Email successfully sent to {self.recipient_email}: {subject}")
            return True
        except Exception as e:
            logger.error(f"[Notifier] Failed to send email alert: {e}")
            return False

    def notify_cloudflare_challenge(self, platform: str, url: str):
        """Triggers immediate notification when Cloudflare / Bot verification is encountered."""
        subject = f"🚨 [Job Applier Alert] Cloudflare Verification Needed on {platform.capitalize()}"
        
        text_body = (
            f"Hello Kaushal,\n\n"
            f"The Job Applier Watcher encountered a Cloudflare or Bot challenge on {platform.capitalize()}.\n\n"
            f"Details:\n"
            f"• Platform: {platform.capitalize()}\n"
            f"• URL: {url}\n"
            f"• Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S IST')}\n\n"
            f"Action Required:\n"
            f"1. Open your browser or run open_browser.bat.\n"
            f"2. Complete the 'Verify you are human' / Cloudflare challenge.\n"
            f"3. The automated watcher will resume immediately.\n\n"
            f"Best regards,\nYour Job Applier Watcher"
        )

        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; border: 1px solid #e0e0e0; border-radius: 8px; padding: 20px;">
                <h2 style="color: #d93025; margin-top: 0;">🚨 Cloudflare Verification Detected</h2>
                <p>The automated job watcher was challenged by Cloudflare on <strong>{platform.capitalize()}</strong>.</p>
                
                <div style="background-color: #f8f9fa; border-left: 4px solid #d93025; padding: 12px; margin: 16px 0;">
                    <p style="margin: 0;"><strong>URL:</strong> <a href="{url}">{url}</a></p>
                    <p style="margin: 4px 0 0 0;"><strong>Timestamp:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S IST')}</p>
                </div>
                
                <h3>Quick Action Steps:</h3>
                <ol>
                    <li>Open <code>open_browser.bat</code> or launch your logged-in Chrome session.</li>
                    <li>Solve the Cloudflare / verification challenge.</li>
                    <li>The automated watcher will automatically continue.</li>
                </ol>
            </div>
        </body>
        </html>
        """

        # 1. Local desktop alert
        if self.desktop_alert_enabled:
            self.trigger_desktop_alert(
                f"Cloudflare Challenge on {platform.capitalize()}",
                f"Please open your browser and verify: {url}"
            )

        # 2. Email alert
        self.send_email(subject, text_body, html_body)

    def notify_action_required(self, company: str, title: str, url: str, reason: str, match_score: float = 0.0):
        """Sends notification when a high-match JD requires manual steps or external application."""
        subject = f"⚠️ [Action Required] {company} — {title} ({match_score:.0f}% Match)"
        
        text_body = (
            f"Hello Kaushal,\n\n"
            f"A high-match job opportunity requires your manual action or external application.\n\n"
            f"• Role: {title}\n"
            f"• Company: {company}\n"
            f"• Match Score: {match_score:.0f}%\n"
            f"• Reason: {reason}\n"
            f"• Application Link: {url}\n\n"
            f"Best regards,\nYour Job Applier Watcher"
        )

        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; border: 1px solid #e0e0e0; border-radius: 8px; padding: 20px;">
                <h2 style="color: #f2994a; margin-top: 0;">⚠️ Action Required: {company}</h2>
                <p>A role matching your ₹10 LPA+ criteria and background was found:</p>
                
                <table style="width: 100%; border-collapse: collapse; margin: 16px 0;">
                    <tr><td style="padding: 6px; font-weight: bold; width: 30%;">Role:</td><td style="padding: 6px;">{title}</td></tr>
                    <tr><td style="padding: 6px; font-weight: bold;">Company:</td><td style="padding: 6px;">{company}</td></tr>
                    <tr><td style="padding: 6px; font-weight: bold;">Match:</td><td style="padding: 6px;">{match_score:.0f}%</td></tr>
                    <tr><td style="padding: 6px; font-weight: bold;">Notes:</td><td style="padding: 6px; color: #d93025;">{reason}</td></tr>
                </table>
                
                <p><a href="{url}" style="display: inline-block; background-color: #1a73e8; color: white; padding: 10px 18px; text-decoration: none; border-radius: 4px; font-weight: bold;">View & Apply Now</a></p>
            </div>
        </body>
        </html>
        """

        self.send_email(subject, text_body, html_body)
