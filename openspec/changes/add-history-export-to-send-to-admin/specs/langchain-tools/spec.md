## MODIFIED Requirements

### Requirement: send_to_admin tool shall forward information to admins

The system SHALL include a `send_to_admin` tool that allows users to forward information, requests, or feedback to administrators.

The tool SHALL collect user data (tg_id, first_name, last_name, username, language_code) from the Telegram message context.

The tool SHALL send a formatted notification to the `ADMIN_TELEGRAM_CHAT_ID` if configured.

After the notification message, the tool SHALL additionally generate and send a markdown file containing the user's full dialogue history.

The tool SHALL persist a record to `admin_notifications` table regardless of delivery status.

#### Scenario: User sends message to admin

- **WHEN** a user triggers `send_to_admin` with a comment
- **THEN** the admin chat SHALL receive a formatted notification with user details and the comment
- **THEN** the admin chat SHALL receive a `.md` file attachment with the user's full dialogue history
- **THEN** a record SHALL be saved in `admin_notifications` table

#### Scenario: Admin chat not configured

- **WHEN** `ADMIN_TELEGRAM_CHAT_ID` is empty and the tool is used
- **THEN** the attempt SHALL be recorded to `admin_notifications` with `delivered=False`
- **THEN** the tool SHALL return a success message to the user
