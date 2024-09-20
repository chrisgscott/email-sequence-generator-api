import re

def format_content(content: str) -> str:
    # Format numbered lists
    content = re.sub(r'(\d+\.\s*.*?)(?=\n\d+\.|\n\n|\Z)', r'<li>\1</li>', content, flags=re.DOTALL)
    content = re.sub(r'(<li>.*?</li>\n?)+', r'<ol>\g<0></ol>', content, flags=re.DOTALL)

    # Format bullet point lists
    content = re.sub(r'(-\s*.*?)(?=\n-|\n\n|\Z)', r'<li>\1</li>', content, flags=re.DOTALL)
    content = re.sub(r'(<li>.*?</li>\n?)+', r'<ul>\g<0></ul>', content, flags=re.DOTALL)

    # Add paragraph tags
    content = re.sub(r'(?<!\n)\n(?!\n)', '<br>', content)
    content = re.sub(r'\n\n+', '</p><p>', content)
    content = f'<p>{content}</p>'

    return content