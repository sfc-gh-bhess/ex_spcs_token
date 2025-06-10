import os
import requests
from urllib.parse import urlparse
from typing import Text
from datetime import datetime
import jwt
import logging
from typing import Text

logger = logging.getLogger(__name__)

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

        logger.info(
            """Creating PATGenerator with arguments
            account : %s, endpoint : %s, role : %s""",
            account, endpoint, role)

        self.account = account.replace('_', '-')
        self.endpoint = endpoint        
        self.pat = open(pat, 'r').read() if os.path.isfile(pat) else pat
        self.role = role
        self.token = None
        self.renew_time = datetime.now()

    def _get_new_token(self) -> Text:
        return self._exchange_response().text
    
    def _exchange_response(self) -> requests.models.Response:
        endpoint_host = urlparse(self.endpoint).hostname
        scope = f'session:scope:{self.role.upper()} {endpoint_host}' if self.role else f'{endpoint_host}'
        data = {
            'grant_type': GRANT_TYPE,
            'scope': scope,
            'subject_token': self.pat,
            'subject_token_type': SUBJECT_TOKEN_TYPE
        }
        logger.info(data)
        url = f'https://{self.account}{TOKEN_EXCHANGE_PATH}'
        logger.info("oauth url: %s" %url)
        response = requests.post(url=url, data=data)
        logger.info("snowflake pat : %s" % response.text)
        assert 200 == response.status_code, f"unable to get snowflake token: {response.text}"
        return response

    def get_token(self) -> Text:
        now = datetime.now()
        if self.token is None or self.renew_time <= now:
            logger.info("Getting new access token because the present time (%s) is later than the renewal time (%s)",
                        now, self.renew_time)
            self.token = self._get_new_token()
            jwt_details = jwt.decode(self.token, options={"verify_signature": False})
            self.renew_time = datetime.fromtimestamp(jwt_details['exp'])
        return self.token

    def authorization_header(self) -> dict:
        return {'Authorization': f'Snowflake Token="{self.get_token()}"'}
