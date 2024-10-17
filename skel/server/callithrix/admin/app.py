from callithrix.crud import Crud
from callithrix import SubApp
import domain

app = SubApp(globals())

crud = Crud(
    app,
    domain,
    'admin',
    permissions=('dbadmin',),
    admin=True,
)
