# Programmatic Access to Snowpark Container Services
This repository demonstrates ways to programmatically access ingress
endpoints in Snowpark Container Services (SPCS).

At this time, the following methods exist to authenticate to SPCS ingress
endpoints:
1. Programmatic Access Tokens (PAT)
2. Keypair JWT

In both cases, the token (either the PAT or the JWT generated from the private key) 
need to be exchanged for a short-lived token at a Snowflake-hosted endpoint (`/oauth/token`).
In general, PAT is slightly simpler and probably should be your first choice.

## Package Installation
You can install directly from github with this command:
```
pip install git+https://github.com/sfc-gh-bhess/ex_spcs_token.git
```

To install directly from github via pipenv, use:
```
pipenv install git+https://github.com/sfc-gh-bhess/ex_spcs_token.git#egg=snowkey
```

## Programmatic Access Token
This method uses a PAT to access the endpoint in SPCS.

We need to exchange the JWT for a short-lived access token. 
We can do that at the Snowflake-hosted endpoint
`https://<ORGNAME>-<ACCTNAME>.snowflakecomputing.com/oauth/token`. To do this
we need to know the hostname of the endpoint in SPCS that we are trying to access
(of the form `<HASH>-<ORGNAME>-<ACCTNAME>.snowflakecomputing.app`).

These steps are encapsulated in a Python class at `snowkey/pat/pat_gen.py`
named `PATGenerator`. This class has a constructor that takes the following
arguments:
* `account` - the Snowflake account URL (of the form `<ORGNAME>-<ACCTNAME>.snowflakecomputing.com`)
* `endpoint` - the SPCS endpoint hostname (of the form `<HASH>-<ORGNAME>-<ACCTNAME>.snowflakecomputing.app`)
* `role` (optional) - The role to use when requesting the short-lived token
* `pat` - the PAT itself

For example:
```python
from snowkey.pat import PatGenerator

gen = PATGenerator(account='MYORG-MYACCT.snowflakecomputing.com', 
                    endpoint='SOMEHASH-MYORG-MYACCT.snowflakecomputing.app', 
                    role='MYROLE', 
                    pat='ey....')
```

This class has one method of interest, `authorization_header()`. 
Call this `authorization_header()` method before every request to 
the SPCS endpoint, and include the result in the headers. 

## Keypair JWT
This method generates a JWT using the private key for a user. 

In order to generate the JWT, we need a few bits of information:
* the Snowflake account URL (of the form `<ORGNAME>-<ACCTNAME>.snowflakecomputing.com)
* the user associated with the private key
* the filename for the private key
* (optional) the lifetime of the generated JWT
* (optional) the delay after which a new JWT should be generated (generally, a few minutes less than the `lifetime`)

Once the JWT is generated, we need to exchange the JWT for a 
short-lived access token. We can do that at the Snowflake-hosted endpoint
`https://<ORGNAME>-<ACCTNAME>.snowflakecomputing.com/oauth/token`. To do this
we need to know the hostname of the endpoint in SPCS that we are trying to access
(of the form `<HASH>-<ORGNAME>-<ACCTNAME>.snowflakecomputing.app`).

These steps are encapsulated in a Python class at `snowkey/keypair/keypair_gen.py`
named `KeypairGenerator`. This class has a constructor that takes the following
arguments:
* `account` - the Snowflake account URL (of the form `<ORGNAME>-<ACCTNAME>.snowflakecomputing.com`)
* `user` - the user associated with the private key
* `private_key` - the filename for the private key
* `password` - (optional) - the password for the private key file
* `lifetime` (optional) - the lifetime of the generated JWT
* `renewal_delay` (optional) - the delay after which a new JWT should be generated (generally, a few minutes less than the `lifetime`)
* `endpoint` - the SPCS endpoint hostname (of the form `<HASH>-<ORGNAME>-<ACCTNAME>.snowflakecomputing.app`)

For example:
```python
from snowkey.keypair import KeypairGenerator

gen = KeypairGenerator(account='MYORG-MYACCT.snowflakecomputing.com', 
                       user='MYUSER', 
                       private_key='/path/to/private_key.p8', 
                       endpoint='SOMEHASH-MYORG-MYACCT.snowflakecomputing.app')
```

This class has one method of interest, `authorization_header()`. 
Call this `authorization_header()` method before every request to 
the SPCS endpoint, and include the result in the headers. 

## Exmaple programs
There is a helper program to illustrate how to use these classes:
* `snowkey/spcs_request.py` - uses either a private key or a pat to perform an HTTP request to an SPCS endpoint.

To use it, run:
```bash
python -m snowkey.spcs_get --help
```

### Example: PAT
```bash
python -m snowkey.spcs_get --account_url 'MYORG-MYACCT.snowflakecomputing.com' \
 --endpoint 'https://mzbqa5c-myorg-myacct.snowflakecomputing.app/some/path' \
 --role MYROLE --patfile '/path/to/pat'
```

### Example: Private Key
```bash
python -m snowkey.spcs_get --account_url 'MYORG-MYACCT.snowflakecomputing.com' \
 --endpoint 'https://mzbqa5c-myorg-myacct.snowflakecomputing.app/some/path' \
 --keyfile '/path/to/private_key.p8' --user MYUSER
```

### Example: PAT POST with data
```bash
python -m snowkey.spcs_get --account_url 'MYORG-MYACCT.snowflakecomputing.com' \
 --endpoint 'https://mzbqa5c-myorg-myacct.snowflakecomputing.app/some/path' \
 --method "POST" --json '{"a": 1, "b": "one"}' --role MYROLE --patfile '/path/to/pat'
```
