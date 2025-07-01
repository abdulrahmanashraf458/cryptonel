import os
import smtplib
import threading
from datetime import datetime
from email.message import EmailMessage
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# SMTP configuration from .env file
SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_SENDER_NAME = os.getenv("SMTP_SENDER_NAME", "Cryptonel")
SMTP_SENDER_EMAIL = os.getenv("SMTP_SENDER_EMAIL")

# Log the email configuration to verify it's loaded
print(f"SMTP Email Sender Loaded: HOST={SMTP_HOST}, PORT={SMTP_PORT}, USER={SMTP_USER}")

# Define constants for our links
DISCORD_LINK = "https://discord.gg/clyne"
X_LINK = "https://x.com/ClyneBot"

def format_decimal(value):
    """Format a decimal value to 8 decimal places"""
    try:
        return f"{float(value):.8f}"
    except:
        return str(value)

def send_transaction_emails(sender, recipient, transaction, users_collection):
    """
    Send transaction notification emails to both sender and recipient
    """
    try:
        # Get email addresses from users
        sender_email = sender.get("email")
        recipient_email = recipient.get("email")
            
        # Check if valid emails exist
        if not sender_email or not recipient_email:
            print(f"Missing email addresses for notification. Sender: {sender.get('username')}, Recipient: {recipient.get('username')}")
            # Don't proceed if we don't have valid emails
            return False
        
        print(f"Sending transaction notification to sender email: {sender_email}")
        print(f"Sending transaction notification to recipient email: {recipient_email}")
        
        # Format timestamp
        timestamp = transaction.get("timestamp")
        if isinstance(timestamp, str):
            try:
                dt = datetime.fromisoformat(timestamp)
                formatted_time = dt.strftime('%Y-%m-%d %H:%M:%S')
            except ValueError:
                formatted_time = timestamp
        else:
            formatted_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Get transfer reason
        transfer_reason = transaction.get("reason", "Not specified")
        
        # Generate HTML for sender and recipient
        sender_html = generate_sender_email(
            total_amount=transaction.get("amount"),
            tax=transaction.get("fee"),
            recipient_data={'public_address': transaction.get("recipient_public_address")},
            transaction_id=transaction.get("id"),
            formatted_time=formatted_time,
            reason=transfer_reason
        )
        
        # Use the same amount value for the recipient as the sender to keep information consistent
        recipient_html = generate_recipient_email(
            total_amount=transaction.get("amount"),  # Use the same amount as sender email
            tax=transaction.get("fee"),
            sender_data={'public_address': transaction.get("sender_public_address")},
            transaction_id=transaction.get("id"),
            formatted_time=formatted_time,
            reason=transfer_reason
        )
        
        # Send emails in separate threads to avoid blocking
        threading.Thread(
            target=send_email,
            args=(
                sender_email, 
                sender.get("username", "Cryptonel User"),
                "CRN Transfer Successful", 
                sender_html
            ),
            daemon=True
        ).start()
        
        threading.Thread(
            target=send_email,
            args=(
                recipient_email, 
                recipient.get("username", "Cryptonel User"),
                "CRN Received Successfully", 
                recipient_html
            ),
            daemon=True
        ).start()
        
        return True
    except Exception as e:
        print(f"Error sending transaction emails: {str(e)}")
        return False

def send_email(to_email, to_name, subject, html_body):
    """Send an email using the configured SMTP server."""
    try:
        if not all([SMTP_HOST, SMTP_USER, SMTP_PASSWORD, SMTP_SENDER_EMAIL]):
            print("SMTP configuration is incomplete. Cannot send email.")
            return False

        msg = EmailMessage()
        msg["From"] = f"{SMTP_SENDER_NAME} <{SMTP_SENDER_EMAIL}>"
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.set_content("This is an HTML email. Please use an HTML-compatible client to view it.")
        msg.add_alternative(html_body, subtype="html")

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
        print(f"Email sent successfully to {to_email}")
        return True
    except Exception as e:
        print(f"Error sending email via SMTP: {str(e)}")
        import traceback
        print(f"Error traceback: {traceback.format_exc()}")
        return False

