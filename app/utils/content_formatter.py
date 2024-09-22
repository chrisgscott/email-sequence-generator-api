import re

def format_content(content: str) -> str:
    # Remove any HTML tags that might have been accidentally included
    content = re.sub(r'<[^>]+>', '', content)
    
    # Ensure proper line breaks for Markdown
    content = content.replace('\n', '\n\n')
    
    # Remove any extra whitespace
    content = re.sub(r'\s+', ' ', content).strip()
    
    return content