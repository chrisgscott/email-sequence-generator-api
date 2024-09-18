import requests
from app.core.config import settings
import re
from app.models.api_key import APIKey
from loguru import logger
from typing import Dict, List
from app.core.exceptions import AppException
from app.schemas.sequence import EmailSection

def create_blog_post(content: Dict[str, str], metadata: dict, api_key: APIKey) -> str:
    # Filter content
    for section_content in content.values():
        if filter_content(section_content):
            return "Content flagged as potentially inappropriate"
    
    # Create WordPress post
    post_data = {
        'title': metadata['title'],
        'status': 'draft',
        'categories': [get_category_id(api_key, metadata['category'])],
        'tags': get_tag_ids(api_key, metadata['tags']),
        'content': '',  # We'll update this with the combined content
    }
    
    # Combine content into the post content
    combined_content = ""
    for field_name, field_content in content.items():
        combined_content += f"<h2>{field_name.capitalize()}</h2>\n{field_content}\n\n"
    post_data['content'] = combined_content

    # Post to WordPress
    url = f"{api_key.wordpress_url}/wp-json/wp/v2/{metadata['custom_post_type']}"
    auth = (api_key.wordpress_username, api_key.wordpress_app_password)
    
    try:
        response = requests.post(url, json=post_data, auth=auth)
        response.raise_for_status()
        post_id = response.json()['id']
        return f"Blog post created with ID: {post_id} (in draft status for review)"
    except requests.RequestException as e:
        logger.error(f"Failed to create blog post: {str(e)}")
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

def filter_content(content: str) -> bool:
    inappropriate_words = [
        # Profanity and explicit language
        "fuck", "shit", "ass", "damn", "dick", "penis", "cock", "pussy", "vagina",
        # Hate speech or discriminatory terms
        "racist", "sexist", "homophobic", "jew", "jewish", "muslim", "palestine", "palestinian", "gaza", "israel",
        # Violence-related words
        "kill", "murder", "attack", "assassinate",
        # Illegal activities
        "drugs", "theft", "fraud",
        # Controversial political terms
        "conspiracy", "extremist", "trump", "kamala", "republican", "democrat", "election", "president",
        # Sensitive health-related terms
        "cancer", "depression", "suicide",
        # Explicit sexual content
        "porn", "xxx", "sexual", "sex",
        # Personal information placeholders
        "[NAME]", "[EMAIL]",
        # Spam-related words
        "limited time offer",
        # Potentially triggering words
        "trauma", "abuse", "trigger warning", "rape", "incest", "abuse", "abusive"
    ]
    
    content_lower = content.lower()
    for word in inappropriate_words:
        if word.lower() in content_lower:
            return True
    
    return False

def setup_custom_post_type_and_fields(api_key: APIKey, custom_post_type: str, email_structure: List[EmailSection]) -> None:
    # Check if the custom post type exists and is accessible via REST API
    url = f"{api_key.wordpress_url}/wp-json/wp/v2/{custom_post_type}"
    auth = (api_key.wordpress_username, api_key.wordpress_app_password)

    try:
        response = requests.get(url, auth=auth)
        response.raise_for_status()
        logger.info(f"Custom post type '{custom_post_type}' exists and is accessible via REST API")
    except requests.RequestException as e:
        logger.error(f"Custom post type '{custom_post_type}' does not exist or is not accessible via REST API: {str(e)}")
        raise AppException(f"Custom post type '{custom_post_type}' is not properly set up in WordPress. Please ensure it's registered with 'show_in_rest' => true", status_code=404)