def send_rating_notification_email(recipient, rater, stars, comment, average_rating):
    """
    Send email notification to recipient when they receive a new rating
    """
    try:
        recipient_email = recipient.get("email")
        if not recipient_email:
            print(f"No email address found for recipient {recipient.get('username')}")
            return False
        
        print(f"Sending rating notification to: {recipient_email}")
        
        # Generate HTML for rating notification
        rating_html = generate_rating_notification_email(
            recipient_username=recipient.get("username", "User"),
            rater_username=rater.get("username", "User"),
            stars=stars,
            comment=comment,
            average_rating=average_rating
        )
        
        # Send email
        success = send_email(
            recipient_email,
            recipient.get("username", "Cryptonel User"),
            f"New Rating Received - {stars} Stars",
            rating_html
        )
        
        return success
    except Exception as e:
        print(f"Error sending rating notification email: {str(e)}")
        return False

def generate_rating_notification_email(recipient_username, rater_username, stars, comment, average_rating):
    """Generate HTML for rating notification email"""
    
    # Create star display
    star_display = "★" * stars + "☆" * (5 - stars)
    
    # Add comment section if provided
    comment_html = ""
    if comment and comment.strip():
        comment_html = f"""
        <tr style="border-bottom: 1px solid #eee;">
            <td style="padding: 10px 0; color: #666;">
                Comment:
            </td>
            <td style="padding: 10px 0; text-align: right;">
                "{comment}"
            </td>
        </tr>
        """
    
    return f"""
    <html>
        <head>
            <title>New Rating Received</title>
            <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.3/css/all.min.css" rel="stylesheet"/>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    margin: 0;
                    padding: 0;
                    background-color: #ffffff;
                }}
                .header {{
                    background-color: #1e2329;
                    padding: 20px;
                    text-align: center;
                    color: #f0b90b;
                    font-size: 24px;
                    font-weight: bold;
                }}
                .content {{
                    padding: 20px;
                }}
                .content h1 {{
                    color: #000000;
                    font-size: 24px;
                }}
                .content p {{
                    color: #000000;
                    font-size: 16px;
                }}
                .content .highlight {{
                    font-weight: bold;
                }}
                .content .button {{
                    background-color: #f0b90b;
                    color: #000000;
                    padding: 10px 20px;
                    text-decoration: none;
                    display: inline-block;
                    margin: 20px 0;
                }}
                .content .button:hover {{
                    background-color: #e5a800;
                }}
                .footer {{
                    background-color: #f4f4f4;
                    padding: 20px;
                    text-align: center;
                    border-top: 2px solid #e5e5e5;
                }}
                .footer p {{
                    color: #000000;
                    font-size: 12px;
                }}
                .footer a {{
                    color: #f0b90b;
                    text-decoration: none;
                }}
                .footer .social-icons {{
                    margin: 20px 0;
                }}
                .footer .social-icons a {{
                    margin: 0 10px;
                    color: #000000;
                    text-decoration: none;
                }}
                .stars {{
                    color: #f0b90b;
                    font-size: 24px;
                    letter-spacing: 2px;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                Cryptonel
            </div>
            <div class="content">
                <h1>New Rating Received</h1>
                <p style="font-size: 20px; font-weight: bold; margin-bottom: 25px;">
                    Congratulations! You received a new rating from {rater_username}.
                </p>
                
                <div style="text-align: center; margin: 30px 0;">
                    <div class="stars">{star_display}</div>
                    <p style="font-size: 18px; margin-top: 10px; color: #666;">
                        {stars} out of 5 stars
                    </p>
                </div>
                
                <table style="width: 100%; border-collapse: collapse; margin-top: 20px;">
                    <tr style="border-bottom: 1px solid #eee;">
                        <td style="padding: 10px 0; color: #666;">
                            Rated by:
                        </td>
                        <td style="padding: 10px 0; text-align: right;">
                            {rater_username}
                        </td>
                    </tr>
                    {comment_html}
                    <tr style="border-bottom: 1px solid #eee;">
                        <td style="padding: 10px 0; color: #666;">
                            Your Average Rating:
                        </td>
                        <td style="padding: 10px 0; text-align: right; font-weight: bold; color: #4CAF50;">
                            {average_rating} / 5.0
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 10px 0; color: #666;">
                            Date:
                        </td>
                        <td style="padding: 10px 0; text-align: right;">
                            {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                        </td>
                    </tr>
                </table>
                
                <a class="button" href="{DISCORD_LINK}">
                    Join Our Discord Community
                </a>
                
                <p>
                    Keep up the great work! Your positive ratings help build trust in our community.
                </p>
                
                <p>
                    This is an automated message, please do not reply.
                </p>
            </div>
            <div class="footer">
                <p>
                    Cryptonel Support
                </p>
                <div class="social-icons">
                    <a href="{DISCORD_LINK}">
                        <i class="fab fa-discord"></i>
                    </a>
                    <a href="{X_LINK}">
                        <i class="fab fa-twitter"></i>
                    </a>
                </div>
                <p>
                    To stay secure, setup Two factor authentication (2FA)
                </p>
                <p>
                    <span class="highlight">
                        Risk warning:
                    </span>
                    Cryptocurrency trading is subject to high market risk.
                </p>
                <p>
                    2025 cryptonel.online, All Rights Reserved
                </p>
            </div>
        </body>
    </html>
    """

