from flask import request, g

def before_api_request():
    g.source = {
        'client': '',
        'version': '',
    }
    if 'X-API-SOURCE' in request.headers:
        client_and_version = request.headers['X-API-SOURCE'].rsplit('/', maxsplit=1)
        if len(client_and_version) > 1 and any(c.isdigit() for c in client_and_version[1]):
            g.source['client'] = client_and_version[0]
            g.source['version'] = client_and_version[1]
        else:
            g.source['client'] = request.headers['X-API-SOURCE']
