from cryptography.fernet import Fernet

from resources.globals import Globals


class CryptographyTool:
    def __init__(self):
        self.fernet = Fernet(Globals.app_config['fernet']['key'])

    def encrypt(self, message):
        return self.fernet.encrypt(message.encode())

    def decrypt(self, message):
        return self.fernet.decrypt(message).decode()
