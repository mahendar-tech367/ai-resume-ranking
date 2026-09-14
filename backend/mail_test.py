import os
from dotenv import load_dotenv
import smtplib

load_dotenv()

server = smtplib.SMTP(
    os.getenv("MAIL_SERVER"),
    int(os.getenv("MAIL_PORT"))
)

server.starttls()

server.login(
    os.getenv("MAIL_USERNAME"),
    os.getenv("MAIL_PASSWORD")
)

print("Mailjet SMTP login successful!")

server.quit()