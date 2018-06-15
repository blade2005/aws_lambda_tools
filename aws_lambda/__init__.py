import logging
import codecs
import pickle
import json
from json import JSONEncoder
import datetime
from base64 import b64decode
import six
from six.moves import configparser
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
    trans_table = _maketrans(
        u"\u201c\u201d\u2019\u2013\u2022\u2122" u"\u00ad\u00ae\u2013",
        "\"\"''* - -",
    )
    if text is None:
        return
    e_text = t_text = u_text = None
    try:
        if isinstance(text, str) and six.PY2:
            u_text = codecs.decode(text, "utf_8")
        elif six.PY3 and isinstance(text, bytes):
            u_text = codecs.decode(text, "utf_8")
        else:
            u_text = text
        t_text = u_text.translate(trans_table)
        e_text = codecs.encode(t_text, "utf_8")
        return e_text
    except (UnicodeDecodeError, UnicodeEncodeError, TypeError) as error:
        logging.critical(error)
        logging.critical("trans_table: %s", trans_table)
        logging.critical('text: "%s", type: %s', text, type(text))
        logging.critical('u_text: "%s", type: %s', u_text, type(u_text))
        logging.critical('t_text: "%s", type: %s', t_text, type(t_text))
        raise


def decrypt(blob):
    return (
        boto3.client("kms")
        .decrypt(CiphertextBlob=b64decode(blob))["Plaintext"]
        .decode("UTF-8")
    )


def ssm_get_config(ssm, parent_path, section):
    param_path = "/config/{}/{}".format(parent_path, section)
    resp = ssm.get_parameter(Name=param_path, WithDecryption=True)
    return json.loads(resp["Parameter"]["Value"])


def ssm_get(ssm, path):
    resp = ssm.get_parameter(Name=path, WithDecryption=True)
    return resp["Parameter"]["Value"]


def encrypted_get_config(
    api_stage, table_name="Configs", table_key="name", conf_key="conf"
):
    import functools

    ddb = dynamodb.DynamoDB()
    encrypted_config = ddb.get(table_name, table_key, api_stage)
    if encrypted_config:
        config_path = "/tmp/{}-config".format(api_stage)
        with open(config_path, "w") as outfile:
            decrypted_config = decrypt(encrypted_config[conf_key])
            outfile.write(decrypted_config)
        return functools.partial(get_config, config_path=config_path)
    else:
        raise Exception("Missing Config")


class PythonObjectEncoder(JSONEncoder):

    def default(self, obj):
        if isinstance(obj, (datetime.datetime, datetime.date)):
            return obj.isoformat()
        elif isinstance(
            obj, (list, dict, str, unicode, int, float, bool, type, type(None))
        ):
            return JSONEncoder.default(self, obj)
        else:
            logging.warning(
                "Unable to find matching encoder for type %s. Using pickle",
                str(type(obj)),
            )
            return {"_python_object": pickle.dumps(obj)}


def get_config(section, config_path="lambda.cfg"):
    """Retrieve config section from file."""
    config = configparser.ConfigParser()
    config.read(config_path)
    if config.has_section(section):
        cfg = dict(config.items(section))
        newcfg = {}
        for key, value in list(cfg.items()):
            if isinstance(value, (unicode, str)):
                if value.isdigit():
                    newcfg[key] = int(value)
                else:
                    newcfg[key] = value
            elif isinstance(value, list):
                newcfg[key] = [e.encode("utf-8") for e in value]
        return newcfg
    else:
        logging.info(
            "Missing section(%s) in configfile(%s)", section, config_path
        )


def generate_return(status, data):
    return generate_response(status, data)


RESPONSE_DEFAULT_HEADERS = {"Content-Type": "application/json"}


def generate_response(status, data, headers=None):
    if not headers:
        headers = RESPONSE_DEFAULT_HEADERS
    return {
        "statusCode": status,
        "headers": headers,
        "body": json.dumps(data, cls=PythonObjectEncoder, sort_keys=True),
    }


def true_bool(dct):
    if isinstance(dct, dict):
        for key, value in list(dct.items()):
            dct[key] = true_bool(value)
    elif isinstance(dct, tuple):
        dct = [true_bool(val) for val in dct]
    elif isinstance(dct, list):
        dct = [true_bool(val) for val in dct]
    elif isinstance(dct, (unicode, str)):
        if dct.lower() == "true":
            dct = True
        elif dct.lower() == "false":
            dct = False
    return dct


def decode_json(json_data):
    return json.loads(json_data, object_hook=true_bool)


def recode_str(string__):
    """Re-encode string if possible to unicode."""
    if string__ and six.PY3:
        return string__.encode("utf-8").decode("utf-8")
    elif string__ and (
        (six.PY2 and hasattr(string__, "encode")) or hasattr(string__, "encode")
    ):
        try:
            return string__.encode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError) as error:
            logging.critical(error)
            logging.info(string__)
    else:
        return string__


def recode_dict(dict__):
    """Re-encode dictionary values if possible to unicode."""
    for key, value in dict__.items():
        dict__[key] = recode_str(value)
    return dict__
