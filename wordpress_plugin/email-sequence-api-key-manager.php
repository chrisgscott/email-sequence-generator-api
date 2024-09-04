<?php
/*
Plugin Name: Email Sequence API Key Manager
Description: Manages API key for Email Sequence Generator services and provides a secure way to use it.
Version: 1.2
Author: Chris Scott
*/

// Define the API endpoint URL as a constant
define('ESAK_API_ENDPOINT', 'https://plankton-app-qivtq.ondigitalocean.app/api/v1/sequences/webhook');

// Add menu item to the WordPress admin
function esak_add_menu_item() {
    add_options_page('Email Sequence API Settings', 'Email Sequence API', 'manage_options', 'esak-settings', 'esak_settings_page');
}
add_action('admin_menu', 'esak_add_menu_item');

// Create the settings page
function esak_settings_page() {
    ?>
    <div class="wrap">
        <h1>Email Sequence API Settings</h1>
        <form method="post" action="options.php">
            <?php
            settings_fields('esak_settings');
            do_settings_sections('esak-settings');
            submit_button();
            ?>
        </form>
    </div>
    <?php
}

// Register settings
function esak_register_settings() {
    register_setting('esak_settings', 'esak_api_key');
    register_setting('esak_settings', 'esak_form_id');
    register_setting('esak_settings', 'esak_topic');
    register_setting('esak_settings', 'esak_brevo_list_id');
    register_setting('esak_settings', 'esak_total_emails');
    register_setting('esak_settings', 'esak_days_between_emails');
    register_setting('esak_settings', 'esak_topic_depth');
    register_setting('esak_settings', 'esak_email_structure', 'esak_sanitize_email_structure');
    register_setting('esak_settings', 'esak_context');

    add_settings_section('esak_settings_section', 'API Settings', null, 'esak-settings');
    add_settings_field('esak_api_key', 'API Key', 'esak_api_key_field', 'esak-settings', 'esak_settings_section');
    add_settings_field('esak_form_id', 'Form ID', 'esak_form_id_field', 'esak-settings', 'esak_settings_section');
    add_settings_field('esak_topic', 'Topic', 'esak_topic_field', 'esak-settings', 'esak_settings_section');
    add_settings_field('esak_brevo_list_id', 'Brevo List ID', 'esak_brevo_list_id_field', 'esak-settings', 'esak_settings_section');
    add_settings_field('esak_total_emails', 'Total Emails', 'esak_total_emails_field', 'esak-settings', 'esak_settings_section');
    add_settings_field('esak_days_between_emails', 'Days Between Emails', 'esak_days_between_emails_field', 'esak-settings', 'esak_settings_section');
    add_settings_field('esak_topic_depth', 'Topic Depth', 'esak_topic_depth_field', 'esak-settings', 'esak_settings_section');
    add_settings_field('esak_email_structure', 'Email Structure', 'esak_email_structure_field', 'esak-settings', 'esak_settings_section');
    add_settings_field('esak_context', 'Context', 'esak_context_field', 'esak-settings', 'esak_settings_section');
}
add_action('admin_init', 'esak_register_settings');

// Create API key field
function esak_api_key_field() {
    $api_key = get_option('esak_api_key');
    echo "<input type='text' name='esak_api_key' value='" . esc_attr($api_key) . "' class='regular-text'>";
}

function esak_form_id_field() {
    $form_id = get_option('esak_form_id', 'daily_journal_prompts');
    echo "<input type='text' name='esak_form_id' value='" . esc_attr($form_id) . "' class='regular-text'>";
}

function esak_topic_field() {
    $topic = get_option('esak_topic', 'Daily Journal Prompts');
    echo "<input type='text' name='esak_topic' value='" . esc_attr($topic) . "' class='regular-text'>";
}

function esak_brevo_list_id_field() {
    $brevo_list_id = get_option('esak_brevo_list_id', 3);
    echo "<input type='number' name='esak_brevo_list_id' value='" . esc_attr($brevo_list_id) . "' class='small-text'>";
}

function esak_total_emails_field() {
    $total_emails = get_option('esak_total_emails', 365);
    echo "<input type='number' name='esak_total_emails' value='" . esc_attr($total_emails) . "' class='small-text'>";
}

function esak_days_between_emails_field() {
    $days_between_emails = get_option('esak_days_between_emails', 1);
    echo "<input type='number' name='esak_days_between_emails' value='" . esc_attr($days_between_emails) . "' class='small-text'>";
}

function esak_topic_depth_field() {
    $topic_depth = get_option('esak_topic_depth', 10);
    echo "<input type='number' name='esak_topic_depth' value='" . esc_attr($topic_depth) . "' class='small-text'>";
}

function esak_email_structure_field() {
    $email_structure = get_option('esak_email_structure', '[{"name":"journal_prompt","word_count":"100-250","description":"The journal prompt for today."},{"name":"wrap_up","word_count":"50","description":"A quick, inspirational or encouraging wrap up for today\'s email."}]');
    echo "<textarea name='esak_email_structure' rows='10' cols='50' class='large-text'>" . esc_textarea($email_structure) . "</textarea>";
    echo "<p class='description'>Enter the email structure as a JSON array. Each object should have 'name', 'word_count', and 'description' fields.</p>";
}

function esak_context_field() {
    $context = get_option('esak_context', "You are creating a daily journal prompt that will be sent via email. Be sure to create a prompt that is relevant to the included interests_and_topics and their goals_and_aspirations. Prompts should always be positive and encouraging. Be sure that your prompts are direct and give a very specific and actionable direction for what they should write today. Avoid giving non-writing tasks. Your job is to give them a jumping-off point for what to write in their journal today, so lean toward prompts that encourage introspection, future-casting, mindfulness, gratitude, overcoming challenges, challenging themselves, etc.");
    echo "<textarea name='esak_context' rows='10' cols='50' class='large-text'>" . esc_textarea($context) . "</textarea>";
}

