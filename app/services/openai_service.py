import openai
from app.core.config import settings
from app.schemas.sequence import EmailContent as EmailBase
from typing import List, Dict
from datetime import datetime, timedelta
import json

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

    Return the result as a JSON array with {settings.SEQUENCE_LENGTH} items."""

    # Define the JSON structure we expect
    json_structure = {
        "type": "object",
        "properties": {
            "emails": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "subject": {"type": "string"},
                        "content": {
                            "type": "object",
                            "properties": {section.name: {"type": "string"} for section in settings.EMAIL_SECTIONS}
                        }
                    },
                    "required": ["subject", "content"]
                }
            }
        },
        "required": ["emails"]
    }

    try:
        response = openai.ChatCompletion.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that generates content for email sequences."},
                {"role": "user", "content": prompt}
            ],
            functions=[{
                "name": "generate_email_sequence",
                "description": "Generate an email sequence based on the given topic and inputs",
                "parameters": json_structure
            }],
            function_call={"name": "generate_email_sequence"},
            temperature=settings.OPENAI_TEMPERATURE,
            max_tokens=settings.OPENAI_MAX_TOKENS,
            top_p=settings.OPENAI_TOP_P,
            frequency_penalty=settings.OPENAI_FREQUENCY_PENALTY,
            presence_penalty=settings.OPENAI_PRESENCE_PENALTY,
        )
        
        # Extract the function call result
        function_call = response.choices[0].message.function_call
        emails_data = json.loads(function_call.arguments)['emails']
        
        # Process and validate the generated data
        processed_emails = []
        current_date = datetime.now()
        for i, email in enumerate(emails_data):
            # Ensure all required sections are present
            for section in settings.EMAIL_SECTIONS:
                if section.name not in email['content']:
                    email['content'][section.name] = f"Content for {section.name} was not generated."
            
            # Calculate the scheduled_for date based on the sequence frequency
            scheduled_for = current_date + timedelta(days=i * settings.SEQUENCE_FREQUENCY_DAYS)
            
            processed_emails.append(EmailBase(
                subject=email['subject'],
                content=email['content'],
                scheduled_for=scheduled_for
            ))

        return processed_emails
    except Exception as e:
        raise Exception(f"Error generating email sequence: {str(e)}")