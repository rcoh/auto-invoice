import configparser
import os
import sys
import subprocess
import datetime

import click
from prompt_toolkit import prompt
from prompt_toolkit.validation import Validator, ValidationError

from gmail import Gmail
from toggl import Toggl
from wrappers import Client, parse_date
from xero_wrapper import XeroWrapper

config = configparser.ConfigParser()
CONFIG_PATH = os.path.expanduser('~/.invoice/config.ini')
config.read(CONFIG_PATH)


def persist_config():
    with open(CONFIG_PATH, 'w') as f:
        config.write(f)


def prompt_choice(options):
    for (i, opt) in enumerate(options):
        print('{i}: {opt}'.format(i=i, opt=opt))
    while True:
        choice = input('Please select an option\n')
        try:
            choice = int(choice)
            options[choice]
            return choice
        except Exception:
            print('Invalid')
            continue


class ClientIdValidator(Validator):
    def validate(self, document):
        if not document.text.isalnum():
            raise ValidationError(message='Client names must be alphanumeric', cursor_position=len(document.text))


class DateValidator(Validator):
    def validate(self, document):
        try:
            parse_date(document.text)
        except ValueError:
            raise ValidationError(message='Expected date like 10/21/2017', cursor_position=len(document.text))


class NumberValidator(Validator):
    def validate(self, document):
        if not document.text.isnumeric():
            raise ValidationError(message='Expected a number')


class EmailAddressListValidator(Validator):
    def validate(self, document):
        addresses = document.text.split(',')
        for address in addresses:
            if not '@' in address:
                raise ValidationError(message=f'{address} is not a valid email address')


def load_simple_field(field_name, section_name, prompt_text, validator=None, persist=True, default=None):
    if not config.has_section(section_name):
        config.add_section(section_name)

    prompt_text = prompt_text + ': '
    if config.has_option(section_name, field_name):
        res = prompt(prompt_text, default=config.get(section_name, field_name), validator=validator)
    else:
        if default is None:
            res = prompt(prompt_text, validator=validator)
        else:
            res = prompt(prompt_text, default=default, validator=validator)
    config.set(section_name, field_name, str(res))
    if persist:
        persist_config()


@click.group()
def cli():
    pass


@cli.command()
def add_client():
    assert config.get('toggl', 'workspace_id')
    toggl = Toggl(config)
    xero = XeroWrapper(config)
    accounts = xero.accounts()
    client_name = prompt('Name this client: ', validator=ClientIdValidator())
    section_name = f'client.{client_name}'
    if not config.has_section(section_name):
        config.add_section(section_name)
    else:
        print('Updating existing section!')

    load_simple_field('display_name', section_name, 'Display name: ')

    print('Select a client')
    clients = toggl.list_clients()
    client = clients[prompt_choice([w['name'] for w in clients])]
    config.set(section_name, 'client_id', str(client['id']))
    config.set(section_name, 'workspace_id', str(client['wid']))
    persist_config()

    print('Select a Xero contact')
    contacts = xero.contacts()
    contact = contacts[prompt_choice([w['Name'] for w in contacts])]
    config.set(section_name, 'contact_id', contact['ContactID'])
    persist_config()

    print('Select a Xero account')
    accounts = xero.accounts()
    account = accounts[prompt_choice([w['Name'] for w in accounts])]
    config.set(section_name, 'account_code', account['Code'])
    persist_config()

    load_simple_field('last_invoice', section_name, 'Last invoice end date', DateValidator())
    load_simple_field('invoice_period_days', section_name, 'Invoice period (days)', NumberValidator())
    load_simple_field('rate_hourly', section_name, 'Rate (Hourly)', NumberValidator())
    load_simple_field('email_addresses', section_name, 'Email addresses (comma separated)', EmailAddressListValidator())


@cli.command()
def configure():
    toggl = Toggl(config)
    workspaces = toggl.list_workspaces()
    print('Available workspaces: ')
    workspace = workspaces[prompt_choice([w['name'] for w in workspaces])]
    config.set('toggl', 'workspace_id', str(workspace['id']))
    persist_config()

    load_simple_field('sender', 'email', 'Your email (for sending emails)', EmailAddressListValidator())
    load_simple_field('your_name', 'email', 'Your name (for signing emails)')
    load_simple_field('password', 'email', 'Your email password')
    load_simple_field('mail_server', 'email', 'Mail server', default='smtp.gmail.com')
    load_simple_field('smtp_port', 'email', 'SMTP port', default='587')
    gmail = Gmail(config)
    gmail.ensure_credentials()


def clients_to_be_invoiced():
    clients = [client for client in config.sections() if client.startswith('client.')]
    ret = []
    for client_header in clients:
        client = Client(config, client_header)
        if client.needs_invoice():
            ret.append(client)
    return ret

def next_invoices():
    clients = [client for client in config.sections() if client.startswith('client.')]
    ret = {}
    for client_header in clients:
        client = Client(config, client_header)
        next_date = client.next_invoice()
        ret[client.display_name] = next_date
    return ret
 

@cli.command()
def test_email():
    gmail = Gmail(config)
    gmail.send('rcoh@rcoh.me', 'test email', Gmail.email_text('https://www.google.com', 'Russell R Cohen'), 'test.pdf', 'test_more_complex.pdf')

@cli.command()
def send_invoices():
    clients_in_need = clients_to_be_invoiced()
    toggl = Toggl(config)
    xero = XeroWrapper(config)
    gmail = Gmail(config)
    gmail.assert_credentials()
    for client in clients_in_need:
        invoice_since, invoice_until = client.next_invoice_interval()
        print(
            f'Invoicing from {invoice_since} ({invoice_since.strftime("%A")}) to {invoice_until} ({invoice_until.strftime("%A")})')

        unnaccounted = toggl.check_for_unaccounted_time(client.workspace_id, invoice_since, invoice_until)
        if unnaccounted.work_hours != 0:
            print(f'Found {unnaccounted.work_hours}h of unaccounted time. Please remove or tag with a project before continuing.')
            sys.exit(1)
        summary = toggl.get_summary(client.workspace_id, client.client_id, since=invoice_since, until=invoice_until)
        if summary.work_hours > 0:
            print(f'{client} Total hours: {summary.work_hours:.2f}. Bill: ${summary.work_hours*client.rate_hourly}')
            input('OK?')
            pdf = toggl.get_summary_pdf(client.workspace_id, client.client_id, since=invoice_since, until=invoice_until)
            print(f'PDF: {pdf}')
            subprocess.call(['open', pdf])
            invoice = xero.invoice(client, summary.work_hours, invoice_since, invoice_until)
            print('Invoice created')
            link = xero.get_share_link(invoice)
            print(f'Link: {link}')
            input(f'Invoicing {client} (${link}).')
            gmail.send_invoice(client, invoice_since, invoice_until, link, pdf)
        client.set_last_invoice(invoice_until)
        persist_config()
        print('Invoice sent! Config updated.')
    else:
        print('No clients need invoicing!')
        print('Next invoice dates: ')
        today = datetime.date.today()       
        for name, date in sorted(next_invoices().items(), key=lambda kv: kv[1]):
            diff = date - today
            print(f'  {name}: {date} ({diff.days} days away)')


        


if __name__ == '__main__':
    cli()
