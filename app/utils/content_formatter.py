import re

def format_content(content: str) -> str:
    # Remove any HTML tags that might have been accidentally included
    content = re.sub(r'<[^>]+>', '', content)
    
    # Ensure proper line breaks for Markdown lists
    content = re.sub(r'(\n[*\-+]|\n\d+\.)\s', r'\n\n\1 ', content)
    
    # Add line breaks between paragraphs
    content = re.sub(r'(?<!\n)\n(?!\n)', '\n\n', content)
    
    # Remove any extra whitespace
    content = re.sub(r'\s+', ' ', content).strip()
    
    return content