def generate_sender_email(total_amount, tax, recipient_data, transaction_id, formatted_time, reason=None):
    """Generate HTML for sender email using user's template"""
    
    # Calculate amount after tax for display
    try:
        amount_after_tax = float(total_amount) - float(tax)
        amount_after_tax_formatted = format_decimal(amount_after_tax)
    except:
        amount_after_tax_formatted = "Error calculating"
    
    # Add reason section if provided
    reason_html = ""
    if reason and reason != "Not specified":
        reason_html = f"""
        <tr style="border-bottom: 1px solid #eee;">
            <td style="padding: 10px 0; color: #666;">
                Reason:
            </td>
            <td style="padding: 10px 0; text-align: right;">
                {reason}
            </td>
        </tr>
        """
    
    return f"""
    <html>
        <head>
            <title>CRN Transfer Successful</title>
            <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.3/css/all.min.css" rel="stylesheet"/>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    margin: 0;
                    padding: 0;
                    background-color: #ffffff;
                }}
                .header {{
                    background-color: #1e2329;
                    padding: 20px;
                    text-align: center;
                    color: #f0b90b;
                    font-size: 24px;
                    font-weight: bold;
                }}
                .content {{
                    padding: 20px;
                }}
                .content h1 {{
                    color: #000000;
                    font-size: 24px;
                }}
                .content p {{
                    color: #000000;
                    font-size: 16px;
                }}
                .content .highlight {{
                    font-weight: bold;
                }}
                .content .button {{
                    background-color: #f0b90b;
                    color: #000000;
                    padding: 10px 20px;
                    text-decoration: none;
                    display: inline-block;
                    margin: 20px 0;
                }}
                .content .button:hover {{
                    background-color: #e5a800;
                }}
                .footer {{
                    background-color: #f4f4f4;
                    padding: 20px;
                    text-align: center;
                    border-top: 2px solid #e5e5e5;
                }}
                .footer p {{
                    color: #000000;
                    font-size: 12px;
                }}
                .footer a {{
                    color: #f0b90b;
                    text-decoration: none;
                }}
                .footer .social-icons {{
                    margin: 20px 0;
                }}
                .footer .social-icons a {{
                    margin: 0 10px;
                    color: #000000;
                    text-decoration: none;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                Cryptonel
            </div>
            <div class="content">
                <h1>CRN Transfer Successful</h1>
                <p style="font-size: 20px; font-weight: bold; margin-bottom: 25px;">
                    You've successfully transferred {format_decimal(total_amount)} CRN, and {amount_after_tax_formatted} CRN was received after fees.
                </p>
                <table style="width: 100%; border-collapse: collapse; margin-top: 20px;">
                    <tr style="border-bottom: 1px solid #eee;">
                        <td style="padding: 10px 0; color: #666;">
                            Total Amount Sent:
                        </td>
                        <td style="padding: 10px 0; text-align: right;">
                            {format_decimal(total_amount)} CRN
                        </td>
                    </tr>
                    <tr style="border-bottom: 1px solid #eee;">
                        <td style="padding: 10px 0; color: #666;">
                            Network Fee:
                        </td>
                        <td style="padding: 10px 0; text-align: right;">
                            {format_decimal(tax)} CRN
                        </td>
                    </tr>
                    <tr style="border-bottom: 1px solid #eee;">
                        <td style="padding: 10px 0; color: #666; font-weight: bold;">
                            Recipient Receives:
                        </td>
                        <td style="padding: 10px 0; text-align: right; font-weight: bold; color: #4CAF50;">
                            {amount_after_tax_formatted} CRN
                        </td>
                    </tr>
                    <tr style="border-bottom: 1px solid #eee;">
                        <td style="padding: 10px 0; color: #666;">
                            Recipient Address:
                        </td>
                        <td style="padding: 10px 0; text-align: right; word-break: break-all;">
                            {recipient_data['public_address']}
                        </td>
                    </tr>
                    {reason_html}
                    <tr>
                        <td style="padding: 10px 0; color: #666;">
                            Transaction ID:
                        </td>
                        <td style="padding: 10px 0; text-align: right; word-break: break-all;">
                            {transaction_id}
                        </td>
                    </tr>
                </table>
                <a class="button" href="{DISCORD_LINK}">
                    Visit Our Discord Server
                </a>
                <p>
                    Don't recognize this activity? Please contact customer support immediately.
                </p>
                <p>
                    Please check with the receiving platform or wallet as the transaction is already confirmed on our Global Transactions Channel on Discord.
                </p>
                <p>
                    This is an automated message, please do not reply.
                </p>
            </div>
            <div class="footer">
                <p>
                    Cryptonel Support
                </p>
                <div class="social-icons">
                    <a href="{DISCORD_LINK}">
                        <i class="fab fa-discord"></i>
                    </a>
                    <a href="{X_LINK}">
                        <i class="fab fa-twitter"></i>
                    </a>
                </div>
                <p>
                    To stay secure, setup Two factor authentication (2FA)
                </p>
                <p>
                    <span class="highlight">
                        Risk warning:
                    </span>
                    Cryptocurrency trading is subject to high market risk.
                </p>
                <p>
                    2025 cryptonel.online, All Rights Reserved
                </p>
            </div>
        </body>
    </html>
    """

