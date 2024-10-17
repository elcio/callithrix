import json
import jinja2
from fastapi.templating import Jinja2Templates
from markupsafe import Markup


@jinja2.pass_context
def is_current_url(context, path, **params):
    request = context['request']
    scope = {
        'type': request.url_for(path, **params).scheme,
        'path': request.url_for(path, **params).path,
        'method': 'get',
    }
    match = request.scope['route'].matches(scope)
    if match[1]:
        return match[1]['path_params'] == request['path_params']


@jinja2.pass_context
def nav_item(context, text, path, _class="navbar-item", active_class='is-active', **params):
    request = context['request']
    if is_current_url(context, path, **params):
        _class += f" {active_class}"
    link = f'<a href="{request.url_for(path, **params)}" class="{_class}">{text}</a>'
    return Markup(link)


def fieldblock(label, content, tag='', tag_color='info', params={}):
    block = '<div class="field">'
    tag_html = ''
    if tag:
        tag_html = f'<span class="tag is-{tag_color} is-light">{tag}</span>'
    if label:
        block += f'''
        <div class="label is-flex" style="justify-content: space-between">
            <label>{label}</label>
            {tag_html}
        </div>'''
    block += f'''
        <div class="control" {" ".join([f"{k}=\"{v}\"" for k, v in params.items()])}>
            {content}
        </div>'''
    block += '</div>'
    return block

def change_password_field(name, label, required, placeholder, type, admin=False, T=lambda t: t, **kwargs):
    field = f'''
    <div class="field" x-data="{'{visible:false}'}">
        <div class="field">
            <label><input type="checkbox" x-model="visible">{T('Change Password')}</label>
        </div>
        <div x-show="visible">
            { '' if admin else password_field('current_'+name, 'Current '+label, required, placeholder, T, **kwargs) }
            { password_field(name, 'New '+label, required, placeholder, T, **kwargs) }
        </div>
    </div>
    '''
    return field


def select_field(name, label, required, placeholder, options, value=None, T=lambda t: t, **kwargs):
    options_html = ''
    for k, v in options:
        options_html += f'<option value="{k}" {"selected" if k==value else ""}>{v}</option>'
    field = f'''
        <div class="select">
            <select name="{name}" {required and 'required' or ''}>
                <option value="">{T(placeholder)}</option>
                {options_html}
            </select>
        </div>
    '''
    return fieldblock(T(label), field, T('Required') if required else '')


def checkbox_field(name, label, required, placeholder, value, T=lambda t: t, **kwargs):
    field = f'''
        <label class="checkbox" x-data="{'{value: '+('1' if value else '0')+'}'}">
            <input type="checkbox" value="1" {'checked' if value else ''} @click="value=0+$event.target.checked">
            {T(label)}
            <input type="hidden" name="{name}" value="{'1' if value else '0'}" x-model="value">
        </label>
    '''
    return fieldblock('', field, T('Required') if required else '')


def textarea_field(name, label, required, placeholder, value, T=lambda t: t, **kwargs):
    field = f'''
        <textarea
            name="{name}" class="textarea" {required and 'required' or ''}
            {' '.join([f'{k}="{v}"' for k, v in kwargs.items()])}
            @input="len=$event.target.value.length"
            placeholder="{T(placeholder)}">{value.replace('<', '&lt;')}</textarea>
    '''
    params = {}
    if 'maxlength' in kwargs:
        field += '''<p class="help is-info" x-bind:class="'help is-'+((len/max)>.95?'danger':((len/max)>.90?'warning':'info'))" x-text="len+' / '+max"></p>'''
        params['x-data'] = '{ max: %s, len: %s }' % (kwargs["maxlength"], len(value))
    return fieldblock(T(label), field, T('Required') if required else '', params=params)


def imageupload_field(name, label, required, placeholder, value, T, width=240, height=160, **kwargs):
    data = {
        'url': f"/optimage/{width}x{height}/{value}" if value else '',
        'hover': 0,
        'file': '',
        'clear': 0,
    }
    data = json.dumps(data).replace("'", "&#x27;")
    field = f'''
        <div class="columns is-desktop" x-data='{data}'>
            <template x-if="clear">
                <input type="hidden" name="{name}" value="">
            </template>
            <div class="column is-narrow">
                <div x-show="url" @mouseover="hover=1" @mouseout="hover=0" style="position:relative">
                    <img x-bind:src="url" style="width:{width}px;height:{height}px;object-fit:cover">
                    <a href="#" class="button is-danger is-small" x-show="hover"
                        style="position:absolute; bottom:10px; right:10px; z-index:1;"
                        @click.prevent="if(confirm('{T('Remove image?')}')){{url='';document.querySelector('#imgfile_{name}').value='';clear=1}}">{T('Remove')}</a>
                </div>
                <div class="box" x-show="!url"
                    style="height:{height}px;width:{width}px;display:flex;justify-content:center;align-items:center;"
                    ><span>{T('No Image')}</span></div>
            </div>
            <div class="column">
                <p>{T('Upload a new image')}</p>
                <input type="file" name="imgfile_{name}" id="imgfile_{name}" class="input"
                    @change="if($event.target.files[0])url=URL.createObjectURL($event.target.files[0])"
                    {'required' if (required and not value) else ''}>
            </div>
        </div>
    '''
    return fieldblock(T(label), field, T('Required') if required else '')


