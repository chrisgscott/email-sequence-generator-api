import requests
from app.core.config import settings
import re
from app.models.api_key import APIKey
from loguru import logger

def create_blog_post(content: str, metadata: dict, api_key: APIKey) -> str:
    # Anonymize content (already done in format_email_for_blog_post)
    
    # Filter content
    if filter_content(content):
        return "Content flagged as potentially inappropriate"
    
    # Create WordPress post
    post_data = {
        'title': metadata['title'],
        'content': content,
        'status': 'draft',
        'categories': [get_category_id(api_key, metadata['category'])],
        'tags': get_tag_ids(api_key, metadata['tags'])
    }
    
    # Post to WordPress
    url = f"{api_key.wordpress_url}/wp-json/wp/v2/posts"
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
    # Implement content filtering logic here
    # Return True if content is inappropriate, False otherwise
    return False