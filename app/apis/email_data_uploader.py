from pyo365 import Account
import logging
import re
from resources.globals import app_config
import flask

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')


class EmailDataUploader:

    def __init__(self):
        # TODO set up shared mailbox
        # TODO decide wording of templates
        # TODO auth without opening gui
        # TODO write tests

        raise NotImplemented

        self.account = Account(credentials=(app_config['CLIENT_ID'], app_config['CLIENT_SECRET']),
                               main_resource=app_config['SHARED_MAILBOX'])
        self.account.authenticate(scopes=[
            'https://graph.microsoft.com/Mail.Read',
            'https://graph.microsoft.com/Mail.Read.Shared',
            'https://graph.microsoft.com/Mail.ReadWrite',
            'https://graph.microsoft.com/Mail.ReadWrite.Shared',
            'https://graph.microsoft.com/Mail.Send',
            'https://graph.microsoft.com/Mail.Send.Shared',
            'https://graph.microsoft.com/User.Read'

        ])  # request a token for this scopes

        # this will ask to visit the app consent screen where the user will be asked to give consent on the requested scopes.
        # then the user will have to provide the result url afeter consent.
        # if all goes as expected, result will be True and a token will be stored in the default location.

    def send_to_submitter(self, study, qc, comments, address):
        logging.info("Emailing {}".format(address))

        if not EmailDataUploader.__is_valid_address(address):
            raise ValueError("Need to provide a valid email address")

        subject = 'Data you uploaded to MR Base'
        html = flask.render_template(
            'email.html',
            title='MR Base data upload',
            subject=subject,
            study=study,
            qc=qc,
            comments=comments
        )

        m = self.account.new_message()
        m.sender.address = app_config['SHARED_MAILBOX']
        m.to.add(address)
        m.subject = subject
        m.body = html
        m.body_type = 'HTML'
        m.send()

    @staticmethod
    def __is_valid_address(email):
        return len(email) > 7 and re.match(r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)",
                                           email) is not None
