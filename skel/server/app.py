from fastapi import Request
from callithrix import SmartApp
import callithrix.auth.app as auth
import callithrix.admin.app as admin
import callithrix.optimage.app as optimage
import domain


app = SmartApp(domain.model)
auth.app.register(app)
admin.app.register(app)
optimage.init('/images/')
optimage.app.register(app)


@app.gethtml("/")
async def index(request: Request):
    request.session['counter'] = request.session.get('counter', 0) + 1
    return {
        "title": "Hello, World!",
    }


@app.gethtml("/secret")
@app.requires()
async def secret(request: Request):
    request.template_path = '/'
    return {
        "msg": "Hello, Secret World!",
        "title": "Secret",
        "counter": request.session['counter']
    }


