import os


class Config(object):
    DEBUG = True
    TESTING = False
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'DEBUG')
    FBAPI_SCOPE = []
    FBAPI_APP_ID = os.environ.get('FACEBOOK_APP_ID')
    FBAPI_APP_SECRET = os.environ.get('FACEBOOK_SECRET')
