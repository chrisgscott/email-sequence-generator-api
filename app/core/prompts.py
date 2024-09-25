# Main prompt for generating email content
EMAIL_PROMPT = """Generate content for emails {start_index} to {end_index} in an email sequence about {topic}.
User inputs: {inputs}

For each email in the sequence, provide the following sections in HTML format:
{sections_prompt}

Also provide:
{subject_prompt}

Use proper HTML tags for formatting, including headers, lists, and emphasis. Ensure proper structure with <p>, <ul>, <ol>, <li>, <strong>, <em> tags as needed.
For lists:
- Use <ul> for unordered lists and <ol> for ordered lists.
- Each list item should be wrapped in <li> tags.
Ensure there's proper spacing between elements using appropriate HTML structure.

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