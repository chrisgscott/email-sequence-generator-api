import requests
from app.core.config import settings
import re
from app.models.api_key import APIKey
from loguru import logger
from typing import Dict, List
from app.core.exceptions import AppException
from app.schemas.sequence import EmailSection

def create_blog_post(content: Dict[str, str], metadata: dict, api_key: APIKey) -> str:
    # Content filtering is temporarily disabled
    # for section_content in content.values():
    #     if filter_content(section_content):
    #         return "Content flagged as potentially inappropriate"
    
    # Create WordPress post
    post_data = {
        'title': metadata['title'],
        'status': 'draft',
        'categories': [get_category_id(api_key, metadata['category'])],
        'tags': get_tag_ids(api_key, metadata['tags']),
        'content': '',  # Leave the content empty
    }

    # Add custom fields
    if 'custom_fields' in metadata:
        post_data['meta'] = metadata['custom_fields']
        logger.info(f"Custom fields being sent: {metadata['custom_fields']}")

    # Post to WordPress
    url = f"{api_key.wordpress_url}/wp-json/wp/v2/{metadata['custom_post_type']}"
    auth = (api_key.wordpress_username, api_key.wordpress_app_password)
    
    logger.info(f"Attempting to create blog post with data: {post_data}")

    try:
        response = requests.post(url, json=post_data, auth=auth)
        response.raise_for_status()
        post_id = response.json()['id']
        logger.info(f"Blog post created successfully. Response: {response.text}")
        return f"Blog post created with ID: {post_id} (in draft status for review)"
    except requests.RequestException as e:
        logger.error(f"Failed to create blog post: {str(e)}")
        logger.error(f"Response content: {e.response.text if e.response else 'No response content'}")
        return f"Failed to create blog post: {str(e)}"

def get_category_id(api_key: APIKey, category_name: str) -> int:
    url = f"{api_key.wordpress_url}/wp-json/wp/v2/categories"
    auth = (api_key.wordpress_username, api_key.wordpress_app_password)
    
    try:
        response = requests.get(url, auth=auth, params={'search': category_name})
        response.raise_for_status()
        categories = response.json()
        if categories:
            return categories[0]['id']
        else:
            # Create new category if it doesn't exist
            new_category = requests.post(url, auth=auth, json={'name': category_name})
            new_category.raise_for_status()
            return new_category.json()['id']
    except requests.RequestException as e:
        logger.error(f"Failed to get or create category: {str(e)}")
        return None

def get_tag_ids(api_key: APIKey, tag_names: list) -> list:
    url = f"{api_key.wordpress_url}/wp-json/wp/v2/tags"
    auth = (api_key.wordpress_username, api_key.wordpress_app_password)
    tag_ids = []
    
    for tag_name in tag_names:
        try:
            response = requests.get(url, auth=auth, params={'search': tag_name})
            response.raise_for_status()
            tags = response.json()
            if tags:
                tag_ids.append(tags[0]['id'])
            else:
                # Create new tag if it doesn't exist
                new_tag = requests.post(url, auth=auth, json={'name': tag_name})
                new_tag.raise_for_status()
                tag_ids.append(new_tag.json()['id'])
        except requests.RequestException as e:
            logger.error(f"Failed to get or create tag: {str(e)}")
    
    return tag_ids

# def filter_content(content: str) -> bool:
#     inappropriate_words = [
#         # Profanity and explicit language
#         "fuck", "shit", "ass", "damn", "dick", "penis", "cock", "pussy", "vagina",
#         # Hate speech or discriminatory terms
#         "racist", "sexist", "homophobic", "jew", "jewish", "muslim", "palestine", "palestinian", "gaza", "israel",
#         # Violence-related words
#         "kill", "murder", "attack", "assassinate",
#         # Illegal activities
#         "drugs", "theft", "fraud",
#         # Controversial political terms
#         "conspiracy", "extremist", "trump", "kamala", "republican", "democrat", "election", "president",
#         # Sensitive health-related terms
#         "cancer", "depression", "suicide",
#         # Explicit sexual content
#         "porn", "xxx", "sexual", "sex",
#         # Personal information placeholders
#         "[NAME]", "[EMAIL]",
#         # Spam-related words
#         "limited time offer",
#         # Potentially triggering words
#         "trauma", "abuse", "trigger warning", "rape", "incest", "abusive"
#     ]
    
#     content_lower = content.lower()
#     for word in inappropriate_words:
#         if word.lower() in content_lower:
#             return True
    
#     return False

def setup_custom_post_type_and_fields(api_key: APIKey, custom_post_type: str, email_structure: List[EmailSection]) -> None:
    # Check if the custom post type exists and is accessible via REST API
    url = f"{api_key.wordpress_url}/wp-json/wp/v2/{custom_post_type}"
    auth = (api_key.wordpress_username, api_key.wordpress_app_password)

    try:
        response = requests.get(url, auth=auth)
        response.raise_for_status()
        logger.info(f"Custom post type '{custom_post_type}' exists and is accessible via REST API")
        
        # Register custom fields
        register_custom_fields(api_key, custom_post_type, email_structure)
    except requests.RequestException as e:
        logger.error(f"Custom post type '{custom_post_type}' does not exist or is not accessible via REST API: {str(e)}")
        raise AppException(f"Custom post type '{custom_post_type}' is not properly set up in WordPress. Please ensure it's registered with 'show_in_rest' => true", status_code=404)

def register_custom_fields(api_key: APIKey, custom_post_type: str, email_structure: List[EmailSection]) -> None:
    url = f"{api_key.wordpress_url}/wp-json/wp/v2/posts"
    auth = (api_key.wordpress_username, api_key.wordpress_app_password)

    custom_fields = {
        f"email_section_{section.name}": {
            "type": "string",
            "description": section.description
        }
        for section in email_structure
    }

    data = {
        "title": "Temporary post to register custom fields",
        "content": "This is a temporary post to register custom fields.",
        "status": "draft",
        "meta": custom_fields
    }

    logger.info(f"Attempting to register custom fields for post type '{custom_post_type}'")
    logger.info(f"Request data: {data}")

    try:
        response = requests.post(url, json=data, auth=auth)
        response.raise_for_status()
        logger.info(f"Custom fields registration response: {response.text}")
        logger.info(f"Custom fields registered for post type '{custom_post_type}'")
        
        # Delete the temporary post
        temp_post_id = response.json()['id']
        delete_url = f"{api_key.wordpress_url}/wp-json/wp/v2/posts/{temp_post_id}"
        delete_response = requests.delete(delete_url, auth=auth)
        delete_response.raise_for_status()
        logger.info(f"Temporary post deleted successfully")
    except requests.RequestException as e:
        logger.error(f"Failed to register custom fields: {str(e)}")
        logger.error(f"Response content: {e.response.text if e.response else 'No response content'}")
        raise AppException(f"Failed to register custom fields: {str(e)}", status_code=500)
