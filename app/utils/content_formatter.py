import re
from bs4 import BeautifulSoup

def format_content(content: str) -> str:
    # Parse the HTML content
    soup = BeautifulSoup(content, 'html.parser')
    
    # Remove any script or style tags
    for script in soup(["script", "style"]):
        script.decompose()
    
    # Get the text content
    text = soup.get_text()
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text