import os
import requests
from urllib.parse import urlparse
from typing import Text
from datetime import timezone, datetime
import jwt

TOKEN_EXCHANGE_PATH = '/oauth/token'
GRANT_TYPE = 'urn:ietf:params:oauth:grant-type:token-exchange'
SUBJECT_TOKEN_TYPE = 'programmatic_access_token'

class PATGenerator:
    def __init__(self, account: Text, endpoint: Text, pat: Text, role: Text = None):
        """
        __init__ creates an object that uses the supplied PAT to get a token to access SPCS ingress endpoints.
        :param account: Your Snowflake account URL (<ORGNAME>-<ACCTNAME>.snowflakecomputing.com)
        :param endpoint: The endpoint you are trying to access (just the hostname here: <HASH>-<ORGNAME>-<ACCTNAME>.snowflakecomputing.app)
        :param pat: The PAT to use.
        :param role: The role to use when requesting the short-lived token (optional).
        """        
        self.account = account
        self.endpoint = endpoint        
        self.pat = open(pat, 'r').read() if os.path.isfile(pat) else pat
        self.role = role
        self.token = None
        self.renew_time = datetime.now()

    def _get_new_token(self) -> Text:
        endpoint_host = urlparse(self.endpoint).hostname
        scope = f'session:scope:{self.role.upper()} {endpoint_host}' if self.role else f'{endpoint_host}'
        data = {
            'grant_type': GRANT_TYPE,
            'scope': scope,
            'subject_token': self.pat,
            'subject_token_type': SUBJECT_TOKEN_TYPE
        }
        url = f'https://{self.account}{TOKEN_EXCHANGE_PATH}'
        resp = requests.post(url=url, data=data)
        return resp.text

    def get_token(self) -> Text:
        now = datetime.now()
        if self.token is None or self.renew_time <= now:
            self.token = self._get_new_token()
            jwt_details = jwt.decode(self.token, options={"verify_signature": False})
            self.renew_time = datetime.fromtimestamp(jwt_details['exp'])
        return self.token

    def authorization_header(self):
        return {'Authorization': f'Snowflake Token="{self.get_token()}"'}
