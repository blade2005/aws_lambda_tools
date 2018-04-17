import json
from jinja2 import Environment, select_autoescape
from jinja2_s3loader import S3loader
from tabulate import tabulate
import aws_lambda

def make_table(rows, headers="keys", tablefmt='psql', exclude_keys=None, required_key=None):
    # list of dicts as an input
    if exclude_keys and isinstance(exclude_keys, (tuple, list)):
        for idx, _ in enumerate(rows):
            for key in exclude_keys:
                if key in rows[idx]:
                    del rows[idx][key]
    if required_key and isinstance(required_key, str):
        for idx, _ in enumerate(rows):
            for key in exclude_keys:
                if key in rows[idx]:
                    del rows[idx][key]


    return tabulate(rows, headers=headers, tablefmt=tablefmt)

def jinja_env(template_dir, s3_bucket):
    env = Environment(
        loader=S3loader(bucket=s3_bucket, prefix=template_dir),
        autoescape=select_autoescape(['html', 'xml'])
    )
    env.filters['tabulate'] = make_table
    return env

def render_template(env, template_name, input_args):

    template = env.get_template(template_name)
    if 'json' not in input_args.keys():
        input_args['json'] = json.dumps(input_args, cls=aws_lambda.PythonObjectEncoder)
    return template.render(**input_args)


