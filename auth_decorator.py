from functools import wraps
from flask import request, Response
from util.common_util import CommonUtil


def authenticate(message):
    """Sends a 401 response that enables basic auth"""
    return Response(
    message, 401,
    {'WWW-Authenticate': 'Basic realm="Login Required"'})

def authorize_request(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.headers.get('authorization')
        if not auth:
            return authenticate("Auth token is not specified.")
        if auth != CommonUtil.get_auth_id():
            return authenticate("Invalid auth token.")
        return f(*args, **kwargs)
    return decorated