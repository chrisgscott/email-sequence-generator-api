<?php
// form_generator.php

// Configuration
$config = [
    'form_id' => 'daily_journal_prompts',
    'topic' => 'Daily Journal Prompts',
    'brevo_list_id' => 3,
    'total_emails' => 30,
    'days_between_emails' => 1,
    'topic_depth' => 10,
    'email_structure' => [
        [
            'name' => 'journal_prompt',
            'word_count' => '100-250',
            'description' => 'The journal prompt for today.'
        ],
        [
            'name' => 'wrap_up',
            'word_count' => 50,
            'description' => 'A quick, inspirational or encouraging wrap up for today\'s email.'
        ]
    ],
    'custom_inputs' => [
        'interests_and_topics' => 'What are your interests and topics?',
        'goals_and_aspirations' => 'What are your goals and aspirations?'
    ],
    'api_endpoint' => 'https://plankton-app-qivtq.ondigitalocean.app/api/v1/webhook',
    'api_key' => 'your_api_key_here'  // Add this line
];

// Generate HTML Form
$html = <<<HTML
<form id="{$config['form_id']}" class="email-sequence-form">
    <input type="hidden" name="form_id" value="{$config['form_id']}">
    <input type="hidden" name="topic" value="{$config['topic']}">
    <input type="hidden" name="brevo_list_id" value="{$config['brevo_list_id']}">
    
    <div class="form-group">
        <label for="first_name">First Name:</label>
        <input type="text" id="first_name" name="first_name" required>
    </div>
    
    <div class="form-group">
        <label for="email">Email:</label>
        <input type="email" id="email" name="email" required>
    </div>

HTML;

foreach ($config['custom_inputs'] as $name => $label) {
    $html .= <<<HTML
    <div class="form-group">
        <label for="$name">$label</label>
        <input type="text" id="$name" name="$name" required>
    </div>

HTML;
}

$html .= <<<HTML
    <div class="form-group">
        <label for="timezone">Timezone:</label>
        <select id="timezone" name="timezone" required></select>
    </div>
    
    <div class="form-group">
        <label for="preferred_time">Preferred Time:</label>
        <input type="time" id="preferred_time" name="preferred_time" required>
    </div>
    
    <button type="submit">Submit</button>
</form>
HTML;

// Generate JavaScript
$js = <<<JAVASCRIPT
<script>
document.addEventListener('DOMContentLoaded', function() {
    // Populate timezone options
    var timezones = moment.tz.names();
    var userTimezone = moment.tz.guess();
    var timezoneSelect = document.getElementById('timezone');
    
    timezones.forEach(function(tz) {
        var option = document.createElement('option');
        option.value = tz;
        option.text = tz;
        if (tz === userTimezone) {
            option.selected = true;
        }
        timezoneSelect.appendChild(option);
    });

    // Form submission
    document.getElementById('{$config['form_id']}').addEventListener('submit', function(e) {
        e.preventDefault();
        
        var formData = new FormData(this);
        var payload = {
            form_id: formData.get('form_id'),
            topic: formData.get('topic'),
            recipient_email: formData.get('email'),
            brevo_list_id: parseInt(formData.get('brevo_list_id')),
            sequence_settings: {
                total_emails: {$config['total_emails']},
                days_between_emails: {$config['days_between_emails']}
            },
            email_structure: {$config['email_structure']},
            inputs: {
                first_name: formData.get('first_name'),
                context: "You are creating a daily journal prompt that will be sent via email. Be sure to create a prompt that is relevant to the included interests_and_topics and their goals_and_aspirations. Prompts should always be positive and encouraging. Be sure that your prompts are direct and give a very specific and actionable direction for what they should write today. Avoid giving non-writing tasks. Your job is to give them a jumping-off point for what to write in their journal today, so lean toward prompts that encourage introspection, future-casting, mindfulness, gratitude, overcoming challenges, challenging themselves, etc.",
                interests_and_topics: formData.get('interests_and_topics'),
                goals_and_aspirations: formData.get('goals_and_aspirations')
            },
            topic_depth: {$config['topic_depth']},
            preferred_time: formData.get('preferred_time'),
            timezone: formData.get('timezone')
        };

        fetch('{$config['api_endpoint']}', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-API-Key': '{$config['api_key']}',  // Add this line
            },
            body: JSON.stringify(payload),
        })
        .then(response => response.json())
        .then(data => {
            if (data.sequence_id) {
                alert('Form submitted successfully!');
                // Redirect or show success message
            } else {
                alert('Error creating sequence');
            }
        })
        .catch((error) => {
            console.error('Error:', error);
            alert('An error occurred. Please try again.');
        });
    });
});
</script>
JAVASCRIPT;

// Output
echo $html;
echo $js;