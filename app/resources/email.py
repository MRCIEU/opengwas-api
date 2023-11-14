from flask import current_app
from flask_mail import Mail, Message


class Email:
    def __init__(self):
        self.mail = Mail(current_app)

    def send_verification_email(self, link, email_address, expiry_str):
        email = Message("Please verify your email address - IEU OpenGWAS", sender=("IEU OpenGWAS", "ieu-dataset-portal@bristol.ac.uk"), recipients=[email_address])
        email.html = 'Dear researcher,<br><br>Please visit this link to verify your email address: <br><br><a href="{}">{}</a><br><br>The link is valid until {}.<br><br>IEU OpenGWAS<br>University of Bristol'.format(link, link, expiry_str)
        print(email)

        self.mail.send(email)

        result = {
            'message': "An email has been sent to {} - please check your junk folder, or contact us if you have not received any after three attempts. The link will be valid until {}.".format(email_address, expiry_str)
        }
        return result
