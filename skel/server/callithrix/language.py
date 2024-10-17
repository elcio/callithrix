import toml
import jinja2
from . import jinja


class Translator:
    def __init__(self, app, request, default='en', langs=()):
        self.request = request
        self.app = app
        self.langs = langs or ()
        self.language = self.get_language()

    def get_language(self):
        lang = self.request.session.get('language')
        if not lang:
            langs = [
                lang.split(';')[0]
                for lang in self.request.headers.get('accept-language').split(',')
            ]
            for lang in langs:
                if lang in self.langs or not self.langs:
                    self.request.session['language'] = lang
                    return lang
        return lang or self.default

    def __call__(self, text):
        return self.app.translate(text, self.language)


class LangApp:
    def __init__(self, app, default='en', langs=None, **kwargs):
        self.app = app
        self.default = default
        self.langs = langs
        self.data = {}

        @jinja2.pass_context
        def T(context, text):
            request = context['request']
            if 'translator' not in dir(request):
                request.translator = Translator(self, request)
            return request.translator(text)

        @jinja2.pass_context
        def getT(context):
            request = context['request']
            if 'translator' not in dir(request):
                request.translator = Translator(self, request)
            return request.translator

        jinja.env_globals['T'] = T
        jinja.env_globals['getT'] = getT

    def getT(self, request):
        if 'translator' not in dir(request):
            request.translator = Translator(self, request)
        return request.translator

    def load_data(self, lang):
        if lang not in self.data:
            try:
                with open(f'lang/{lang}.toml') as f:
                    self.data[lang] = toml.load(f)
            except FileNotFoundError:
                self.data[lang] = {}

    def translate(self, text, lang=None):
        if isinstance(text, Translation):
            return text
        self.load_data(lang)
        if text not in self.data[lang]:
            self.data[lang][text] = text
            with open(f'lang/{lang}.toml', 'w') as f:
                toml.dump(self.data[lang], f)
        return Translation(self.data[lang][text])


class Translation(str):
    def __init__(self, text):
        self.text = text
        str.__init__(text)
    def toJson(self):
        return self.text
    def __str__(self):
        return self.text
    def __repr__(self):
        return f'<T:{self.text}>'

