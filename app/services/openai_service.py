import openai
from app.core.config import settings
from app.schemas.sequence import EmailContent as EmailBase
from typing import List, Dict
import json
from datetime import datetime, timedelta

openai.api_key = settings.OPENAI_API_KEY

def generate_email_sequence(topic: str, inputs: Dict[str, str]) -> List[EmailBase]:
    sections_prompt = "\n".join([f"{i+1}. {section.name}: {section.description} ({section.word_count} words)" 
                                 for i, section in enumerate(settings.EMAIL_SECTIONS)])
    
    prompt = f"""Generate content for an email sequence about {topic}.
    User inputs: {json.dumps(inputs)}
    
    For each email in the sequence, provide the following sections:
    {sections_prompt}

    Also provide:
    {len(settings.EMAIL_SECTIONS) + 1}. subject: A compelling subject line for the email
    {len(settings.EMAIL_SECTIONS) + 2}. scheduled_for: The scheduled send date (in ISO format)

    Return the result as a JSON array with {settings.SEQUENCE_LENGTH} items."""

    try:
        response = openai.ChatCompletion.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that generates content for email sequences."},
                {"role": "user", "content": prompt}
            ],
            temperature=settings.OPENAI_TEMPERATURE,
            max_tokens=settings.OPENAI_MAX_TOKENS,
            top_p=settings.OPENAI_TOP_P,
            frequency_penalty=settings.OPENAI_FREQUENCY_PENALTY,
            presence_penalty=settings.OPENAI_PRESENCE_PENALTY,
        )
        
        emails_data = json.loads(response.choices[0].message['content'])
        
        # Process and validate the generated data
        processed_emails = []
        current_date = datetime.now()
        for email in emails_data:
            # Ensure all required sections are present
            for section in settings.EMAIL_SECTIONS:
                if section.name not in email['content']:
                    email['content'][section.name] = f"Content for {section.name} was not generated."
            
            # Parse and validate the scheduled_for date
            try:
                scheduled_for = datetime.fromisoformat(email['scheduled_for'])
            except ValueError:
                # If parsing fails, schedule the email for the next day
                current_date += timedelta(days=1)
                scheduled_for = current_date
            
            processed_emails.append(EmailBase(
                subject=email['subject'],
                content=email['content'],
                scheduled_for=scheduled_for
            ))
        
        return processed_emails
    except Exception as e:
        raise Exception(f"Error generating email sequence: {str(e)}")