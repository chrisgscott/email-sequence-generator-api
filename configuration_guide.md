# Email Sequence Generator Configuration Guide

This guide explains how to configure the Email Sequence Generator for different use cases. Follow these steps to customize the generator for your specific needs.

## 1. Update Email Sections

File to modify: `app/core/config.py`

Locate the `EMAIL_SECTIONS` list in the `Settings` class. Modify this list to define the structure of your emails.

Example:

python
EMAIL_SECTIONS: List[EmailSection] = [
EmailSection(name="greeting", description="A friendly greeting to the recipient", word_count="20-30"),
EmailSection(name="main_content", description="The primary content or tip for this email", word_count="200-300"),
EmailSection(name="call_to_action", description="A clear call-to-action for the recipient", word_count="30-50"),
]

## 2. Adjust Sequence Configuration

File to modify: `app/core/config.py`

Update the following settings in the `Settings` class:

python
SEQUENCE_LENGTH: int = 52 # Total number of emails in the sequence
SEQUENCE_FREQUENCY_DAYS: int = 7 # Number of days between each email

## 3. Modify OpenAI Prompt

File to modify: `app/core/prompts.py`

Update the `EMAIL_PROMPT` to provide context for your specific use case:

python:app/core/prompts.py
startLine: 2
endLine: 11

Modify this prompt to include any specific instructions or context for your use case.

## 4. Update Sequence Creation Schema

File to modify: `app/schemas/sequence.py`

If your use case requires additional fields for sequence creation, update the `SequenceCreate` class:

python:app/schemas/sequence.py
startLine: 13
endLine: 16

Add any additional fields required for your specific use case.

## 5. Adjust Webhook Handler

File to modify: `app/api/api_v1/api.py`

If you added new fields to `SequenceCreate`, update the webhook handler to process these fields:

python:app/api/api_v1/api.py
startLine: 21
endLine: 58

Modify this function to handle any new fields you've added to the `SequenceCreate` model.

## 6. Update Email Generation Logic

File to modify: `app/services/openai_service.py`

If your use case requires changes to how emails are generated, update the `generate_email_sequence` function:

python:app/services/openai_service.py
startLine: 38
endLine: 56

Adjust this function to include any new fields or logic required for your specific use case.

## 7. Test Your Configuration

After making these changes, thoroughly test your new configuration:

1. Use the webhook to create a new sequence.
2. Check that the emails are generated correctly with the new structure.
3. Verify that the emails are scheduled and sent as expected.

Remember to update any unit tests to reflect your changes, and consider adding new tests for any new functionality.

## Need Help?

If you encounter any issues or need further assistance, please contact the development team.
