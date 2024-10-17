import os
import json
import string
import random
import inspect
import pathlib
import functools
import importlib
from domain import model
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from .jinja import SmartTemplates
from .authapp import AuthApp
from .db import DBApp
from .language import LangApp


class SmartApp(DBApp, AuthApp, LangApp):
    def __init__(self, *args, static_path="static", templates_path="templates", config_folder="config/", **kwargs):
        self.base_template = str(pathlib.Path(__file__).parent.resolve())+'/templates'
        if not isinstance(templates_path, list):
            templates_path = [templates_path]
        self.templates_path = templates_path
        self.config = self.load_config(config_folder)
        self.globals = {}
        DBApp.__init__(self, *args, **kwargs)
        self.mount("/static", StaticFiles(directory=static_path), name="static")
        self.templates = None
        self.add_middleware(SessionMiddleware, secret_key=self.config['secret_key'])
        LangApp.__init__(self, *args, **kwargs)


    def load_config(self, config_folder="config/"):
        if not os.path.isfile(f"{config_folder}config.json"):
            with open(f"{config_folder}configsample.json") as sample:
                config = json.load(sample)
                config['secret_key'] = ''.join(random.choices(string.printable, k=32))
            with open(f"{config_folder}config.json", "w") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        with open(f"{config_folder}config.json") as f:
            config = json.load(f)
        return config

    def gethtml(self, path, *args, **kwargs):
        return self.req_html(self.get, path, *args, **kwargs)

    def posthtml(self, path, *args, **kwargs):
        return self.req_html(self.post, path, *args, **kwargs)

    def puthtml(self, path, *args, **kwargs):
        return self.req_html(self.put, path, *args, **kwargs)

    def deletehtml(self, path, *args, **kwargs):
        return self.req_html(self.delete, path, *args, **kwargs)

    def patchhtml(self, path, *args, **kwargs):
        return self.req_html(self.patch, path, *args, **kwargs)

    def req_html(self, method, path, *args, tags=('html',), **kwargs):
        def decorator(fn):
            @method(path, *args, tags=tags, **kwargs)
            @functools.wraps(fn)
            async def wrapper(*args, **kwargs):
                nonlocal path
                ret_val = fn(*args, **kwargs)
                if inspect.iscoroutine(ret_val):
                    ret_val = await ret_val
                if isinstance(ret_val, dict):
                    request = kwargs.get('request')
                    if request is None:
                        raise ValueError("Your function's first argument should be 'request: Request'")
                    template_val= {
                        "form": await request.form(),
                        "request": request,
                        "globals": self.globals,
                        "roles": [],
                        "permissions": [],
                        "user": {},
                    }
                    userid = request.session.get('userid')
                    if userid:
                        template_val['roles'] = await self.get_roles(userid)
                        template_val['permissions'] = await self.get_permissions(userid)
                        template_val['user'] = await self.repository.get('User', userid)
                    template_val.update(ret_val)
                    if request.query_params.get('format') != 'json':
                        if 'template_path' in dir(request):
                            path = request.template_path
                        ret = self.render_template(path, template_val)
                        if ret:
                            return ret
                    return JSONResponse(ret_val)
                if isinstance(ret_val, str):
                    return HTMLResponse(ret_val)
                return ret_val
            return wrapper
        return decorator

    def render_template(self, path, return_value):
        if 'title' not in return_value:
            return_value['title'] = ''
        templates_path = self.templates_path + [self.base_template]
        if not self.templates:
            self.templates = SmartTemplates(directory=templates_path)
        path = path.replace('{', '_').replace('}', '')
        if not path.endswith('/'):
            path += '/'
        for basepath in templates_path:
            if os.path.isfile(f"{basepath}{path[:-1]}.html"):
                return self.templates.TemplateResponse(f"{path[:-1]}.html", return_value)
            if os.path.isfile(f"{basepath}{path}index.html"):
                return self.templates.TemplateResponse(f"{path}index.html", return_value)


class SubApp(AuthApp):
    def __init__(self, module, path=None):
        self.module = module
        if not path:
            path = '/' + module['__name__'].split('.')[-2].lower() + '/'
        self.path = path
        self.methods = []
        self.app = None
        self.templates_path = str(pathlib.Path(module['__file__']).parent.resolve()).removesuffix('/') + '/templates'

        try:
            moddomain = importlib.import_module(module['__name__'].replace('.app', '.model'))
            for k in dir(moddomain):
                v = getattr(moddomain, k)
                if inspect.isclass(v) and issubclass(v, model.BaseModel):
                    if k not in dir(model):
                        setattr(model, k, v)
        except ImportError as e:
            pass

    def gethtml(self, path, *args, **kwargs):
        return self.req_html('get', path, *args, **kwargs)

    def posthtml(self, path, *args, **kwargs):
        return self.req_html('post', path, *args, **kwargs)

    def puthtml(self, path, *args, **kwargs):
        return self.req_html('put', path, *args, **kwargs)

    def deletehtml(self, path, *args, **kwargs):
        return self.req_html('delete', path, *args, **kwargs)

    def patchhtml(self, path, *args, **kwargs):
        return self.req_html('patch', path, *args, **kwargs)

    def req_html(self, method, path, *args, tags='', **kwargs):
        if not tags:
            tags = 'html/' + self.path
            tags = [tags.replace('//', '/')]
        def decorator(fn):
            self.methods.append((method, path, fn, tags, args, kwargs))
            return fn
        return decorator

    def build_path(self, path):
        path = f"{self.path}/{path}"
        path = path.replace('//', '/')
        path = path.replace('//', '/')
        return path

    def register(self, app):
        app.templates_path.append(self.templates_path)
        self.app = app
        for method, path, fn, tags, args, kwargs in self.methods:
            app.req_html(getattr(app, method), self.build_path(path), tags=tags, *args, **kwargs)(fn)

    def __getattr__(self, name):
        if self.app:
            return getattr(self.app, name)

