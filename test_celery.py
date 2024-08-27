from app.tasks import send_scheduled_emails
from app.db.database import SessionLocal
from app.models.email import Email
from app.models.sequence import Sequence
from datetime import datetime, timedelta, timezone
import time

def test_send_scheduled_emails():
    db = SessionLocal()
    try:
        # Create a test sequence and email
        sequence = Sequence(topic="Test Topic", inputs={}, recipient_email="chrisgscott@gmail.com")
        db.add(sequence)
        db.commit()

        email = Email(
            sequence_id=sequence.id,
            subject="Test Email from Celery",
            content={
                "intro_content": "This is a test email sent by Celery.",
                "week_task": "Your task is to verify this email was sent.",
                "quick_tip": "Check your inbox and the Brevo interface.",
                "cta": "If you received this, the setup is working!"
            },
            scheduled_for=datetime.now(timezone.utc) - timedelta(minutes=1)  # Schedule it for 1 minute ago
        )
        db.add(email)
        db.commit()

        # Call the task directly
        print("Calling send_scheduled_emails task...")
        send_scheduled_emails()

        print("Task called. Waiting for 5 seconds...")
        time.sleep(5)  # Wait for 5 seconds

        # Check if the email was marked as sent
        db.refresh(email)
        if email.sent:
            print("Email was marked as sent in the database.")
        else:
            print("Email was not marked as sent in the database.")

    finally:
        db.close()

if __name__ == "__main__":
    test_send_scheduled_emails()