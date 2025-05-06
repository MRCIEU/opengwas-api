from flask import current_app
from flask_mail import Mail, Message

from middleware import Validator


class Email:
    def __init__(self):
        self.mail = Mail(current_app)

    def send_signin_email(self, link, email_address, expiry_str):
        try:
            Validator('UserNodeSchema', partial=True).validate({'uid': email_address})
        except Exception:
            raise Exception("Invalid email address.")

        email = Message(
            subject="Your sign in link - IEU OpenGWAS",
            sender=("OpenGWAS", "info@opengwas.io"),
            recipients=[email_address],
            html=f'Dear researcher,<br><br>'
                 f'This is your unique link, which you can use to securely sign in to your OpenGWAS account without using a password: <br><br>'
                 f'<a href="{link}">{link}</a><br><br>'
                 f'The link is valid until {expiry_str}. Do not share this link with anyone else.<br><br>'
                 f'IEU OpenGWAS<br>'
                 f'University of Bristol<br><br>'
                 f'	Please do not reply to this message. This email was sent from a notification-only email address that cannot accept incoming emails.',
            extra_headers={
                'X-Priority': '1',
                'X-MSMail-Priority': 'High',
                'Importance': 'High'
            }
        )

        try:
            self.mail.send(email)
        except Exception as e:
            print(e)
            raise Exception("Unable to send email. Please contact us.")

        result = {
            'message': "An email has been sent to {} - please check your junk folder, or contact us if you have not received anything after three attempts. The link will be valid until {}.".format(email_address, expiry_str)
        }
        return result
