# Main prompt for generating email content
EMAIL_PROMPT = """Generate content for emails {start_index} to {end_index} in an email sequence about {topic}.
User inputs: {inputs}

For each email in the sequence, provide the following sections in Markdown format:
{sections_prompt}

Also provide:
{subject_prompt}

Use proper Markdown syntax for formatting, including headers, lists, and emphasis. Do not use HTML tags.

Return the result as a JSON array with {batch_size} items."""

# Prompt template for generating individual email sections
# {index}: The number of the section in the email
# {name}: The name of the section (e.g., "intro_content", "week_task")
# {description}: A brief description of what this section should contain
# {word_count}: The target word count for this section
SECTIONS_PROMPT = "{index}. {name}: {description} ({word_count} words)"

# Prompt for generating email subject lines
# {subject_index}: The index for the subject line (typically after all content sections)
SUBJECT_PROMPT = "{subject_index}. subject: A compelling subject line for the email. DO NOT include \"Email Number\" or anything like that in the subject line."