import re
from bs4 import BeautifulSoup

def format_content(content: str) -> str:
    # Parse the HTML content
    soup = BeautifulSoup(content, 'html.parser')
    
    # Remove any script or style tags
    for script in soup(["script", "style"]):
        script.decompose()
    
    # Remove extra whitespace within tags, but preserve space after closing tags
    for tag in soup.find_all(text=True):
        if tag.parent.name not in ['script', 'style']:
            new_text = re.sub(r'\s+', ' ', tag.strip())
            new_text = re.sub(r'>\s+', '> ', new_text)  # Preserve space after closing tags
            tag.replace_with(new_text)
    
    # Return the cleaned HTML as a string
    return str(soup)