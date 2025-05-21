import argparse
import requests
import json
from keypair_gen import KeypairGenerator
from datetime import timedelta
from urllib.parse import urlparse

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--account_url', required=True, help="Account URL in the form of: <ORGNAME>-<ACCTNAME>.snowflakecomputing.com")
    parser.add_argument('--user', required=True, help="Snowflake USER associated with the private key")
    parser.add_argument('--endpoint', required=True, help="SPCS reqeust URL (including 'https://')")
    parser.add_argument('--keyfile', required=True, help="Filename of private key")
    parser.add_argument('--lifetime', required=False, help='The number of minutes during which the key will be valid.', default=59)
    parser.add_argument('--renewal_delay', required=False, help='The number of minutes from now after which the JWT generator should renew the JWT.', default=54)
    args = vars(parser.parse_args())

    lifetime = timedelta(minutes=args['lifetime'])
    renewal_delay = timedelta(minutes=args['renewal_delay'])
    endpoint_host = urlparse(args['endpoint']).hostname
    jwt_generator = KeypairGenerator(account=args['account_url'], user=args['user'], private_key=args['keyfile'], 
                                     endpoint=endpoint_host, lifetime=lifetime, renewal_delay=renewal_delay)
    auth_header = jwt_generator.authorization_header
    headers = auth_header()
    resp = requests.get(url=args['endpoint'], headers=headers)
    print(json.dumps(resp.json(), indent=2))
