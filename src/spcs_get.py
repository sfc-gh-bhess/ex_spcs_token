import os
import sys
import argparse
import requests
import json
from pat.pat_gen import PATGenerator
from keypair.keypair_gen import KeypairGenerator
from datetime import timedelta
from urllib.parse import urlparse

def get_pat_filename():
    files = os.listdir()
    pat_files = [x for x in files if x.endswith('-token-secret.txt')]
    if len(pat_files) < 1:
        return None
    return pat_files[0]

def get_pat(pfname):
    if not pfname or not os.path.isfile(pfname):
        return None
    return open(pfname, 'r').read()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--account_url', required=True, help="Account URL in the form of: <ORGNAME>-<ACCTNAME>.snowflakecomputing.com")
    parser.add_argument('--endpoint', required=True, help="SPCS reqeust URL (including 'https://')")
    parser.add_argument('--role', required=False, help="Snowflake ROLE to use (optional, for use with PAT)")
    parser.add_argument('--user', required=False, help="Snowflake USER associated with the private key (required, for use with keypair)")
    parser.add_argument('--lifetime', required=False, help='The number of minutes during which the key will be valid.', default=59)
    parser.add_argument('--renewal_delay', required=False, help='The number of minutes from now after which the JWT generator should renew the JWT.', default=54)
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--patfile', required=False, help="Filename of PAT token")
    group.add_argument('--pat', required=False, help="PAT token to use")
    group.add_argument('--keyfile', required=False, help="Filename of private key")
    args = vars(parser.parse_args())

    if args['keyfile'] and not args['user']:
        sys.exit("If you supply a private key file, you must specify a user.")
    if args['pat'] or args['patfile']:
        pat = args['pat'] if args['pat'] else get_pat(args['patfile'] if args['patfile'] else get_pat_filename())
        if not pat:
            sys.exit("No PAT found")
        pat_generator = PATGenerator(account=args['account_url'], endpoint=args['endpoint'], pat=pat, role=args['role'])
        auth_header = pat_generator.authorization_header
    else:
        lifetime = timedelta(minutes=args['lifetime'])
        renewal_delay = timedelta(minutes=args['renewal_delay'])
        endpoint_host = urlparse(args['endpoint']).hostname
        jwt_generator = KeypairGenerator(account=args['account_url'], user=args['user'], private_key=args['keyfile'], 
                                         endpoint=endpoint_host, lifetime=lifetime, renewal_delay=renewal_delay)
        auth_header = jwt_generator.authorization_header

    headers = auth_header()
    resp = requests.get(url=args['endpoint'], headers=headers)
    print(json.dumps(resp.json(), indent=2))
