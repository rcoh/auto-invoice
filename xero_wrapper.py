import configparser
import datetime
import os
from datetime import date
from datetime import timedelta

from xero import Xero
from xero.auth import PrivateCredentials
import requests

from wrappers import Client


class XeroWrapper:
    SECTION = 'xero'

    def __init__(self, config: configparser.RawConfigParser):
        self.consumer_key = config.get(self.SECTION, 'key')
        self.consumer_secret = config.get(self.SECTION, 'secret')
        with open(os.path.expanduser('~/.invoice/privatekey.pem')) as f:
            self.rsa_key = f.read()

        self.credentials = PrivateCredentials(self.consumer_key, self.rsa_key)
        self.xero = Xero(self.credentials)
        self.xero_url = config.get(self.SECTION, 'api_url')

    def contacts(self):
        return self.xero.contacts.all()

    def accounts(self):
        return self.xero.accounts.all()

    def invoice(self, client: Client, hours, since: datetime.date, until: datetime.date):
        open_invoices = self.xero.invoices.filter(
            Contact_ContactID=client.contact_id,
            Status='AUTHORISED'
        )
        matching_invoice = [invoice for invoice in open_invoices if hours * client.rate_hourly == invoice['Total']]
        if len(matching_invoice) == 1:
            if input('Warning! Probable matching invoice exists. Proceed with this invoice? y/n') == 'y':
                return matching_invoice[0]
        elif open_invoices and len(matching_invoice) == 0:
            if input('Warning! Open invoices exist for this client but the total is different. Create another?') != 'y':
                return open_invoices[0]
        elif len(matching_invoice) > 1:
            if input('Multiple matching invoices! Abort? y/n') == 'y':
                exit(1)


        due_date = date.today() + timedelta(days=14)

        invoice = dict(
            Type='ACCREC',
            Contact=dict(ContactID=client.contact_id),
            LineItems=[dict(
                Description=f'{client.name} contracting {since:%m/%d/%y} {until:%m/%d/%y}',
                Quantity=hours,
                UnitAmount=client.rate_hourly,
                AccountCode=client.account_code
            )],
            Status='AUTHORISED',
            DueDate=due_date
        )
        invoice = self.xero.invoices.put(invoice)

        return invoice[0]

    def get_share_link(self, invoice):
        'GET https://api.xero.com/api.xro/2.0/Invoices/9b9ba9e5-e907-4b4e-8210-54d82b0aa479/OnlineInvoice'
        resp = requests.get(
            f'{self.xero_url}Invoices/{invoice["InvoiceID"]}/OnlineInvoice',
            headers={'Accept': 'application/json'},
            auth=self.credentials.oauth
        ).json()
        print(resp)
        return resp['OnlineInvoices'][0]['OnlineInvoiceUrl']

