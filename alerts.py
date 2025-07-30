import requests
import smtplib
from email.message import EmailMessage

def send_discord_alert(message, webhook_url):
    requests.post(webhook_url, json={"content": message})

def send_email_alert(subject, body, to_email, from_email, smtp_server, smtp_port, password):
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = from_email
    msg["To"] = to_email
    msg.set_content(body)

    with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
        server.login(from_email, password)
        server.send_message(msg)