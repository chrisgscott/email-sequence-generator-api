import openai
from app.core.config import settings, TIMEZONE
from app.schemas.sequence import EmailContent as EmailBase
from typing import List, Dict
from datetime import datetime, timedelta
import json
from tenacity import retry, stop_after_attempt, wait_exponential
from app.core.exceptions import AppException
import time
import logging

logger = logging.getLogger(__name__)

openai.api_key = settings.OPENAI_API_KEY

class RateLimiter:
    def __init__(self, max_calls, period):
        self.max_calls = max_calls
        self.period = period
        self.calls = []

    def __call__(self, func):
        def wrapper(*args, **kwargs):
            now = time.time()
            self.calls = [call for call in self.calls if call > now - self.period]
            if len(self.calls) >= self.max_calls:
                sleep_time = self.calls[0] - (now - self.period)
                time.sleep(sleep_time)
            self.calls.append(time.time())
            return func(*args, **kwargs)
        return wrapper

# Assuming 60 calls per minute for OpenAI API
openai_limiter = RateLimiter(max_calls=60, period=60)

@openai_limiter
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def generate_email_sequence(topic: str, inputs: Dict[str, str], start_index: int, batch_size: int) -> List[EmailBase]:
    logger.info(f"Generating email sequence for topic: {topic}, start_index: {start_index}, batch_size: {batch_size}")
    sections_prompt = "\n".join([f"{i+1}. {section.name}: {section.description} ({section.word_count} words)" 
                                 for i, section in enumerate(settings.EMAIL_SECTIONS)])
    
    prompt = f"""Generate content for emails {start_index + 1} to {start_index + batch_size} in an email sequence about {topic}.
    User inputs: {json.dumps(inputs)}
    
    For each email in the sequence, provide the following sections:
    {sections_prompt}
    
    Also provide:
    {len(settings.EMAIL_SECTIONS) + 1}. subject: A compelling subject line for the email
    
    Return the result as a JSON array with {batch_size} items."""
    
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
    
    logger.info(f"Sending request to OpenAI API for emails {start_index + 1} to {start_index + batch_size}")
    logger.info(f"Full prompt being sent to OpenAI:\n{prompt}")
    logger.info(f"JSON structure for function call:\n{json.dumps(json_structure, indent=2)}")
    
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
            timeout=180  # Increase timeout to 3 minutes
        )
        
        logger.info(f"Received response from OpenAI API for emails {start_index + 1} to {start_index + batch_size}")
        function_call = response.choices[0].message.function_call
        logger.info(f"Function call response:\n{json.dumps(function_call.arguments, indent=2)}")
        
        emails_data = json.loads(function_call.arguments)['emails']
        
        processed_emails = []
        current_date = datetime.now(TIMEZONE)
        for i, email in enumerate(emails_data):
            for section in settings.EMAIL_SECTIONS:
                if section.name not in email['content']:
                    logger.warning(f"Content for {section.name} was not generated in email {start_index + i + 1}")
                    email['content'][section.name] = f"Content for {section.name} was not generated."
            
            scheduled_for = current_date + timedelta(days=(start_index + i) * settings.SEQUENCE_FREQUENCY_DAYS)
            
            processed_emails.append(EmailBase(
                subject=email['subject'],
                content=email['content'],
                scheduled_for=scheduled_for
            ))
        
        logger.info(f"Generated and processed emails {start_index + 1} to {start_index + len(processed_emails)} out of {settings.SEQUENCE_LENGTH}")
        return processed_emails
    except openai.error.Timeout:
        logger.error(f"OpenAI API request timed out for batch starting at {start_index}")
        raise AppException("OpenAI API request timed out", status_code=504)
    except openai.error.APIError as e:
        logger.error(f"OpenAI API error for batch starting at {start_index}: {str(e)}")
        raise AppException(f"OpenAI API error: {str(e)}", status_code=500)
    except openai.error.RateLimitError as e:
        logger.error(f"OpenAI API rate limit exceeded for batch starting at {start_index}: {str(e)}")
        raise AppException("OpenAI API rate limit exceeded. Please try again later.", status_code=429)
    except Exception as e:
        logger.error(f"Unexpected error in generate_email_sequence for batch starting at {start_index}: {str(e)}")
        raise AppException(f"Unexpected error: {str(e)}", status_code=500)