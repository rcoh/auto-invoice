import configparser
import os
import smtplib
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from oauth2client.file import Storage

from wrappers import Client

SCOPES = 'https://www.googleapis.com/auth/gmail.send'
CLIENT_SECRET_FILE = os.path.expanduser('~/.invoice/client_secret.json')
APPLICATION_NAME = 'Gmail API Python Quickstart'


def create_message_with_attachment(sender, to, subject, message_text, attachment_path, attachment_name):
    message = MIMEMultipart()
    message['to'] = to
    message['from'] = sender
    message['subject'] = subject

    msg = MIMEText(message_text)
    message.attach(msg)

    with open(attachment_path, 'rb') as fp:
        msg = MIMEBase('application', 'pdf')
        msg.set_payload(fp.read())
    encoders.encode_base64(msg)
    msg.add_header('Content-Disposition', 'attachment', filename=attachment_name)
    message.attach(msg)

    return message


class Gmail:
    def __init__(self, config: configparser.RawConfigParser):
        self.sender = config.get('email', 'sender')
        self.your_name = config.get('email', 'your_name')
        self.password = config.get('email', 'password')
        self.mailserver = config.get('email', 'mail_server')

    def assert_credentials(self):
        if not self.has_credentials():
            raise Exception('No Gmail credentials')

    def has_credentials(self):
        credential_path = os.path.expanduser('~/.invoice/gmail_token.json')

        store = Storage(credential_path)
        credentials = store.get()
        return credentials and not credentials.invalid

    def ensure_credentials(self):
        """Gets valid user credentials from storage.

        If nothing has been stored, or if the stored credentials are invalid,
        the OAuth2 flow is completed to obtain the new credentials.

        Returns:
            Credentials, the obtained credential.
        """
        with smtplib.SMTP('smtp.gmail.com', 587) as s:
            s.ehlo()
            s.starttls()
            s.ehlo()
            s.login(self.sender, self.password)
            s.close()

    def send_invoice(self, client: Client, invoice_since, invoice_until, invoice_url, pdf_path):
        subject = f'Invoice {invoice_since:%m/%d/%y}-{invoice_until:%m/%d/%y}'
        attach_name = f'hours_{invoice_since:%m-%d-%y}_to_{invoice_until:%m-%d-%y}.pdf'
        text = f'{invoice_url}\nThanks!\n{self.your_name}\nP.S: This invoice was generated automatically. If anything looks weird please let me know.'
        message = create_message_with_attachment(sender=self.sender,
                                                 to=client.email_addresses,
                                                 subject=subject,
                                                 message_text=text,
                                                 attachment_path=pdf_path,
                                                 attachment_name=attach_name)

        with smtplib.SMTP('smtp.gmail.com', 587) as s:
            s.ehlo()
            s.starttls()
            s.ehlo()
            s.login(self.sender, self.password),
            s.sendmail(self.sender, client.email_addresses, message.as_string())
            s.close()
        print("Email sent!")
