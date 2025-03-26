import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.application import MIMEApplication
import os
from typing import List
from fastapi import HTTPException, BackgroundTasks
from pathlib import Path

class EmailConfig:
    # Gmail SMTP Configuration
    SMTP_SERVER = os.getenv('SMTP_SERVER')
    SMTP_PORT = os.getenv('SMTP_PORT')  # SSL Port
    
    # Gmail Credentials (Use App Password)
    EMAIL_ADDRESS = os.getenv("SMTP_EMAIL")
    EMAIL_PASSWORD = os.getenv("SMTP_PASSWORD")  # App password

class InstitutionEmailSender:
    def __init__(self):
        self.email = EmailConfig.EMAIL_ADDRESS
        self.password = EmailConfig.EMAIL_PASSWORD
        
    def send_institution_email(self, to_email: str, institution_name: str, registration_key: str, registration_url: str) -> bool:
        """Send email to institution"""
        try:
            msg = MIMEMultipart()
            msg["From"] = self.email
            msg["To"] = to_email
            msg["Subject"] = "KAUTHIG 2025 - INSTITUTION REGISTRATION"
            html_content = f"""
            <html>
                <body>
                        <p>Dear {institution_name},</p>
                        <p>This is official invitation for KAUTHIG 2025. We are excited to have you as part of our event.</p>
                        <p>Please find the registration key and Registration url below.</p>
                        <p>Registration Key: {registration_key}</p>
                        <p>Registration Url: {registration_url}</p>
                        <h5>Instructions:</h5>
                        <p>copy the registration key.</p>
                        <p>click on the registration url.</p>
                        <p>paste the registration key in the registration form on the 'YOUR KEY' field.</p>
                        <p>click on the register button.</p>
                        <p>you will be redirected to the registration form.</p>
                        <p>fill the form and submit.</p>
                        <p>you will receive a confirmation email.</p>
                        <p>If you have any questions, please feel free to contact us at <a href="mailto:{os.getenv('SMTP_EMAIL')}">{os.getenv('SMTP_EMAIL')}</a>.</p>
                        <p>Best regards,</p>
                        <p>VEER MADHO SINGH BHANDARI UTTARAKHAND TECHNICAL UNIVERSITY</p>
                        <p>KAUTHIG 2025</p>
                </body>
            </html>
            """
            msg.attach(MIMEText(html_content, "html"))
            
            server = smtplib.SMTP_SSL(EmailConfig.SMTP_SERVER, EmailConfig.SMTP_PORT)
            server.login(self.email, self.password)
            server.send_message(msg)
            server.quit()
            print(f"✅ Email sent successfully to {to_email}")
            return True
        
        except Exception as e:
            print(f"❌ Failed to send email: {str(e)}")
            return False

    def send_institution_email_background(self, background_tasks: BackgroundTasks, to_email: str, institution_name: str, registration_key: str, registration_url: str):
        """Add institution email sending to background tasks"""
        def send_email():
            success = self.send_institution_email(to_email, institution_name, registration_key, registration_url)
            if success:
                print(f"✅ Background email sent successfully to {to_email}")
            else:
                print(f"❌ Failed to send background email to {to_email}")

        background_tasks.add_task(send_email)

class sendConfirmationEmailInstitution:
    def __init__(self):
        self.email = EmailConfig.EMAIL_ADDRESS
        self.password = EmailConfig.EMAIL_PASSWORD
        
    def send_confirmation_email_institution(self, to_email: str, institution_name: str, login_id: str, password: str, registration_url: str) -> bool:
        """Send confirmation email to institution"""
        try:
            msg = MIMEMultipart()
            msg["From"] = self.email
            msg["To"] = to_email
            msg["Subject"] = "KAUTHIG 2025 - INSTITUTION REGISTRATION CONFIRMATION"
            html_content = f"""
            <html>
                <body>
                    <p>Dear {institution_name},</p>
                    <p>Thank you for your registration. We have received your registration and we are excited to have you as part of our event.</p>
                    <p>Please find the registration credentials and Student Registration url below.</p>
                    <h4>Your registration credentials are:</h4>
                    <p>LOGIN ID: {login_id}</p>
                    <p>PASSWORD: {password}</p>
                    <p>STUDENT REGISTRATION URL: {registration_url}</p>
                    <p>Please use the login id and password for register your student.</p>
                    <p>If you have any questions, please feel free to contact us at <a href="mailto:{os.getenv('SMTP_EMAIL')}">{os.getenv('SMTP_EMAIL')}</a>.</p>
                    <p>Best regards,</p>
                    <p>VEER MADHO SINGH BHANDARI UTTARAKHAND TECHNICAL UNIVERSITY</p>
                    <p>KAUTHIG 2025</p>
                </body>
            </html>
            """
            msg.attach(MIMEText(html_content, "html"))
            
            server = smtplib.SMTP_SSL(EmailConfig.SMTP_SERVER, EmailConfig.SMTP_PORT)
            server.login(self.email, self.password)
            server.send_message(msg)
            server.quit()
            print(f"✅ Email sent successfully to {to_email}")  
            return True
        
        except Exception as e:
            print(f"❌ Failed to send email: {str(e)}")
            return False

    def send_confirmation_email_institution_background(self, background_tasks: BackgroundTasks, to_email: str, institution_name: str, login_id: str, password: str, registration_url: str):
        """Add confirmation email sending to background tasks"""
        def send_email():
            success = self.send_confirmation_email_institution(to_email, institution_name, login_id, password, registration_url)
            if success:
                print(f"✅ Background confirmation email sent successfully to {to_email}")
            else:
                print(f"❌ Failed to send background confirmation email to {to_email}")

        background_tasks.add_task(send_email)

