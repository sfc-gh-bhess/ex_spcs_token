import os
import sys
import argparse
import requests
import json
from pat_gen import PATGenerator

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
    parser.add_argument('--url', required=True, help="SPCS reqeust URL (including 'https://')")
    parser.add_argument('--method', required=False, help="HTTP method (GET, POST, etc)", default='GET')
    parser.add_argument('--data', required=False, help="Payload for HTTP request as a JSON string")
    parser.add_argument('--role', required=False, help="Snowflake ROLE to use")
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--patfile', required=False, help="Filename of PAT token")
    group.add_argument('--pat', required=False, help="PAT token to use")
    args = vars(parser.parse_args())

    pat = args['pat'] if args['pat'] else get_pat(args['patfile'] if args['patfile'] else get_pat_filename())
    if not pat:
        sys.exit("No PAT found")
    pat_generator = PATGenerator(account=args['account_url'], endpoint=args['url'], pat=pat, role=args['role'])
    auth_header = pat_generator.authorization_header
    headers = auth_header()
    reqargs = {k:v for k,v in args.items() if k in ('method', 'data', 'url')}
    resp = requests.request(headers=headers, **reqargs)
    print(json.dumps(resp.json(), indent=2))
