EMAIL_PROMPT = """Generate content for emails {start_index} to {end_index} in an email sequence about {topic}.
User inputs: {inputs}

For each email in the sequence, provide the following sections:
{sections_prompt}

Also provide:
{subject_prompt}

Return the result as a JSON array with {batch_size} items."""

SECTIONS_PROMPT = "{index}. {name}: {description} ({word_count} words)"

SUBJECT_PROMPT = "{subject_index}. subject: A compelling subject line for the email. DO NOT include \"Email Number\" or anything like that in the subject line."