def password_field(name, label, required, placeholder, T=lambda t:t, **kwargs):
    field = f'''
        <div class="columns">
            <div class="column">
                <input
                    name="{name}" class="input" {required and 'required' or ''}
                    placeholder="{T(placeholder)}"
                    {' '.join([f'{k}="{v}"' for k, v in kwargs.items()])}
                    x-bind:type="visible ? 'text' : 'password'"
                    autocomplete="off"
                    >
            </div>
            <div class="column is-narrow">
                <button type="button" class="button" x-on:click="visible=!visible"
                x-text="visible?'{T('Hide Password')}':'{T('Show Password')}'">
                {T('Show Password')}</button>
            </div>
        </div>
    '''
    return fieldblock(T(label), field, T('Required') if required else '', params={'x-data': '{visible:false}'})


def common_field(name, label, required, placeholder, type, value, T=lambda t: t, **kwargs):
    field = f'''
        <input
            name="{name}" class="input" {required and 'required' or ''}
            type="{type}" placeholder="{T(placeholder)}" value="{value}"
            {' '.join([f'{k}="{v}"' for k, v in kwargs.items()])}
            >
    '''
    return fieldblock(T(label), field, T('Required') if required else '')


@jinja2.pass_context
def form_field(context, name, label=None, placeholder=None, type='text', required=False, value='', admin=False, relations=None, T=lambda t:t, **kwargs):
    if label is None:
        label = name.removesuffix('_id').capitalize()
    if placeholder is None:
        placeholder = label
    if name.endswith('_id') and name.removesuffix('_id') in relations:
        type = 'select'
    if type == 'password':
        field = password_field(name, label, required, placeholder, T, **kwargs)
    elif type == 'change-password':
        field = change_password_field(name, label, required, placeholder, type, admin, T, **kwargs)
    elif type == "hidden":
        field = f'''
            <input name="{name}" type="{type}" value="{value}">
        '''
    elif type == 'select':
        field = select_field(name, label, required, placeholder, value=value, options=relations[name.removesuffix('_id')], T=T, **kwargs)
    elif type == 'checkbox':
        field = checkbox_field(name, label, required, placeholder, value, T, **kwargs)
    elif type == 'textarea':
        field = textarea_field(name, label, required, placeholder, value, T, **kwargs)
    elif type == 'imageupload':
        field = imageupload_field(name, label, required, placeholder, value, T, **kwargs)
    else:
        field = common_field(name, label, required, placeholder, type, value, T, **kwargs)
    return Markup(field)


@jinja2.pass_context
def post_field(context, name, label=None, placeholder=None, type='text', required=False, admin=False, relations=None, T=lambda t: t, **kwargs):
    value = context['form'].get(name, kwargs.get('value', ''))
    if 'value' in kwargs:
        del kwargs['value']
    return form_field(context, name, label, placeholder, type, required, value, admin, relations, T, **kwargs)


@jinja2.pass_context
def post_form(context, form):
    return Markup(form.html(context))


@jinja2.pass_context
def flash(context):
    request = context['request']
    color = 'info'
    flash = request.session.get('flash')

    if isinstance(flash, tuple) or isinstance(flash, list) :
        color, flash = flash

    if flash:
        del request.session['flash']
        return Markup(f'''
        <div class="container" x-data="{'{ show: true }'}" x-show="show" x-init="setTimeout(()=>show=false,5000)">
            <div class="notification is-{color}">
                <button class="delete" x-on:click="show=false"></button>
                {flash}
            </div>
        </div>
        ''')
    return ''


env_globals = {
    'is_current_url': is_current_url,
    'nav_item': nav_item,
    'form_field': form_field,
    'post_field': post_field,
    'post_form': post_form,
    'flash': flash,
}


class SmartTemplates(Jinja2Templates):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.env.globals.update(env_globals)
