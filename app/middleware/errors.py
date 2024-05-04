from werkzeug.exceptions import Unauthorized, ServiceUnavailable

from . import limiter


def raise_error(key):
    if key == 'MISSING_TOKEN':
        with limiter.limiter.shared_limit(limit_value="100 per 1 minutes", scope='allowance_of_test_mode'):  # per IP
            raise Unauthorized("From 1st May 2024 you must provide a token (JWT) alongside most of your requests. Read more at https://api.opengwas.io/ and also check for the latest version at https://mrcieu.github.io/ieugwasr/")
    elif key == 'NO_UID':
        raise Unauthorized("Unable to get uid. Please provide your token.")
    elif key == 'NO_UID_OR_SOURCE':
        raise Unauthorized("Unable to get user source. Please provide your token.")

    raise ServiceUnavailable()
