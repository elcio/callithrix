import time
import jinja2
import functools
from callithrix.optimage.app import app as imageserver
from fastapi import Request
from callithrix import jinja
from callithrix.form import ModelForm
from fastapi.responses import RedirectResponse


hidden_headers = ['created_at', 'updated_at', 'created_by', 'updated_by', 'password', 'validation_code']


@jinja2.pass_context
def db_table(context, table, rows, headers=None, readonly=False, T=lambda t:t, labels={}, max_cols=6, prefix='admin_'):
    request = context['request']
    if rows:
        if not headers:
            headers = [h for h in rows[0].keys() if h not in hidden_headers][:max_cols]
        tbody = ''
        for row in rows:
            tbody += '<tr>'
            for header in headers:
                tbody += f'<td><a href="{request.url_for(prefix+"edit", table=table, id=row["id"])}">{row[header]}</a></td>'
            tbody += '<td>'
            if (table!='user' or row['id']!=request.session.get('userid')) and not readonly:
                tbody += f'''
                    <a
                        href="{request.url_for(prefix+"delete", table=table, id=row["id"])}"
                        @click.prevent="if(confirm('{T('Are you sure you want to delete this record?')}')) location.href=$event.target.href"
                        class="button is-danger is-small">{T('Delete')}</a>
                '''
            tbody += '</td>'
            tbody += '</tr>'
        table = f'''
            <div class="table-container">
            <table class="table is-fullwidth is-striped is-hoverable" x-data="{'{}'}">
                <thead>
                    <tr>
                        {''.join([f'<th>{T(labels.get(header, header))}</th>' for header in headers])}
                        <th>&nbsp;</th>
                    </tr>
                </thead>
                <tbody>
                    {tbody}
                </tbody>
            </table>
            </div>
        '''
    return jinja.Markup(table)


jinja.env_globals['db_table'] = db_table


