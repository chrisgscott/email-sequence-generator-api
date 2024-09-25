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
from zoneinfo import ZoneInfo
from functools import lru_cache, wraps
from cachetools import TTLCache
import asyncio
import sentry_sdk
from app.utils.content_formatter import format_content
from app.services.pexels_service import get_image_for_tags
from app.models.email import EmailBase  

openai.api_key = settings.OPENAI_API_KEY

@openai_limiter
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
async def generate_email_sequence(topic: str, inputs: Dict[str, str], email_structure: List[EmailSection], start_index: int, batch_size: int, days_between_emails: int, buffer_time: timedelta = timedelta(minutes=1), previous_topics: Dict[str, int] = {}, topic_depth: int = 5, start_date: datetime = None) -> List[EmailBase]:
    try:
        sections_prompt = "\n".join([settings.OPENAI_SECTIONS_PROMPT.format(
            index=i+1, 
            name=section.name, 
            description=section.description,
            word_count=section.word_count if isinstance(section.word_count, str) else f"{section.word_count}"
        ) for i, section in enumerate(email_structure)])
    
        subject_prompt = settings.OPENAI_SUBJECT_PROMPT.format(subject_index=len(email_structure) + 1)
        
        previous_topics_str = "\n".join([f"- {topic} (covered {depth} time{'s' if depth > 1 else ''})" for topic, depth in previous_topics.items()])
        
        depth_instruction = f"Depth setting: {topic_depth}/10. "
        if topic_depth < 4:
            depth_instruction += "Focus on broad topics without repeating any topics across emails."
        elif topic_depth < 7:
            depth_instruction += "Balance between broad topics and some deeper dives into subtopics."
        else:
            depth_instruction += "Focus on a specific, deep facet of the core topic in each email. Dive into detailed subtopics, avoiding repetition across the sequence. This approach ensures comprehensive coverage of the subject while maintaining uniqueness in each email."

        prompt = settings.OPENAI_EMAIL_PROMPT.format(
            start_index=start_index + 1,
            end_index=start_index + batch_size,
            topic=topic,
            inputs=json.dumps(inputs),
            sections_prompt=sections_prompt,
            subject_prompt=subject_prompt,
            batch_size=batch_size,
            previous_topics=previous_topics_str,
            depth_instruction=depth_instruction
        )

        prompt += "\n\nFor each email, please include a 'category' field with a single category related to the email, and a 'tags' field with 3-5 tags related to the email. These will be used for blog post metadata."

        prompt += """
For lists, use the following Markdown syntax:
- For unordered lists, use a hyphen followed by a space (- ) at the beginning of each list item.
- For ordered lists, use a number followed by a period and a space (1. ) at the beginning of each list item.
Ensure there's an empty line before and after each list.
"""

        json_structure = {
            "type": "object",
            "properties": {
                "emails": {
                    "type": "array",
                    "description": "An array of email objects",
                    "items": {
                        "type": "object",
                        "properties": {
                            "subject": {
                                "type": "string",
                                "description": "The subject line of the email"
                            },
                            "content": {
                                "type": "object",
                                "properties": {
                                    section.name: {
                                        "type": "string",
                                        "description": f"Content for the '{section.name}' section"
                                    } for section in email_structure
                                },
                                "required": [section.name for section in email_structure]
                            },
                            "category": {
                                "type": "string",
                                "description": "A single category related to this email to be used in a blog post"
                            },
                            "tags": {
                                "type": "array",
                                "items": {
                                    "type": "string"
                                },
                                "minItems": 3,
                                "maxItems": 5,
                                "description": "3-5 tags related to this email to be used in a blog post"
                            }
                        },
                        "required": ["subject", "content", "category", "tags"]
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
                "parameters": json_structure,
                "examples": [
                    {
                        "emails": [
                            {
                                "subject": "Exciting Pet Training Tip for Your Lab!",
                                "content": {
                                    "This weeks' training tip": "## This Week's Training Tip\n\nThis week, we're focusing on teaching your Labrador to 'stay'. This command is crucial for your dog's safety and obedience.",
                                    "How you'll teach this": "### How to Teach 'Stay'\n\n1. Start with your dog in a sitting position.\n2. Hold your hand out, palm facing the dog, and say 'stay'.\n3. Take a step back.\n4. If your dog stays, immediately reward them with a treat and praise.\n5. Gradually increase the distance and duration.",
                                    "Things to consider": "### Things to Consider\n\nRemember, Labradors are energetic breeds. Ensure you've exercised your dog before training sessions to help them focus better.",
                                    "If it's not going well": "### Troubleshooting\n\nIf your Labrador is struggling with 'stay', try reducing distractions in the environment. Start in a quiet room before moving to more challenging locations.",
                                    "CTA": "**Share your 'stay' training progress with us! We'd love to hear how it's going.**"
                                },
                                "category": "Pet Training",
                                "tags": ["Labrador", "Training", "Behavior", "Obedience", "Safety"]
                            }
                        ]
                    }
                ]
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
        
        try:
            emails_data = json.loads(function_call.arguments)['emails']
        except json.JSONDecodeError as e:
            logger.error(f"JSONDecodeError in OpenAI response: {str(e)}")
            logger.error(f"Raw response: {function_call.arguments}")
            raise AppException(f"Invalid JSON in OpenAI API response: {str(e)}", status_code=500)
        except KeyError as e:
            logger.error(f"KeyError in OpenAI response: {str(e)}")
            logger.error(f"Parsed response: {json.loads(function_call.arguments)}")
            raise AppException(f"Missing 'emails' key in OpenAI API response", status_code=500)

        processed_emails = []
        current_date = start_date if start_date else datetime.now(TIMEZONE) + buffer_time
        for i, email_data in enumerate(emails_data):
            try:
                content = {section.name: format_content(email_data['content'].get(section.name, '')) for section in email_structure}
                
                # Fetch image information
                image_info = await get_image_for_tags(email_data['tags'], orientation="landscape")
                logger.info(f"Fetched image info for email {start_index + i + 1}: {image_info}")
                
                email = EmailBase(
                    subject=email_data['subject'],
                    content=content,
                    category=email_data['category'],
                    tags=email_data['tags'],
                    image_url=image_info['image_url'] if image_info else None,
                    photographer=image_info['photographer'] if image_info else None,
                    pexels_url=image_info['pexels_url'] if image_info else None,
                    scheduled_for=current_date + timedelta(days=i * days_between_emails)
                )
                logger.debug(f"Created EmailBase object: {email.dict()}")  # Add this debug log
                processed_emails.append(email)
            except Exception as e:
                logger.error(f"Error creating EmailBase object: {str(e)}")
                raise

        logger.info(f"Generated and processed emails {start_index + 1} to {start_index + len(processed_emails)}")
        return processed_emails
    except openai.error.APIError as e:
        sentry_sdk.capture_exception(e)
        logger.error(f"OpenAI API error for batch starting at {start_index}: {str(e)}")
        raise AppException(f"OpenAI API error: {str(e)}", status_code=500)
    except openai.error.Timeout as e:
        sentry_sdk.capture_exception(e)
        logger.error(f"OpenAI API timeout for batch starting at {start_index}: {str(e)}")
        raise AppException(f"OpenAI API timeout: {str(e)}", status_code=504)
    except openai.error.RateLimitError as e:
        sentry_sdk.capture_exception(e)
        logger.error(f"OpenAI API rate limit exceeded for batch starting at {start_index}: {str(e)}")
        raise AppException(f"OpenAI API rate limit exceeded: {str(e)}", status_code=429)
    except Exception as e:
        sentry_sdk.capture_exception(e)
        logger.error(f"Unexpected error in generate_email_sequence for batch starting at {start_index}: {str(e)}")
        raise AppException(f"Unexpected error: {str(e)}", status_code=500)

def validate_email_content(email, email_structure):
    for section in email_structure:
        if section.name not in email['content'] or not email['content'][section.name].strip():
            return False
    return 'subject' in email and email['subject'].strip()

# Create a cache with a maximum of 100 items and a 5-minute TTL
cache = TTLCache(maxsize=100, ttl=300)

def async_lru_cache(maxsize=100, ttl=300):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            key = str(args) + str(kwargs)
            if key in cache:
                return cache[key]
            result = await func(*args, **kwargs)
            cache[key] = result
            return result
        return wrapper
    return decorator

@async_lru_cache(maxsize=100, ttl=300)
async def cached_generate_demo_prompt(interests: str, goals: str) -> Dict[str, str]:
    return await generate_demo_prompt(interests, goals)

async def generate_demo_prompt(interests: str, goals: str) -> Dict[str, str]:
    prompt = f"""Generate a single email for a journal prompt sequence. The email must be tailored to the user's interests and goals, but only focus on just one or two specific aspects of their interests and goals rather than trying to cover everything they've mentioned in a single journal prompt.
Interests: {interests}
Goals: {goals}

Provide:
1. journal_prompt: A specific, actionable prompt for today's journal entry that incorporates just one or two of their stated interests and goals. Try not to always start with the words 'Reflect on...' (50-100 words)
2. wrap_up: A brief, encouraging wrap-up (20-30 words)

Return the result as a JSON object."""

    json_structure = {
        "type": "object",
        "properties": {
            "journal_prompt": {"type": "string"},
            "wrap_up": {"type": "string"}
        },
        "required": ["journal_prompt", "wrap_up"]
    }

    response = await openai.ChatCompletion.acreate(
        model=settings.OPENAI_MODEL,
        messages=[
            {"role": "system", "content": "You are a helpful assistant that generates journal prompts."},
            {"role": "user", "content": prompt}
        ],
        functions=[{
            "name": "generate_demo_prompt",
            "description": "Generate a demo journal prompt",
            "parameters": json_structure
        }],
        function_call={"name": "generate_demo_prompt"},
        temperature=0.7,
        max_tokens=300
    )

    if hasattr(response.choices[0].message, 'function_call'):
        return json.loads(response.choices[0].message.function_call.arguments)
    else:
        # If function_call is not present, try to parse the content directly
        content = response.choices[0].message.content
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # If parsing fails, return a default response
            return {
                "journal_prompt": "We couldn't generate a specific prompt. Write about your day and reflect on your progress towards your goals.",
                "wrap_up": "Keep pushing forward. Every step counts!"
            }
