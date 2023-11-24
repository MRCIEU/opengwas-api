import requests

from resources.globals import Globals


class GitHubUniversities:
    def __init__(self):
        self.api = Globals.app_config['providers']['github']['universities']['url']

    def search_by_domain(self, domain):
        try:
            results = requests.get(self.api, params={
                'domain': domain
            }).json()
        except Exception as e:
            raise Exception("Service unavailable. At the moment we cannot search for universities using the domain name. Please try again later.")

        if len(results) == 0:
            return []
        elif len(results) == 1:
            return {
                'gh_name': results[0]['name'],
                'gh_domains': results[0]['domains']
            }
        if len(results) > 1:
            raise Exception("Cannot identify your organisation using the domain name {} - too many choices.".format(domain))
