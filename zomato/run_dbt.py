
import sys
import snowflake.connector

original_connect = snowflake.connector.connect

def connect_without_cache(*args, **kwargs):
    kwargs["client_store_temporary_credential"] = False
    kwargs["client_request_mfa_token"] = False
    return original_connect(*args, **kwargs)

snowflake.connector.connect = connect_without_cache

from dbt.cli.main import dbtRunner

args = sys.argv[1:] or ["debug"]
result = dbtRunner().invoke(args)

sys.exit(0 if result.success else 1)
