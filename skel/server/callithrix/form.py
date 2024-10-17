import re
from .jinja import post_field
from pydantic import EmailStr, SecretStr

class Form(dict):
    def __init__(self, *fields, action="Save", method="POST", admin=False, relations=None,
                 readonly=False, T=lambda t:t, template=None, _class="box", extra_buttons=()):
        self.fields = {field['name']: field for field in fields}
        self.action = action
        self.method = method
        self.admin = admin
        self.relations = relations
        self.readonly = readonly
        self.template = template
        self._class = _class
        self.extra_buttons = extra_buttons
        self.T = T
        dict.__init__(self, action=action, method=method, admin=admin, readonly=readonly, fields=self.fields)

    def html(self, context):
        fields = {
            name: post_field(context, admin=self.admin, relations=self.relations, T=self.T, **field)
            for name, field in self.fields.items()
        }

        html = f'''
            <form method="{self.method}" {'enctype="multipart/form-data" ' if self.method.lower()=='post' else ''}class="{self._class}">'''
        if self.template:
            with open(self.template) as f:
                template = f.read()
            template = re.sub(r'\{\{ *', '__START__', template)
            template = re.sub(r' *\}\}', '__END__', template)
            template = template.replace('{', '{{').replace('}', '}}')
            template = template.replace('__START__', '{').replace('__END__', '}')
            html += template.format(form_method=self.method, form_readonly=self.readonly, **fields)
        else:
            html += ''.join(fields.values())
            if not self.readonly:
                html += f'''<div class="control columns">
                            <div class="column">
                                <button class="button is-link">{self.T(self.action)}</button>
                            </div>
                            <div class="column is-narrow">
                                {''.join(self.extra_buttons)}
                            </div>
                        </div>'''
        html += '</form>'

        return html


class ModelForm(Form, dict):
    def __init__(self, model, action="Save", method="POST", admin=False, relations=None, readonly=False,
                 T=lambda t: t, template=None, _class="box", extra_buttons=()):
        self.model = model
        Form.__init__(self, action=action, method=method, admin=admin, relations=relations,
                      readonly=readonly, T=T, template=template, _class=_class)
        for name, field in model.model_fields.items():
            if self.admin or not (field.json_schema_extra and field.json_schema_extra.get('internal')):
                self.fields[name] = self.field_dict(name, field)

    def load(self, data):
        for field in self.fields.values():
            if field.get('type') == 'password':
                field['type'] = 'change-password'
                field['autocomplete'] = 'new-password'
                if 'required' in field:
                    del field['required']
            else:
                field['value'] = data.get(field['name'])
                if field['value'] is None:
                    field['value'] = ''

    def field_dict(self, name, field):
        fd = {
            'name': name,
            'label': self.T(field.json_schema_extra and field.json_schema_extra.get('label', '') or name.removesuffix('_id').replace('_', ' ').title()),
            'required': field.is_required(),
        }
        inputtype = field.json_schema_extra and field.json_schema_extra.get('inputtype')
        if inputtype:
            fd['type'] = inputtype
        elif field.annotation == EmailStr:
            fd['type'] = 'email'
        elif field.annotation == SecretStr:
            fd['type'] = 'password'
        elif field.annotation == bool:
            fd['type'] = 'checkbox'
        elif name == 'id':
            fd['type'] = 'hidden'
        for metadata in field.metadata:
            if 'max_length' in dir(metadata):
                fd['maxlength'] = metadata.max_length
        return fd

