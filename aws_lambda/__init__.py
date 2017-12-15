import logging
import pickle
import json
from json import JSONEncoder
import datetime
import ConfigParser
from base64 import b64decode
import boto3

def decrypt(blob):
    return boto3.client('kms').decrypt(CiphertextBlob=b64decode(blob))['Plaintext'].decode('UTF-8')

class PythonObjectEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime.datetime, datetime.date)):
            return obj.isoformat()
        elif isinstance(obj, (list, dict, str, unicode, int, float, bool, type,
                              type(None))):
            return JSONEncoder.default(self, obj)
        return {'_python_object': pickle.dumps(obj)}

def get_config(section, config_path='lambda.cfg'):
    """Retrieve config section from file."""
    config = ConfigParser.ConfigParser()
    config.read(config_path)
    if config.has_section(section):
        cfg = dict(config.items(section))
        newcfg = {}
        for key, value in cfg.items():
            if isinstance(value, (unicode, str)):
                if value.isdigit():
                    newcfg[key] = int(value)
                else:
                    newcfg[key] = value
            elif isinstance(value, list):
                newcfg[key] = [e.encode('utf-8') for e in value]
        return newcfg
    else:
        logging.info(
            'Missing section(%s) in configfile(%s)', section, config_path)

def generate_return(status, data):
    return generate_response(status, data)

RESPONSE_DEFAULT_HEADERS = {'Content-Type': 'application/json'}

def generate_response(status, data, headers=None):
    if not headers:
        headers = RESPONSE_DEFAULT_HEADERS
    return {
        "statusCode": status, 'headers': headers,
        "body": json.dumps(data, cls=PythonObjectEncoder, sort_keys=True),
    }

def true_bool(dct):
    logging.info('Found obj of type: %s', type(dct))
    if isinstance(dct, dict):
        for key, value in dct.items():
            dct[key] = true_bool(value)
    elif isinstance(dct, tuple):
        dct = ([true_bool(val) for val in dct])
    elif isinstance(dct, list):
        dct = [true_bool(val) for val in dct]
    elif isinstance(dct, (str, unicode)):
        logging.info('Found obj of value: %s', dct)
        if dct == 'true':
            dct = True
        elif dct == 'false':
            dct = False
    return dct


def decode_json(json_data):
    return json.loads(json_data, object_hook=true_bool)