class Crud:
    def __init__(self, app, domain, name, path='/', tables=None, permissions=(),
                 filters={}, readonly=(), admin=False, defaults={}, form_templates={}):
        self.tables = tables
        self.permissions = permissions
        self.path = path.removesuffix('/')
        self.app = app
        self.filters = filters
        self.domain = domain
        self.name = name
        self.prefix = name + '_'
        self.readonly = readonly
        self.admin = admin
        self.defaults = defaults
        self.form_templates = form_templates

        self.plug(self.home, '/')
        self.plug(self.table, '/{table}')
        self.plug(self.new, '/{table}/new')
        self.plug(self.post_new, '/{table}/new', 'post', write=True)
        self.plug(self.edit, '/{table}/{id}')
        self.plug(self.post_edit, '/{table}/{id}', 'post', write=True)
        self.plug(self.delete, '/{table}/delete/{id}', write=True)

    def plug(self, fn, path, method='get', write=False):
        @self.app.requires(*self.permissions)
        @functools.wraps(fn)
        async def wrapper(request: Request, *args, **kwargs):
            T = self.app.getT(request)
            if 'table' in kwargs:
                if (self.tables and kwargs['table'] not in self.tables) or \
                   (kwargs['table'] in self.readonly and write):
                    request.session['flash'] = ('danger', T('You do not have permission to access this page.'))
                    return RedirectResponse(request.url_for(self.prefix+'home'), status_code=302)
            ret_val = await fn(request, *args, **kwargs)
            if isinstance(ret_val, dict):
                ret_val['prefix'] = self.prefix
                ret_val['readonly'] = self.readonly
            return ret_val
        fname = f'{self.name}_{fn.__name__}'
        dec=getattr(self.app, method+'html')
        dec(self.path + path, name=fname)(wrapper)

    def build_filters(self, request):
        filters = {}
        for table, fields in self.filters.items():
            filters[table] = {}
            for field, value in fields.items():
                filters[table][field] = value[0], value[1].format(**request.session)
        return filters

    def build_defaults(self, request):
        defaults = {}
        for table, fields in self.defaults.items():
            defaults[table] = {}
            for field, value in fields.items():
                defaults[table][field] = value.format(**request.session)
        return defaults

    async def select_options(self, request, table):
        entity = get_model(self.domain, table)
        filters = self.build_filters(request)
        rows = await self.app.repository.find(table, filters.get(table, {}))
        return [(row['id'], str(entity(**row))) for row in rows]

    async def get_relations(self, request, table):
        relations = {}
        entity = get_model(self.domain, table)
        for field in entity.model_fields:
            if field.endswith('_id'):
                field = field.removesuffix('_id')
                if (not self.tables or field in self.tables) and get_model(self.domain, field):
                    relations[field] = await self.select_options(request, field)
        return relations

    async def home(self, request: Request):
        if self.tables and len(self.tables) == 1:
            return RedirectResponse(request.url_for(self.prefix+'table', table=self.tables[0]), status_code=302)
        T = self.app.getT(request)
        return {'title':T('Admin page'), 'tables': self.tables or await self.app.repository.get_tables()}

    async def table(self, request: Request, table: str):
        T = self.app.getT(request)
        filters = self.build_filters(request)
        rows = await self.app.repository.find(table, filters.get(table, {}))
        rows = [await self.prepare_row(row) for row in rows]
        entity = get_model(self.domain, table)
        labels = {}
        for name, field in entity.model_fields.items():
            if field.json_schema_extra and field.json_schema_extra.get('label'):
                labels[name] = field.json_schema_extra['label']
            else:
                labels[name] = name.replace('_', ' ').title()
        return {'title': T(f'List of {table}'), 'rows': rows, 'table': table, 'labels': labels, 'total_tables': len(self.tables or [])}

    async def prepare_row(self, row):
        prepared = {}
        for k, v in row.items():
            if k in hidden_headers:
                continue
            if k.endswith('_id'):
                m = get_model(self.domain, k.removesuffix('_id'))
                if m:
                    k = k.removesuffix('_id')
                    obj = await self.app.repository.get(k, v)
                    if obj:
                        v = str(m(**obj))
            prepared[k] = v
        return prepared

    async def new(self, request: Request, table: str):
        T = self.app.getT(request)
        relations = await self.get_relations(request, table)
        the_form = ModelForm(get_model(self.domain, table), action=T('Save'), admin=self.admin, relations=relations,
                             readonly=(table in self.readonly), T=T, template=self.form_templates.get(table))
        rows = await self.app.repository.find(table)
        tables = await self.app.repository.get_tables()
        return {'title': T('Admin page'), 'tables': tables, 'rows':rows, 'table': table, 'the_form': the_form}

    async def post_new(self, request: Request, table: str):
        T = self.app.getT(request)
        if not await self.save_obj(request, table):
            return await self.new(request=request, table=table)
        request.session['flash'] = T(f'{table.title()} saved.')
        return RedirectResponse(request.url_for(self.prefix+'table', table=table), status_code=302)

    async def edit(self, request: Request, table: str, id: int):
        T = self.app.getT(request)
        relations = await self.get_relations(request, table)
        the_form = ModelForm(get_model(self.domain, table), action=T('Save'), admin=self.admin, relations=relations,
                             readonly=(table in self.readonly), T=T, template=self.form_templates.get(table))
        obj = await self.app.repository.get(table, id)
        the_form.load(obj)
        tables = await self.app.repository.get_tables()
        return {'title': T('Admin page'), 'tables': tables, 'table': table, 'the_form': the_form}

    async def post_edit(self, request: Request, table: str, id: int):
        T = self.app.getT(request)
        if not await self.save_obj(request, table, id):
            return await self.edit(request=request, table=table, id=id)
        request.session['flash'] = T(f'{table.title()} saved.')
        return RedirectResponse(request.url_for(self.prefix+'table', table=table), status_code=302)

    async def delete(self, request: Request, table: str, id: int):
        T = self.app.getT(request)
        await self.app.repository.delete(table, id)
        request.session['flash'] = T('{table} with id {id} deleted.').format(table=table.title(), id=id)
        return RedirectResponse(request.url_for(self.prefix+'table', table=table), status_code=302)

    async def save_obj(self, request, table, id=None):
        T = self.app.getT(request)
        try:
            saved = await save_obj(request, table, self.app, self.domain, defaults=self.build_defaults(request))
            request.session['flash'] = T(f'{table.title()} saved.')
            return saved
        except Exception as e:
            request.session['flash'] = ('danger', T(str(e)))
            return False



def get_model(domain, table):
    for name in dir(domain.model):
        if name.lower() == table:
            return getattr(domain.model, name)


async def save_obj(request, table, app, domain, defaults={}):
    obj = {}
    obj.update(defaults.get(table, {}))
    form = dict(**await request.form())
    form_items = list(form.items())
    for k, v in form_items:
        if k.startswith('imgfile_'):
            del form[k]
            if 'read' in dir(v) and v.filename and v.size:
                fieldname = k.removeprefix('imgfile_')
                filename = f'{time.time()}-{table}_{fieldname}.{v.filename.split(".")[-1]}'
                await imageserver.save_image(v, filename)
                form[fieldname] = filename

    obj.update(form)

    if 'id' in obj and not obj['id']:
        del obj['id']

    model = get_model(domain, table)
    model(**obj)

    if 'password' in obj:
        if obj['password']:
            obj['password'] = app.repository.encode_password(obj['password'])
        else:
            del obj['password']

    async with app.storage.transaction():
        saved = await app.repository.save(table, obj)

    return saved