def generate_recipient_email(total_amount, tax, sender_data, transaction_id, formatted_time, reason=None):
    """Generate HTML for recipient email using user's template"""
    
    # Calculate amount after tax for display
    try:
        amount_after_tax = float(total_amount) - float(tax)
        amount_after_tax_formatted = format_decimal(amount_after_tax)
    except:
        amount_after_tax_formatted = "Error calculating"
    
    # Add reason section if provided
    reason_html = ""
    if reason and reason != "Not specified":
        reason_html = f"""
        <tr style="border-bottom: 1px solid #eee;">
            <td style="padding: 10px 0; color: #666;">
                Reason:
            </td>
            <td style="padding: 10px 0; text-align: right;">
                {reason}
            </td>
        </tr>
        """
    
    return f"""
    <html>
        <head>
            <title>CRN Received Successfully</title>
            <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.3/css/all.min.css" rel="stylesheet"/>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    margin: 0;
                    padding: 0;
                    background-color: #ffffff;
                }}
                .header {{
                    background-color: #1e2329;
                    padding: 20px;
                    text-align: center;
                    color: #f0b90b;
                    font-size: 24px;
                    font-weight: bold;
                }}
                .content {{
                    padding: 20px;
                }}
                .content h1 {{
                    color: #000000;
                    font-size: 24px;
                }}
                .content p {{
                    color: #000000;
                    font-size: 16px;
                }}
                .content .highlight {{
                    font-weight: bold;
                }}
                .content .button {{
                    background-color: #f0b90b;
                    color: #000000;
                    padding: 10px 20px;
                    text-decoration: none;
                    display: inline-block;
                    margin: 20px 0;
                }}
                .content .button:hover {{
                    background-color: #e5a800;
                }}
                .footer {{
                    background-color: #f4f4f4;
                    padding: 20px;
                    text-align: center;
                    border-top: 2px solid #e5e5e5;
                }}
                .footer p {{
                    color: #000000;
                    font-size: 12px;
                }}
                .footer a {{
                    color: #f0b90b;
                    text-decoration: none;
                }}
                .footer .social-icons {{
                    margin: 20px 0;
                }}
                .footer .social-icons a {{
                    margin: 0 10px;
                    color: #000000;
                    text-decoration: none;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                Cryptonel
            </div>
            <div class="content">
                <h1>CRN Received Successfully</h1>
                <p style="font-size: 20px; font-weight: bold; margin-bottom: 25px;">
                    You've received {amount_after_tax_formatted} CRN after network fees.
                </p>
                <table style="width: 100%; border-collapse: collapse; margin-top: 20px;">
                    <tr style="border-bottom: 1px solid #eee;">
                        <td style="padding: 10px 0; color: #666;">
                            Transaction Amount:
                        </td>
                        <td style="padding: 10px 0; text-align: right;">
                            {format_decimal(total_amount)} CRN
                        </td>
                    </tr>
                    <tr style="border-bottom: 1px solid #eee;">
                        <td style="padding: 10px 0; color: #666;">
                            Network Fee:
                        </td>
                        <td style="padding: 10px 0; text-align: right;">
                            {format_decimal(tax)} CRN
                        </td>
                    </tr>
                    <tr style="border-bottom: 1px solid #eee;">
                        <td style="padding: 10px 0; color: #666; font-weight: bold;">
                            Net Amount Received:
                        </td>
                        <td style="padding: 10px 0; text-align: right; font-weight: bold; color: #4CAF50;">
                            {amount_after_tax_formatted} CRN
                        </td>
                    </tr>
                    <tr style="border-bottom: 1px solid #eee;">
                        <td style="padding: 10px 0; color: #666;">
                            Public Address:
                        </td>
                        <td style="padding: 10px 0; text-align: right; word-break: break-all;">
                            {sender_data['public_address']}
                        </td>
                    </tr>
                    {reason_html}
                    <tr>
                        <td style="padding: 10px 0; color: #666;">
                            Transaction ID:
                        </td>
                        <td style="padding: 10px 0; text-align: right; word-break: break-all;">
                            {transaction_id}
                        </td>
                    </tr>
                </table>
                <a class="button" href="{DISCORD_LINK}">
                    Visit Our Discord Server
                </a>
                <p>
                    Don't recognize this activity? Please contact customer support immediately.
                </p>
                <p>
                    Please check with the receiving platform or wallet as the transaction is already confirmed on our Global Transactions Channel on Discord.
                </p>
                <p>
                    This is an automated message, please do not reply.
                </p>
            </div>
            <div class="footer">
                <p>
                    Cryptonel Transaction
                </p>
                <div class="social-icons">
                    <a href="{DISCORD_LINK}">
                        <i class="fab fa-discord"></i>
                    </a>
                    <a href="{X_LINK}">
                        <i class="fab fa-twitter"></i>
                    </a>
                </div>
                <p>
                    To stay secure, setup 2FA
                </p>
                <p>
                    <span class="highlight">
                        Risk warning:
                    </span>
                    Cryptocurrency trading is subject to high market risk.
                </p>
                <p>
                    2025 cryptonel.online, All Rights Reserved
                </p>
            </div>
        </body>
    </html>
    """
