import pickle
import json
from json import JSONEncoder

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
    return {
        "statusCode": status, 'headers': {'Content-Type': 'application/json'},
        "body": json.dumps(data, cls=PythonObjectEncoder, sort_keys=True),
    }

