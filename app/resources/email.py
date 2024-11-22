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

        email = Message("Your temporary sign in link - IEU OpenGWAS", sender=("IEU OpenGWAS", "ieu-opengwas@bristol.ac.uk"), recipients=[email_address])
        email.html = 'Dear researcher,<br><br>Please visit this link to sign in to OpenGWAS: <br><br><a href="{}">{}</a><br><br>The link is valid until {}.<br><br>IEU OpenGWAS<br>University of Bristol'.format(link, link, expiry_str)

        try:
            self.mail.send(email)
        except Exception as e:
            print(e)
            raise Exception("Unable to send email. Please contact us.")

        result = {
            'message': "An email has been sent to {} - please check your junk folder, or contact us if you have not received anything after three attempts. The link will be valid until {}.".format(email_address, expiry_str)
        }
        return result
