from typing import List, Dict, Any
from app.schemas.sequence import EmailSection, EmailBase
from app.core.config import settings, TIMEZONE
from app.core.exceptions import AppException
from loguru import logger
import openai
import json
from datetime import timedelta, datetime
from tenacity import retry, stop_after_attempt, wait_exponential
from app.core.rate_limiter import openai_limiter
import time

openai.api_key = settings.OPENAI_API_KEY

@openai_limiter
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
async def generate_email_sequence(topic: str, inputs: Dict[str, str], email_structure: List[EmailSection], start_index: int, batch_size: int, days_between_emails: int, buffer_time: timedelta = timedelta(hours=1)) -> List[EmailBase]:
    try:
        sections_prompt = "\n".join([settings.OPENAI_SECTIONS_PROMPT.format(
            index=i+1, 
            name=section.name, 
            description=section.description,
            word_count=section.word_count
        ) for i, section in enumerate(email_structure)])
    
        subject_prompt = settings.OPENAI_SUBJECT_PROMPT.format(subject_index=len(email_structure) + 1)
        
        prompt = settings.OPENAI_EMAIL_PROMPT.format(
            start_index=start_index + 1,
            end_index=start_index + batch_size,
            topic=topic,
            inputs=json.dumps(inputs),
            sections_prompt=sections_prompt,
            subject_prompt=subject_prompt,
            batch_size=batch_size
        )

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
                                "properties": {section.name: {"type": "string"} for section in email_structure}
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
        
        response: openai.ChatCompletion = await openai.ChatCompletion.acreate(
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
            timeout=settings.OPENAI_REQUEST_TIMEOUT
        )
        
        logger.info(f"Received response from OpenAI API for emails {start_index + 1} to {start_index + batch_size}")
        function_call = response.choices[0].message.function_call
        logger.info(f"Function call response:\n{json.dumps(function_call.arguments, indent=2)}")
        
        emails_data = json.loads(function_call.arguments)['emails']
        
        processed_emails = []
        current_date = datetime.now(TIMEZONE) + buffer_time
        for i, email in enumerate(emails_data):
            if 'content' not in email:
                logger.error(f"Missing 'content' key in email {start_index + i + 1}")
                email['content'] = {}
            
            for section in email_structure:
                if section.name not in email['content']:
                    logger.warning(f"Content for {section.name} was not generated in email {start_index + i + 1}")
                    email['content'][section.name] = f"Content for {section.name} was not generated."
            
            if 'subject' not in email:
                logger.error(f"Missing 'subject' key in email {start_index + i + 1}")
                email['subject'] = f"Email {start_index + i + 1}"

            scheduled_for = current_date + timedelta(days=(start_index + i) * days_between_emails)
            
            processed_emails.append(EmailBase(
                subject=email['subject'],
                content=email['content'],
                scheduled_for=scheduled_for
            ))

        logger.info(f"Generated and processed emails {start_index + 1} to {start_index + len(processed_emails)}")
        return processed_emails
    except openai.error.APIError as e:
        logger.error(f"OpenAI API error for batch starting at {start_index}: {str(e)}")
        raise AppException(f"OpenAI API error: {str(e)}", status_code=500)
    except openai.error.Timeout as e:
        logger.error(f"OpenAI API timeout for batch starting at {start_index}: {str(e)}")
        raise AppException(f"OpenAI API timeout: {str(e)}", status_code=504)
    except KeyError as e:
        logger.error(f"KeyError in OpenAI response for batch starting at {start_index}: {str(e)}")
        raise AppException(f"Invalid response structure from OpenAI API: {str(e)}", status_code=500)
    except json.JSONDecodeError as e:
        logger.error(f"JSONDecodeError in OpenAI response for batch starting at {start_index}: {str(e)}")
        raise AppException(f"Invalid JSON in OpenAI API response: {str(e)}", status_code=500)
    except Exception as e:
        logger.error(f"Unexpected error in generate_email_sequence for batch starting at {start_index}: {str(e)}")
        raise AppException(f"Unexpected error: {str(e)}", status_code=500)