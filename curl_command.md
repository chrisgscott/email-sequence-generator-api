curl -X POST https://plankton-app-qivtq.ondigitalocean.app/api/v1/webhook \
-H "Content-Type: application/json" \
-d @- << EOF
{
  "form_id": "daily_journal_prompts",
  "topic": "Daily Journal Prompts",
  "recipient_email": "chrisgscott+djp@gmail.com",
  "brevo_list_id": 3,
  "brevo_template_id": 2,
  "sequence_settings": {
    "total_emails": 30,
    "days_between_emails": 1
  },
  "email_structure": [
    {
      "name": "journal_prompt",
      "word_count": "100-250",
      "description": "The journal prompt for today."
    },
    {
      "name": "wrap_up",
      "word_count": 50,
      "description": "A quick, inspirational or encouraging wrap up for today's email."
    }
  ],
  "inputs": {
    "first_name": "Chris",
    "context": "You are creating a daily journal prompt that will be sent via email. Be sure to create a prompt that is relevant to the included interests_and_topics and their goals_and_aspirations. Prompts should always be positive and encouraging. Be sure that your prompts are direct and give a very specific and actionable direction for what they should write today. Avoid giving non-writing tasks. Your job is to give them a jumping-off point for what to write in their journal today, so lean toward prompts that encourage introspection, future-casting, mindfulness, gratitude, overcoming challenges, challenging themselves, etc.",
    "interests_and_topics": "Mental health, mindfulness, parenting, and creativity.",
    "goals_and_aspirations": "I want to build a consistent morning routine, manage stress better, and tap into my creativity for personal projects."
  },
  "topic_depth": 10,
  "preferred_time": "07:30:00",
  "timezone": "America/New_York"
}
EOF