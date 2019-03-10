import configparser
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Tuple

import nylas
from nylas import APIClient
from nylas.client.errors import FileUploadError
from nylas.client.restful_models import File
from six import StringIO

from wrappers import Client


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


def patched_save(self):  # pylint: disable=arguments-differ
    print('running patched save')
    stream = getattr(self, "stream", None)
    if not stream:
        data = getattr(self, "data", None)
        if data:
            stream = StringIO(data)

    if not stream:
        message = (
            "File object not properly formatted, "
            "must provide either a stream or data."
        )
        raise FileUploadError(message=message)

    file_info = (
        self.filename,
        stream,
        self.content_type,
        {},  # upload headers
    )

    new_obj = self.api._create_resources(File, {"file": file_info})
    new_obj = new_obj[0]
    for attr in self.attrs:
        if hasattr(new_obj, attr):
            setattr(self, attr, getattr(new_obj, attr))


class Gmail:

    def __init__(self, config: configparser.RawConfigParser):
        self.sender = config.get('email', 'sender')
        self.your_name = config.get('email', 'your_name')
        self.nylas_client = APIClient(config.get('nylas', 'app_id'), config.get('nylas', 'app_secret'),
                                      config.get('nylas', 'token'))

    def assert_credentials(self):
        pass

    @staticmethod
    def email_text(invoice_url, your_name):
        return f'{invoice_url}<br>Thanks!<br>{your_name}<br>This invoice was generated automatically by https://github.com/rcoh/auto-invoice.'

    def send_invoice(self, client: Client, invoice_since, invoice_until, invoice_url, toggle_pdf_path, xero_pdf_path):
        subject = f'Invoice {invoice_since:%m/%d/%y}-{invoice_until:%m/%d/%y}'
        toggl_attach_name = f'hours_{invoice_since:%m-%d-%y}_to_{invoice_until:%m-%d-%y}.pdf'
        xero_attach_name = f'invoice_{invoice_since:%m-%d-%y}_to_{invoice_until:%m-%d-%y}.pdf'
        text = Gmail.email_text(invoice_url, self.your_name)

        recipients = client.email_addresses.split(',')
        self.send(recipients=recipients, subject=subject, message=text,
                  attachments=[(toggle_pdf_path, toggl_attach_name), (xero_pdf_path, xero_attach_name)])
        print("Email sent!")

    def send(self, recipients, subject, message, attachments: List[Tuple[str, str]]):  # attachment_path, attachment_name):
        # Create the attachment
        for attachment_path, attachment_name in attachments:
            myfile = self.nylas_client.files.create()
            myfile.content_type = 'application/pdf'
            myfile.filename = attachment_name
            with open(attachment_path, 'rb') as f:
                myfile.stream = f
                # To work around https://github.com/nylas/nylas-python/issues/95
                patched_save(myfile)

            myfile.filename = attachment_name
        # Create a new draft
        draft = self.nylas_client.drafts.create()
        if type(recipients) == str:
            recipients = [recipients]
        draft.to = [{'email': recipient} for recipient in recipients]
        draft.subject = subject
        draft.body = message
        draft.attach(myfile)

        # Send it
        try:
            draft.send()
        except nylas.client.errors.ConnectionError as e:
            print("Unable to connect to the SMTP server.")
        except nylas.client.errors.MessageRejectedError as e:
            print("Message got rejected by the SMTP server!")
            print(e.message)

            # Sometimes the API gives us the exact error message
            # returned by the server. Display it since it can be
            # helpful to know exactly why our message got rejected:
            print(e.server_error)
