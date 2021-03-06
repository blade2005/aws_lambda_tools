import collections
import pyforce
from urlparse import urlparse


def init_sf(url, username, password, token):
    """Connect to Salesforce"""
    conn = pyforce.PythonClient(serverUrl=url)
    conn.login(username, "".join([password, token]))
    return conn


def flatten(d, parent_key="", sep="."):

    if isinstance(d, (list, tuple)):
        n_d = []
        for r in d:
            n_d.append(flatten(r))
        return n_d
    elif isinstance(d, dict):
        n_d = {}
        for k, v in list(d.items()):
            n_k = k
            if k.endswith("__r"):
                n_k = k.rstrip("__r")
            n_d[n_k] = flatten(v)
        return n_d
    else:
        return d
    return d


def execute_query(conn, query):
    records = []
    results = conn.query(query)
    query_locator = results["queryLocator"]
    done = results["done"]
    records.extend([flatten(r) for r in results["records"]])
    while not done:
        results = conn.queryMore(query_locator)
        query_locator = results["queryLocator"]
        done = results["done"]
        records.extend([flatten(r) for r in results["records"]])
    return records


def get_sfdc_instance_name(conn):
    (scheme, host, path, params, query, frag) = urlparse(
        conn._Client__serverUrl
    )
    return "{}://{}".format(scheme, host)
