jQuery(document).ready(function($) {
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

    $('#journalPromptForm').on('submit', function(e) {
        e.preventDefault();
        
        var formData = new FormData(this);
        var payload = {
            form_id: esak_ajax.form_id,
            topic: esak_ajax.topic,
            recipient_email: formData.get('email'),
            brevo_list_id: esak_ajax.brevo_list_id,
            sequence_settings: {
                total_emails: parseInt(esak_ajax.total_emails),
                days_between_emails: parseInt(esak_ajax.days_between_emails)
            },
            email_structure: esak_ajax.email_structure,
            inputs: {
                first_name: formData.get('first_name'),
                context: esak_ajax.context,
                interests_and_topics: formData.get('interests_and_topics'),
                goals_and_aspirations: formData.get('goals_and_aspirations')
            },
            topic_depth: parseInt(esak_ajax.topic_depth),
            preferred_time: formData.get('preferred_time'),
            timezone: formData.get('timezone')
        };

        console.log('Payload being sent:', payload);

        $.ajax({
            url: esak_ajax.ajax_url,
            type: 'POST',
            data: {
                action: 'esak_submit_form',
                security: esak_ajax.nonce,
                payload: JSON.stringify(payload)
            },
            success: function(response) {
                if (response.success) {
                    console.log('Success:', response.data);
                    // Redirect to the success page with query parameters
                    const successUrl = new URL('/success', window.location.origin);
                    successUrl.searchParams.append('firstName', encodeURIComponent(formData.get('first_name')));
                    successUrl.searchParams.append('preferredTime', encodeURIComponent(formData.get('preferred_time')));
                    successUrl.searchParams.append('timezone', encodeURIComponent(formData.get('timezone')));
                    window.location.href = successUrl.toString();
                } else {
                    console.error('Error:', response.data.message);
                    alert('Error: ' + response.data.message);
                }
            },
            error: function(xhr, status, error) {
                console.error('AJAX Error:', status, error);
                alert('An error occurred. Please try again.');
            }
        });
    });
});