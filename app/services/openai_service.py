import openai
from app.core.config import settings
from app.schemas.sequence import EmailContent as EmailBase
from typing import List, Dict
from datetime import datetime, timedelta
import json
from tenacity import retry, stop_after_attempt, wait_exponential

openai.api_key = settings.OPENAI_API_KEY

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def generate_email_sequence(topic: str, inputs: Dict[str, str], batch_size: int = 5) -> List[EmailBase]:
    sections_prompt = "\n".join([f"{i+1}. {section.name}: {section.description} ({section.word_count} words)" 
                                 for i, section in enumerate(settings.EMAIL_SECTIONS)])
    
    all_emails = []
    current_date = datetime.now()
    
    for batch_start in range(0, settings.SEQUENCE_LENGTH, batch_size):
        batch_end = min(batch_start + batch_size, settings.SEQUENCE_LENGTH)
        
        prompt = f"""Generate content for emails {batch_start + 1} to {batch_end} in an email sequence about {topic}.
        User inputs: {json.dumps(inputs)}
        
        For each email in the sequence, provide the following sections:
        {sections_prompt}
        
        Also provide:
        {len(settings.EMAIL_SECTIONS) + 1}. subject: A compelling subject line for the email
        
        Return the result as a JSON array with {batch_end - batch_start} items."""
        
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
                timeout=60
            )
            
            function_call = response.choices[0].message.function_call
            emails_data = json.loads(function_call.arguments)['emails']
            
            for i, email in enumerate(emails_data):
                for section in settings.EMAIL_SECTIONS:
                    if section.name not in email['content']:
                        email['content'][section.name] = f"Content for {section.name} was not generated."
                
                scheduled_for = current_date + timedelta(days=(batch_start + i) * settings.SEQUENCE_FREQUENCY_DAYS)
                
                all_emails.append(EmailBase(
                    subject=email['subject'],
                    content=email['content'],
                    scheduled_for=scheduled_for
                ))
            
            logger.info(f"Generated emails {batch_start + 1} to {batch_end} out of {settings.SEQUENCE_LENGTH}")
        
        except openai.error.Timeout:
            logger.error("OpenAI API request timed out")
            raise HTTPException(status_code=504, detail="OpenAI API request timed out")
        except Exception as e:
            logger.error(f"Error in generate_email_sequence batch {batch_start + 1} to {batch_end}: {str(e)}")
            raise
    
    return all_emails