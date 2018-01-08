import requests
import tempfile

class Summary:
    def __init__(self, json):
        work_hours_raw = (json['total_grand'] or 0) / 1000 / 60 / 60
        self.work_hours = round(work_hours_raw, 2)
        self.underlying = json

class Toggl:
    BASE_URL = "https://www.toggl.com/api/v8"
    REPORTS_URL = "https://toggl.com/reports/api/v2"

    def __init__(self, config):
        self.api_token = config.get('toggl', 'api_token')
        settings = {
            'token': self.api_token,
            'user_agent': 'autoinvoice'
        }

    def query(self, url):
        headers = {'content-type': 'application/json'}
        auth = (self.api_token, 'api_token')
        resp = requests.get(self.BASE_URL + url, headers=headers, auth=auth)
        return resp.json()

    def query_reports(self, url, params):
        headers = {'content-type': 'application/json'}
        auth = (self.api_token, 'api_token')
        resp = requests.get(self.REPORTS_URL + url, headers=headers, auth=auth, params=params)
        return resp



    def list_workspaces(self):
        return self.query('/workspaces')

    def list_clients(self):
        return self.query('/clients')

    def check_for_unaccounted_time(self, workspace_id, since, until):
        since_str = since.isoformat()
        until_str = until.isoformat()
        return Summary(self.query_reports('/summary', params={'user_agent': 'autoinvoice',
                                                              'workspace_id': workspace_id,
                                                              'project_ids': '0',
                                                              'since': since_str,
                                                              'until': until_str}).json())

    def get_summary(self, workspace_id, client_id, since, until):
        since_str = since.isoformat()
        until_str = until.isoformat()
        return Summary(self.query_reports('/summary', params={'user_agent': 'autoinvoice',
                                                              'workspace_id': workspace_id,
                                                              'client_ids': client_id,
                                                              'since': since_str,
                                                              'until': until_str}).json())

    def get_summary_pdf(self, workspace_id, client_id, since, until):
        since_str = since.isoformat()
        until_str = until.isoformat()
        result = self.query_reports('/summary.pdf', params={'user_agent': 'autoinvoice',
                                                              'workspace_id': workspace_id,
                                                              'client_ids': client_id,
                                                              'since': since_str,
                                                              'until': until_str})

        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as f:
            f.write(result.content)
        return f.name


