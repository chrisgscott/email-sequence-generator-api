from wordpress_xmlrpc import Client, WordPressPost
from wordpress_xmlrpc.methods.posts import NewPost
from app.core.config import settings
import re

def create_blog_post(content: str, metadata: dict, api_key: APIKey) -> str:
    wp = Client(api_key.wordpress_url, api_key.wordpress_username, api_key.wordpress_password)
    
    # Anonymize content (already done in format_email_for_blog_post)
    
    # Filter content
    if filter_content(content):
        return "Content flagged as potentially inappropriate"
    
    # Create WordPress post
    post = WordPressPost()
    post.title = metadata['title']
    post.content = content
    post.terms_names = {
        'category': [metadata['category']],
        'post_tag': metadata['tags']
    }
    post.post_status = 'draft'
    
    # Post to WordPress
    post_id = wp.call(NewPost(post))
    
    return f"Blog post created with ID: {post_id} (in draft status for review)"

def anonymize_content(content: str) -> str:
    # Replace names with generic alternatives
    name_pattern = r'\b[A-Z][a-z]+ (?:[A-Z][a-z]+ )?[A-Z][a-z]+\b'
    names = re.findall(name_pattern, content)
    
    for i, name in enumerate(names):
        content = content.replace(name, f"Person{i+1}")
    
    return content

def filter_content(content: str) -> bool:
    # Check content against a list of potentially triggering or harmful words/phrases
    triggering_words = ["suicide", "self-harm", "abuse", "trauma", "violence"]
    return any(word in content.lower() for word in triggering_words)

def generate_title(content: str, metadata: dict) -> str:
    # Implement title generation logic
    return f"New Post: {metadata.get('topic', 'Untitled')}"

def expand_content(content: str, metadata: dict) -> str:
    # Implement content expansion logic
    return f"{content}\n\nMetadata: {metadata}"

def get_terms(metadata: dict) -> dict:
    # Implement logic to map metadata to WordPress terms
    return {
        "category": [metadata.get("category", "Uncategorized")],
        "post_tag": metadata.get("tags", [])
    }