class InvitationEmailHandler:
    def __init__(self):
        self.email = EmailConfig.EMAIL_ADDRESS
        self.password = EmailConfig.EMAIL_PASSWORD
        
        if not all([self.email, self.password]):
            raise ValueError("Email credentials not configured")

    def send_welcome_email(
        self,
        to_email: str,
        user_name: str,
        qr_code_path: str,
        visitor_card_path: str
    ) -> bool:
        """Send welcome email with visitor card details and attachments"""
        try:
            from_email = os.getenv('SMTP_EMAIL')
            email_password = os.getenv('SMTP_PASSWORD')
            
            # Fix: Convert MAIL_COUNT to int before comparison
            mail_count = int(os.getenv('MAIL_COUNT', '0'))  # Default to 0 if not set
            
            if mail_count > 500 and mail_count <= 1000:
                from_email = os.getenv('SMTP_EMAIL2')
                email_password = os.getenv('SMTP_PASSWORD2')
            elif mail_count > 1000 and mail_count <= 1500:
                from_email = os.getenv('SMTP_EMAIL3')
                email_password = os.getenv('SMTP_PASSWORD3')

            msg = MIMEMultipart()
            msg["From"] = from_email
            msg["To"] = to_email
            msg["Subject"] = "Welcome to Kauthig 2025 - Your Visitor Card is Ready"

            # HTML Content
            html_content = f"""
            <html>
                <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                    <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px;">
                        <h1 style="text-align: center; color: #1a1a1a;">Welcome to Kauthig 2025</h1>
                        <div style="margin: 20px 0; line-height: 1.6;">
                            <p>Dear {user_name},</p>
                            <p>Welcome to Kauthig 2025! Your registration has been completed successfully.</p>
                            <p>Your visitor card and QR code are attached to this email.</p>
                            <p>Important Information:</p>
                            <ul>
                                <li>Keep your QR code handy for quick check-in</li>
                                <li>Your visitor card is your identity within the premises</li>
                                <li>Follow all safety guidelines and protocols</li>
                            </ul>
                            <p>Please find your visitor card and QR code attached to this email.</p>
                        </div>
                        <div style="text-align: center; color: #6c757d; font-size: 12px; margin-top: 20px; border-top: 1px solid #dee2e6; padding-top: 20px;">
                            <p>This is an automated message. Please do not reply to this email.</p>
                            <p>Kauthig 2025 Team</p>
                        </div>
                    </div>
                </body>
            </html>
            """

            msg.attach(MIMEText(html_content, "html"))

            # Attach Visitor Card
            if os.path.exists(visitor_card_path):
                with open(visitor_card_path, 'rb') as f:
                    visitor_card = MIMEImage(f.read())
                    visitor_card.add_header(
                        'Content-Disposition',
                        'attachment',
                        filename=f'visitor_card_{user_name}.png'
                    )
                    msg.attach(visitor_card)

            # Attach QR Code
            if os.path.exists(qr_code_path):
                with open(qr_code_path, 'rb') as f:
                    qr_code = MIMEImage(f.read())
                    qr_code.add_header(
                        'Content-Disposition',
                        'attachment',
                        filename=f'qr_code_{user_name}.png'
                    )
                    msg.attach(qr_code)

            try:
                # Connect to Gmail SMTP Server and Send Email
                server = smtplib.SMTP_SSL(EmailConfig.SMTP_SERVER, EmailConfig.SMTP_PORT)
                server.login(from_email, email_password)
                server.send_message(msg)
                server.quit()
                print(f"✅ Welcome email with attachments sent successfully to {to_email}!")
                
                # Update mail count safely
                new_count = str(mail_count + 1)
                os.environ['MAIL_COUNT'] = new_count

                return True
                
            except Exception as e:
                print(f"❌ SMTP Error: {str(e)}")
                return False

        except Exception as e:
            print(f"❌ Failed to send welcome email: {str(e)}")
            return False

def send_welcome_email_background(
    background_tasks: BackgroundTasks,
    user_email: str,
    user_name: str,
    qr_code_path: str,
    visitor_card_path: str
):
    """Add email sending to background tasks"""
    def send_email():
        try:
            email_handler = InvitationEmailHandler()
            success = email_handler.send_welcome_email(
                to_email=user_email,
                user_name=user_name,
                qr_code_path=qr_code_path,
                visitor_card_path=visitor_card_path
            )
            if success:
                print(f"✅ Background email with attachments sent successfully to {user_email}")
            else:
                print(f"❌ Failed to send background email to {user_email}")
        except Exception as e:
            print(f"❌ Background email task failed: {str(e)}")

    background_tasks.add_task(send_email) 