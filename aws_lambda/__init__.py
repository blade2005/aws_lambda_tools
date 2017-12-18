import logging
import codecs
import pickle
import json
from json import JSONEncoder
import datetime
import ConfigParser
from base64 import b64decode
import six
import boto3
from . import dynamodb

def _maketrans(frm, _to):
    """Handle py2 ascii encoding."""
    if six.PY2:
        ord_map = dict([(ord(f), ord(t)) for f, t in zip(frm, _to)])
        ord_map[8482] = None
        ord_map[174] = None
        return ord_map
    else:
        return str.maketrans(frm, _to)  # pylint: disable=no-member


def trans_text(text):
    """Translate text into utf-8 characters."""
    # Translation must be 1 char to 1 char, if needing to delete or multiple
    #   character then modify _maketrans
    trans_table = _maketrans(u'\u201c\u201d\u2019\u2013\u2022\u2122'
                             u'\u00ad\u00ae\u2013',
                             '""\'\'* - -')
    if text is None:
        return
    e_text = t_text = u_text = None
    try:
        if isinstance(text, str) and six.PY2:
            u_text = codecs.decode(text, 'utf_8')
        elif six.PY3 and isinstance(text, bytes):
            u_text = codecs.decode(text, 'utf_8')
        else:
            u_text = text
        t_text = u_text.translate(trans_table)
        e_text = codecs.encode(t_text, 'utf_8')
        return e_text
    except (UnicodeDecodeError, UnicodeEncodeError, TypeError) as error:
        logging.critical(error)
        logging.critical('trans_table: %s', trans_table)
        logging.critical('text: "%s", type: %s', text, type(text))
        logging.critical('u_text: "%s", type: %s', u_text, type(u_text))
        logging.critical('t_text: "%s", type: %s', t_text, type(t_text))
        raise


def decrypt(blob):
    return boto3.client('kms').decrypt(CiphertextBlob=b64decode(blob))['Plaintext'].decode('UTF-8')

def encrypted_get_config(api_stage):
    import functools
    ddb = dynamodb.DynamoDB()
    encrypted_config = ddb.get('Configs', 'name', api_stage)
    if encrypted_config:
        config_path = '/tmp/{}-config'.format(api_stage)
        with open(config_path, 'w') as outfile:
            decrypted_config = decrypt(encrypted_config['data'])
            outfile.write(decrypted_config)
        return functools.partial(get_config, config_path=config_path)
    else:
        raise Exception('Missing Config')

class PythonObjectEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime.datetime, datetime.date)):
            return obj.isoformat()
        elif isinstance(obj, (list, dict, str, unicode, int, float, bool, type,
                              type(None))):
            return JSONEncoder.default(self, obj)
        else:
            logging.warning('Unable to find matching encoder for type %s. Using pickle', str(type(obj)))
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
    if isinstance(dct, dict):
        for key, value in dct.items():
            dct[key] = true_bool(value)
    elif isinstance(dct, tuple):
        dct = ([true_bool(val) for val in dct])
    elif isinstance(dct, list):
        dct = [true_bool(val) for val in dct]
    elif isinstance(dct, (str, unicode)):
        if dct == 'true':
            dct = True
        elif dct == 'false':
            dct = False
    return dct


def decode_json(json_data):
    return json.loads(json_data, object_hook=true_bool)
