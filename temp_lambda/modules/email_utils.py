"""
Module for email related utilities to send AWS access review reports.
"""

import email.mime.multipart
import email.mime.text
import email.mime.application


def send_email_with_attachment(
    ses_client, recipient_email, narrative, csv_content, filename
):
    """
    Send an email with a narrative and CSV attachment.
    """
    print(f"Preparing to send email to {recipient_email} with report attachment")

    # Create a multipart/mixed parent container
    msg = email.mime.multipart.MIMEMultipart("mixed")

    # Add subject, from, to headers
    msg["Subject"] = "AWS Access Review Report"
    msg["From"] = recipient_email  # Using recipient as sender (must be verified in SES)
    msg["To"] = recipient_email

    # Create a multipart/alternative child container for text and HTML versions
    msg_body = email.mime.multipart.MIMEMultipart("alternative")

    # Format the narrative for HTML (replace newlines with <br> tags)
    formatted_narrative = narrative.replace("\n", "<br>")

    # Plain text version of the message
    text_content = (
        "AWS Access Review Report\n\n"
        f"{narrative}\n\n"
        "Please see the attached CSV file for detailed findings."
    )
    text_part = email.mime.text.MIMEText(text_content, "plain")

    # HTML version of the message
    html_content = (
        "<html>\n"
        "<head></head>\n"
        "<body>\n"
        "<h1>AWS Access Review Report</h1>\n"
        f"<p>{formatted_narrative}</p>\n"
        "<p>Please see the attached CSV file for detailed findings.</p>\n"
        "</body>\n"
        "</html>"
    )
    html_part = email.mime.text.MIMEText(html_content, "html")

    # Add the text and HTML parts to the child container
    msg_body.attach(text_part)
    msg_body.attach(html_part)

    # Attach the multipart/alternative child container to the multipart/mixed parent
    msg.attach(msg_body)

    # Create the attachment
    attachment = email.mime.application.MIMEApplication(csv_content)
    attachment.add_header("Content-Disposition", "attachment", filename=filename)

    # Add the attachment to the message
    msg.attach(attachment)

    try:
        # Convert the message to a string and send it
        print("Attempting to send email via SES...")
        response = ses_client.send_raw_email(
            Source=recipient_email,
            Destinations=[recipient_email],
            RawMessage={"Data": msg.as_string()},
        )
        print(f"Email sent successfully! Message ID: {response['MessageId']}")
        return True
    except Exception as e:
        error_msg = str(e)
        print(f"Error sending email: {error_msg}")
        # Print SES verification status for debugging
        try:
            verification = ses_client.get_identity_verification_attributes(
                Identities=[recipient_email]
            )
            print(f"SES verification status: {verification}")
        except Exception as ve:
            error_msg = str(ve)
            print(f"Error checking SES verification: {error_msg}")
        return False


def verify_email_for_ses(ses_client, email_address):
    """
    Verify an email address with SES if it's not already verified.
    """
    print(f"Checking SES verification status for {email_address}")

    try:
        # Get verification status
        response = ses_client.get_identity_verification_attributes(
            Identities=[email_address]
        )

        # Check if the email is already verified
        attributes = response.get("VerificationAttributes", {})
        if email_address in attributes:
            status = attributes[email_address].get("VerificationStatus")
            if status == "Success":
                print(f"Email {email_address} is already verified in SES")
                return True
            else:
                print(f"Email {email_address} verification status: {status}")

        # If not verified, send verification email
        print(f"Sending verification email to {email_address}")
        ses_client.verify_email_identity(EmailAddress=email_address)
        print(f"Verification email sent to {email_address}. Check inbox to verify.")

        return False
    except Exception as e:
        error_msg = str(e)
        print(f"Error verifying email with SES: {error_msg}")
        raise