function esak_sanitize_email_structure($input) {
    $sanitized = json_decode($input, true);
    if (json_last_error() !== JSON_ERROR_NONE) {
        add_settings_error('esak_email_structure', 'invalid_json', 'The email structure must be valid JSON.');
        return get_option('esak_email_structure');
    }
    return json_encode($sanitized);
}

// Create custom REST API endpoint
function esak_handle_form_submission($request) {
    $api_key = get_option('esak_api_key');
    if (!$api_key) {
        error_log('ESAK: API key is not set');
        return new WP_Error('no_api_key', 'API key is not set', array('status' => 403));
    }

    $payload = $request->get_json_params();
    
    $response = wp_remote_post(ESAK_API_ENDPOINT, array(
        'headers' => array(
            'Content-Type' => 'application/json',
            'X-API-Key' => $api_key
        ),
        'body' => json_encode($payload),
        'timeout' => 60, // Increase timeout to 60 seconds
    ));

    if (is_wp_error($response)) {
        error_log('ESAK: Failed to connect to the API - ' . $response->get_error_message());
        return new WP_Error('api_error', 'Failed to connect to the API', array('status' => 500));
    }

    $body = wp_remote_retrieve_body($response);
    $data = json_decode($body, true);

    $response_code = wp_remote_retrieve_response_code($response);
    if ($response_code !== 200) {
        error_log('ESAK: API error - Status: ' . $response_code . ', Body: ' . $body);
        return new WP_Error('api_error', $data['detail'] ?? 'Unknown error', array('status' => $response_code));
    }

    return new WP_REST_Response($data, 200);
}

// Register the REST API endpoint
function esak_register_rest_route() {
    register_rest_route('esak/v1', '/submit-form', array(
        'methods' => 'POST',
        'callback' => 'esak_handle_form_submission',
        'permission_callback' => '__return_true'
    ));
}
add_action('rest_api_init', 'esak_register_rest_route');

// Add AJAX action for frontend form submission
function esak_ajax_submit_form() {
    check_ajax_referer('esak_submit_form', 'security');

    $payload = json_decode(stripslashes($_POST['payload']), true);
    
    $api_key = get_option('esak_api_key');
    if (!$api_key) {
        wp_send_json_error(array('message' => 'API key is not set'), 403);
    }

    $response = wp_remote_post(ESAK_API_ENDPOINT, array(
        'headers' => array(
            'Content-Type' => 'application/json',
            'X-API-Key' => $api_key
        ),
        'body' => json_encode($payload),
        'timeout' => 60, // Increase timeout to 60 seconds
    ));

    if (is_wp_error($response)) {
        error_log('ESAK: Failed to connect to the API - ' . $response->get_error_message());
        wp_send_json_error(array('message' => 'Failed to connect to the API'), 500);
    }

    $body = wp_remote_retrieve_body($response);
    $data = json_decode($body, true);

    $response_code = wp_remote_retrieve_response_code($response);
    if ($response_code !== 200) {
        error_log('ESAK: API error - Status: ' . $response_code . ', Body: ' . $body);
        wp_send_json_error(array('message' => $data['detail'] ?? 'Unknown error'), $response_code);
    }

    wp_send_json_success($data);
}
add_action('wp_ajax_esak_submit_form', 'esak_ajax_submit_form');
add_action('wp_ajax_nopriv_esak_submit_form', 'esak_ajax_submit_form');

// Enqueue scripts for frontend
function esak_enqueue_scripts() {
    $total_emails = get_option('esak_total_emails', 365);
    $topic_depth = get_option('esak_topic_depth', 10);
    error_log("Debug: total_emails = $total_emails, topic_depth = $topic_depth");

    wp_enqueue_script('esak-form-submission', plugin_dir_url(__FILE__) . 'js/form-submission.js', array('jquery'), '1.0', true);
    wp_localize_script('esak-form-submission', 'esak_ajax', array(
        'ajax_url' => admin_url('admin-ajax.php'),
        'nonce' => wp_create_nonce('esak_submit_form'),
        'form_id' => get_option('esak_form_id', 'daily_journal_prompts'),
        'topic' => get_option('esak_topic', 'Daily Journal Prompts'),
        'brevo_list_id' => intval(get_option('esak_brevo_list_id', 3)),
        'total_emails' => intval($total_emails),
        'days_between_emails' => intval(get_option('esak_days_between_emails', 1)),
        'topic_depth' => intval($topic_depth),
        'email_structure' => json_decode(get_option('esak_email_structure', '[{"name":"journal_prompt","word_count":"100-250","description":"The journal prompt for today."},{"name":"wrap_up","word_count":"50","description":"A quick, inspirational or encouraging wrap up for today\'s email."}]'), true),
        'context' => get_option('esak_context', "You are creating a daily journal prompt that will be sent via email. Be sure to create a prompt that is relevant to the included interests_and_topics and their goals_and_aspirations. Prompts should always be positive and encouraging. Be sure that your prompts are direct and give a very specific and actionable direction for what they should write today. Avoid giving non-writing tasks. Your job is to give them a jumping-off point for what to write in their journal today, so lean toward prompts that encourage introspection, future-casting, mindfulness, gratitude, overcoming challenges, challenging themselves, etc.")
    ));
}
add_action('wp_enqueue_scripts', 'esak_enqueue_scripts');