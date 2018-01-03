import json
import logging
from jinja2 import Environment, FileSystemLoader, select_autoescape
import zdesk
import aws_lambda

TEMPLATE_SUBJECTS = {}
BLACKLISTED_FIELDS = ['system::embeddable_last_seen']

def __convert_fields_to_dict(field_list):
    field_dict = {}
    for field in field_list:
        field_dict[field['id']] = field['value']
    return field_dict

def __prettify_custom_fields(ticket_info):
    ticket_info['ticket']['prettified_custom_fields'] = {}
    for f in ticket_info['ticket']['custom_fields']:
        field_name = aws_lambda.trans_text(TICKET_FIELDS[f['id']]['title'])
        ticket_info['ticket']['prettified_custom_fields'][field_name] = f['value']
    return ticket_info

def __clean_up_user_info(user):
    for field in list(user.keys()):
        if field in BLACKLISTED_FIELDS:
            del user[field]
            continue
        if isinstance(user[field], dict):
            for k in list(user[field].keys()):
                if k in BLACKLISTED_FIELDS:
                    del user[field][k]
    return user

def clean_up_user_info(user_info, singleton=True):
    removed_fields = ['count', 'next_page', 'previous_page']
    if 'users' in list(user_info.keys()) and isinstance(user_info['users'], list):
        if singleton:
            user_info['user'] = __clean_up_user_info(user_info['users'][0])
            removed_fields.append('users')
        else:
            user_info['users'] = [__clean_up_user_info(user) for user in user_info['users']]
    for k in removed_fields:
        if k in list(user_info.keys()):
            del user_info[k]
    return user_info

def __jinja_env():
    return Environment(
        loader=FileSystemLoader('templates'),
        autoescape=select_autoescape(['html', 'xml'])
    )

def __render_ticket_body(template_name, json_input):
    env = __jinja_env()
    template = env.get_template(template_name)
    json_input['json'] = json.dumps(json_input, indent=2, cls=aws_lambda.PythonObjectEncoder)
    return template.render(**json_input)


def __create_ticket_data(json_input, ticket):
    """Returns dictionary of data using when posting to ZenDesk to creating a ticket."""

    fields_copied_from_input = ['ticket_form_id', 'brand_id', 'group_id', 'description', 'subject']
    if 'template_name' in list(json_input.keys()):
        logging.info('Formatting for %s template', json_input['template_name'])
        ticket['comment'] = {'body': __render_ticket_body(json_input['template_name'], json_input)}
        if json_input['template_name'] in list(TEMPLATE_SUBJECTS.keys()):
            fields_copied_from_input.remove('subject')
            ticket['subject'] = TEMPLATE_SUBJECTS[json_input['template_name']].format(**json_input)
    else:
        fields_copied_from_input.append('comment')

    for field in fields_copied_from_input:
        if field in list(json_input.keys()):
            ticket[field] = json_input[field]

    if 'prettified_custom_fields' in list(json_input.keys()):
        ticket['custom_fields'] = []
        for title, value in list(json_input['prettified_custom_fields'].items()):
            field_id = TICKET_FIELDS[title]['id']
            ticket['custom_fields'].append({'id': field_id, 'value': value})

    return {'ticket': ticket}

TICKET_FIELDS = None

class ZenDesk(object):
    def __init__(self, zdesk_email, zdesk_password, zdesk_url, zdesk_token):
        self.zendesk = zdesk.Zendesk(zdesk_email=zdesk_email,
                                     zdesk_password=zdesk_password,
                                     zdesk_url=zdesk_url,
                                     zdesk_token=zdesk_token)
    def __cache_ticket_fields(self, api_stage):
        global TICKET_FIELDS
        if not TICKET_FIELDS:
            import os
            ticket_fields_cache_file = '/tmp/{}-zendesk-fields.json'.format(api_stage)
            if (os.path.exists(ticket_fields_cache_file) and
                    os.stat(ticket_fields_cache_file).st_size != 0):
                with open(ticket_fields_cache_file, 'r') as infile:
                    TICKET_FIELDS = json.loads(infile.read())
            else:
                fields = self.zendesk.ticket_fields_list(get_all_pages=True)
                TICKET_FIELDS = {}
                for field in fields['ticket_fields']:
                    TICKET_FIELDS[field['id']] = field
                    TICKET_FIELDS[field['title']] = field
                with open(ticket_fields_cache_file, 'w') as outfile:
                    outfile.write(json.dumps(TICKET_FIELDS))

    def user_lookup(self, user_id):
        return self.zendesk.user_show(user_id)

    def user_name_lookup(self, user_id):
        user_info = self.user_lookup(user_id)
        return user_info['user']['name']

    def __add_names_for_ids(self, ticket_info):
        for field in ['author_id', 'submitter_id', 'assignee_id']:
            if field in list(ticket_info['ticket'].keys()) and ticket_info['ticket'][field]:
                ticket_info['ticket'][field.replace('_id', '')] = self.user_name_lookup(
                    ticket_info['ticket'][field])
        return ticket_info


    def munge_ticket_response(self, ticket_info):
        ticket_info = self.__add_names_for_ids(ticket_info)
        # ticket_info = __prettify_custom_fields(ticket_info)
        for key in ['custom_fields', 'fields']:
            if key in list(ticket_info['ticket'].keys()) and ticket_info['ticket'][key]:
                ticket_info['ticket'][key] = __convert_fields_to_dict(ticket_info['ticket'][key])
            else:
                logging.info('unable to find %s', key)
        return ticket_info

