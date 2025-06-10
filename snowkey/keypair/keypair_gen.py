from cryptography.hazmat.primitives.serialization import load_pem_private_key
from cryptography.hazmat.primitives.serialization import Encoding
from cryptography.hazmat.primitives.serialization import PublicFormat
from cryptography.hazmat.backends import default_backend
from datetime import timedelta, timezone, datetime
from urllib.parse import urlparse
import base64
from getpass import getpass
import hashlib
import logging
import jwt
import requests
from typing import Text

logger = logging.getLogger(__name__)

ISSUER = "iss"
EXPIRE_TIME = "exp"
ISSUE_TIME = "iat"
SUBJECT = "sub"
TOKEN_EXCHANGE_PATH = '/oauth/token'
GRANT_TYPE = 'urn:ietf:params:oauth:grant-type:jwt-bearer'

def get_private_key_passphrase():
    return getpass('Passphrase for private key: ')

class KeypairGenerator(object):
    """
    Creates and signs a JWT with the specified private key file, username, and account identifier. The JWTGenerator keeps the
    generated token and only regenerates the token if a specified period of time has passed. It then exchanges the 
    JWT for a short-lived token to be used for SPCS ingress.
    """
    LIFETIME = timedelta(minutes=59)  # The tokens will have a 59 minute lifetime
    RENEWAL_DELTA = timedelta(minutes=54)  # Tokens will be renewed after 54 minutes
    ALGORITHM = "RS256"  # Tokens will be generated using RSA with SHA256

    def __init__(self, account: Text, user: Text, private_key: Text, endpoint: Text, password: Text = None,
                 lifetime: timedelta = LIFETIME, renewal_delay: timedelta = RENEWAL_DELTA):
        """
        __init__ creates an object that generates JWTs for the specified user, account identifier, and private key.
        :param account: Your Snowflake account URL (<ORGNAME>-<ACCTNAME>.snowflakecomputing.com)
        :param user: The Snowflake username.
        :param private_key: Private key file used for signing the JWTs.
        :param endpoint: The endpoint you are trying to access (just the hostname here: <HASH>-<ORGNAME>-<ACCTNAME>.snowflakecomputing.app)
        :param password: (optional) Password for the private key file (if applicable).
        :param lifetime: (optional) The number of minutes (as a timedelta) during which the key will be valid.
        :param renewal_delay: (optional) The number of minutes (as a timedelta) from now after which the JWT generator should renew the JWT.
        """

        logger.info(
            """Creating KeypairGenerator with arguments
            account : %s, user : %s, endpoint : %s, lifetime : %s, renewal_delay : %s""",
            account, user, endpoint, lifetime, renewal_delay)

        # Construct the fully qualified name of the user in uppercase.
        self.account_url = account.replace('_', '-')
        self.account = self._prepare_account_name_for_jwt(account)
        self.user = user.upper()
        self.qualified_username = self.account + "." + self.user

        self.lifetime = lifetime
        self.renewal_delay = renewal_delay
        self.jwt_renew_time = datetime.now(timezone.utc)
        self.jwt_token = None
        pemlines = open(private_key, 'rb').read()
        self.private_key = load_pem_private_key(pemlines, password, default_backend())
        self.endpoint = endpoint
        self.token = None
        self.renew_time = datetime.now(timezone.utc)

    def _prepare_account_name_for_jwt(self, raw_account: Text) -> Text:
        """
        Prepare the account identifier for use in the JWT.
        For the JWT, the account identifier must not include the subdomain or any region or cloud provider information.
        :param raw_account: The specified account identifier. 
        :return: The account identifier in a form that can be used to generate JWT.
        """
        account = raw_account
        if not '.global' in account:
            # Handle the general case.
            idx = account.find('.')
            if idx > 0:
                account = account[0:idx]
        else:
            # Handle the replication case.
            idx = account.find('-')
            if idx > 0:
                account = account[0:idx]
        # Use uppercase for the account identifier.
        return account.upper()

    def _generate_jwt(self) -> Text:
        """
        Generates a new JWT. If a JWT has been already been generated earlier, return the previously generated token unless the
        specified renewal time has passed.
        :return: the new token
        """
        now = datetime.now(timezone.utc)  # Fetch the current time

        # If the token has expired or doesn't exist, regenerate the token.
        if self.jwt_token is None or self.jwt_renew_time <= now:
            logger.info("Generating a new token because the present time (%s) is later than the renewal time (%s)",
                        now, self.jwt_renew_time)
            # Calculate the next time we need to renew the token.
            self.jwt_renew_time = now + self.renewal_delay

            # Prepare the fields for the payload.
            # Generate the public key fingerprint for the issuer in the payload.
            public_key_fp = self._calculate_public_key_fingerprint(self.private_key)

            # Create our payload
            payload = {
                # Set the issuer to the fully qualified username concatenated with the public key fingerprint.
                ISSUER: self.qualified_username + '.' + public_key_fp,

                # Set the subject to the fully qualified username.
                SUBJECT: self.qualified_username,

                # Set the issue time to now.
                ISSUE_TIME: now,

                # Set the expiration time, based on the lifetime specified for this object.
                EXPIRE_TIME: now + self.lifetime
            }

            # Regenerate the actual token
            token = jwt.encode(payload, key=self.private_key, algorithm=KeypairGenerator.ALGORITHM)
            # If you are using a version of PyJWT prior to 2.0, jwt.encode returns a byte string, rather than a string.
            # If the token is a byte string, convert it to a string.
            if isinstance(token, bytes):
              token = token.decode('utf-8')
            self.jwt_token = token
            logger.info("Generated a JWT with the following payload: %s", jwt.decode(self.jwt_token, key=self.private_key.public_key(), algorithms=[KeypairGenerator.ALGORITHM]))

        return self.jwt_token

    def _calculate_public_key_fingerprint(self, private_key: Text) -> Text:
        """
        Given a private key in PEM format, return the public key fingerprint.
        :param private_key: private key string
        :return: public key fingerprint
        """
        # Get the raw bytes of public key.
        public_key_raw = private_key.public_key().public_bytes(Encoding.DER, PublicFormat.SubjectPublicKeyInfo)

        # Get the sha256 hash of the raw bytes.
        sha256hash = hashlib.sha256()
        sha256hash.update(public_key_raw)

        # Base64-encode the value and prepend the prefix 'SHA256:'.
        public_key_fp = 'SHA256:' + base64.b64encode(sha256hash.digest()).decode('utf-8')
        logger.info("Public key fingerprint is %s", public_key_fp)

        return public_key_fp
    
    def _token_exchange(self, token) -> Text:
        return self._exchange_response(token).text
    
    def _exchange_response(self, token) -> requests.models.Response:
        scope = self.endpoint
        data = {
            'grant_type': GRANT_TYPE,
            'scope': scope,
            'assertion': token,
        }
        logger.info(data)
        url = f'https://{self.account_url}{TOKEN_EXCHANGE_PATH}'
        logger.info("oauth url: %s" %url)
        response = requests.post(url=url, data=data)
        logger.info("snowflake jwt : %s" % response.text)
        assert 200 == response.status_code, "unable to get snowflake token"
        return response.text
    
    def get_token(self) -> Text:
        now = datetime.now()
        if self.token is None or self.renew_time <= now:
            logger.info("Getting new access token because the present time (%s) is later than the renewal time (%s)",
                        now, self.renew_time)
            jwt_token = self._generate_jwt()
            self.token = self._token_exchange(jwt_token)
            jwt_details = jwt.decode(self.token, options={"verify_signature": False})
            self.renew_time = datetime.fromtimestamp(jwt_details['exp'])
        return self.token

    def authorization_header(self) -> dict:
        return {'Authorization': f'Snowflake Token="{self.get_token()}"'}
