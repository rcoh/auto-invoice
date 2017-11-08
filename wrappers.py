import configparser
from datetime import date, timedelta, datetime


class Client(object):
    def __init__(self, config: configparser.RawConfigParser, section):
        self.workspace_id = config.getint(section, 'workspace_id')
        self.client_id = config.getint(section, 'client_id')
        self.invoice_period = config.getint(section, 'invoice_period_days')
        self.name = section[len('client.'):]
        self.rate_hourly = config.getint(section, 'rate_hourly')
        self.contact_id = config.get(section, 'contact_id')
        self.account_code = config.get(section, 'account_code')
        self.email_addresses = config.get(section, 'email_addresses')
        if config.has_option(section, 'last_invoice'):
            self.last_invoice = parse_date(config.get(section, 'last_invoice'))
        else:
            self.last_invoice = None

        self.config = config
        self.section = section

    def set_last_invoice(self, until):
        self.config.set(self.section, 'last_invoice', f'{until:%m/%d/%Y}')

    def next_invoice_interval(self):
        if self.last_invoice is None:
            print(f'Last_invoice undefined. Assuming {self.invoice_period} days ago.')
            self.last_invoice = date.today() - timedelta(days=self.invoice_period)
        return (self.last_invoice + timedelta(days=1), self.next_invoice_end())

    def next_invoice_end(self):
        if self.last_invoice is None:
            return None
        return self.last_invoice + timedelta(days=self.invoice_period)

    def needs_invoice(self):
        if self.next_invoice_end() is None:
            return True
        return date.today() > self.next_invoice_end()

    def __repr__(self):
        return f'Client[{self.name}]'


def parse_date(s):
    return datetime.strptime(s, '%m/%d/%Y').date()