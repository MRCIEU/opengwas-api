from werkzeug.exceptions import Unauthorized, ServiceUnavailable

from . import limiter


# TODO: store error context to Redis etc. (w/ TTL) under UUID key and return the key to users
def raise_error(key):
    match key:
        case 'MISSING_TOKEN':
            with limiter.limiter.shared_limit(limit_value="100 per 1 minutes", scope='allowance_of_test_mode'):  # per IP
                raise Unauthorized("ERROR - Go to https://api.opengwas.io/ - From 1st May 2024 you must provide a token (JWT) alongside most of your requests. Read more at https://api.opengwas.io/ and also check for the latest version at https://mrcieu.github.io/ieugwasr/")
        case 'NO_UID':
            raise Unauthorized("Unable to get uid. Please provide your token.")
        case 'NO_UID_OR_SOURCE':
            raise Unauthorized("Unable to get user source. Please provide your token.")
        case 'NO_PRIVILEGE':
            raise Unauthorized("You do not have the privilege to access this resource.")
        case 'MISSING_KEY':
            raise Unauthorized("Missing or invalid key.")
        case 'INVALID_ACCOUNT':
            raise Unauthorized("ERROR - Please try again.")

    raise ServiceUnavailable()
