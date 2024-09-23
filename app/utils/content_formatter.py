import re

def format_content(content: str) -> str:
    # Remove any HTML tags that might have been accidentally included
    content = re.sub(r'<[^>]+>', '', content)
    
    # Add line breaks between numbered list items
    content = re.sub(r'(\d+\..*?)(?=\n\d+\.|\Z)', r'\1\n', content)
    
    # Add line breaks between bullet point list items
    content = re.sub(r'(-\s.*?)(?=\n-|\Z)', r'\1\n', content)
    
    # Ensure proper line breaks for Markdown
    content = content.replace('\n', '\n\n')
    
    # Remove any extra whitespace
    content = re.sub(r'\s+', ' ', content).strip()
    
    return content