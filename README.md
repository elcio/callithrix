# Callithrix Framework

Callithrix Framework is a web project skeleton built on FastAPI (hence, Starlette), Jinja2, and MEL Repository. It uses [mise-en-place](https://mise.jdx.dev/) and [uv](https://github.com/astral-sh/uv), so make sure these tools are installed.

## Creating a Project

Run:

```callithrix project_name```

## Running

Navigate to the project folder and run:

```mise run server```

## Configuring the Project

In the `config/` folder, there is a `configsample.json` file. When running the project for the first time, it will be copied to `config/config.json`, and a random key will be generated in the "secret_key" value. The values in config.json are:

```javascript
{
  "dbconn": "sqlite://storage.sqlite3",     // Database connection URL
  "migrations": "database/",                // Migrations folder
  "smtp": {
    "host": "smtp.youremail.server",        // SMTP server
    "port": 465,                            // SMTP port
    "user": "username@youremail.server",    // SMTP user
    "sender": "username@youremail.server",  // SMTP sender (used in the From: header)
    "password": "password"                  // SMTP password
  },
                                            // Session cookie encryption key
  "secret_key": "fW%t\\\"`:a\rJ `=5wCC0|Se\nx\n0l2&MF$"
}
```

The secret key must be random and unique; do not reuse the key in different installations.

## Installing Modules

To install new Python modules into the project, navigate to the server folder and run:

```uv add module_name```

## Users and Permissions

When starting a new project, go to http://127.0.0.1:8000/auth/signup and register your first user. A `dbadmin` permission and a `dbadmin` role will be created, and the first user will be assigned this role. Any user with `dbadmin` permission can access http://127.0.0.1:8000/admin/ and manage all database tables.

When users sign up, they must validate their email. If you haven't set up an SMTP service, the Callithrix Framework will print the contents of the emails it cannot send to the terminal. Check the terminal where the server was started, and you will find the key to validate your email.

## Project Structure

+ **config/config.json:** project configurations.
+ **domain/model.py:** model, where you can create your database tables.
+ **images/:** storage for images uploaded by users.
+ **lang/:** application translations.
+ **migrations/:** database migration data. If you're using SQLite, the database itself will also be here.
+ **callithrix/:** Callithrix Framework modules; do not modify these.
+ **templates/:** HTML templates (Jinja2)

## Database

Let's create two new tables, called `car` and `manufacturer`. To do this, edit the `domain/model.py` file, adding the following at the end:

```python
class Manufacturer(MelBase):
    name: str = Field(max_length=100, unique=True)

    class Config:
        audit_table = 'manufacturer'

    def __str__(self):
        return self.name


class Car(MelBase):
    model: str = Field(max_length=100)
    year: int = Field(inputtype='number')
    manufacturer_id: int
    photo: str = Field(default='', inputtype='imageupload')

    class Config:
        audit_table = 'car'
```

That's it. Access the admin panel, and you'll be able to register manufacturers and cars.

## Image Optimizer

Edit a car for which you have already uploaded a photo, right-click on the photo, and open it in a new tab. You'll notice that the URL looks like this:

```http://127.0.0.1:8000/optimage/240x160/1728988027.0574777-car_1_photo.avif```

The image has been automatically optimized to AVIF format for faster loading. Notice the `/240x160/` part — this indicates the size the image should be rendered. To view the image in its original size, remove this fragment from the URL, like this:

```http://127.0.0.1:8000/optimage/1728988027.0574777-car_1_photo.avif```

To generate it in another size, change the values, like this:

```http://127.0.0.1:8000/optimage/400x400/1728988027.0574777-car_1_photo.avif```

## Creating Your Routes

By editing the `app.py` file, you can create your routes. The application is based on FastAPI, so you can create Starlette or FastAPI routes normally. For example, if you want to create a route to be used as an API, you can do it as follows:

```python
@app.get('/cars')
async def cars():
    manufacturers = await app.repository.find('Manufacturer')
    manufacturers = {
        manufacturer['id']: manufacturer['name'] for
        manufacturer in manufacturers
    }

    cars = await app.repository.find('Car')
    for car in cars:
        car['manufacturer'] = manufacturers[car['manufacturer_id']]

    return {"cars": cars}
```

To turn it into a special Callithrix Framework route, just replace the `@app.get` decorator with `@app.gethtml` and ensure the function receives `request: Request` as its first parameter:

```python
@app.gethtml('/cars')
async def cars(request: Request):
    ...
    return {"cars": cars}
```

## Templates

Doing this, you will still see the JSON return if you test this method, because there is no template for it yet. Write a file `templates/cars.html` (or `templates/cars/index.html`) with the following content:

```html
{% extends "base/layout.html" %}

{% block content %}
  <div class="container">
    <h1 class="title is-1">{{ T('Cars') }}</h1>
    <ul>
      {% for car in cars %}
        <li>
          {% if car.photo %}
            <img
              src="{{ url_for('resized_image', width=200, height=100, img=car.photo) }}"
              alt="{{ car.model }}"><br />
          {% endif %}
          {{ car.manufacturer }} {{ car.model }} {{ car.year }}
        </li>
      {% endfor %}
    </ul>
  </div>
{% endblock %}
```

The templates are located based on the URL being called. The URL parameters are converted into paths with underscores (`_`). For example, the following method:

```@app.gethtml('/sum/{a}/{b}/')```

Will be rendered using the template:

```templates/sum/_a/_b/index.html```

The templates use [Jinja](https://jinja.palletsprojects.com/en/3.1.x/). Explore the templates folder, and you will find two interesting files:

+ **base/layout.html**: the base layout of the application
+ **components/menu.html**: the navigation menu

This folder structure (base for layouts and components for reusable components) is optional, but we suggest you keep it. If you need to create additional base layouts or even a hierarchy among them, do so inside the base folder. If you're creating reusable HTML blocks, place them in the components folder.

Let's practice. Open the file `components/menu.html` and, just after the line:

```html
        {{ nav_item(T('Home'), 'index') }}
```

Insert:

```html
        {{ nav_item(T('Cars'), 'cars') }}
```

Now, test the application, and you will see a link to the car list in the menu.

Now, let's change the theme's CSS. Open the file `base/layout.html`, and you will find this line:

```html
        <link rel="stylesheet" href="//unpkg.com/bulmaswatch/flatly/bulmaswatch.min.css" />
```

The `/flatly/` fragment in the URL is the name of the theme. Visit [Bulmaswatch](https://jenil.github.io/bulmaswatch/) and choose another theme. For example, to use the `darkly` theme, change it to:

```html
        <link rel="stylesheet" href="//unpkg.com/bulmaswatch/darkly/bulmaswatch.min.css" />
```
```

## Translations

You may have noticed in the template above the use of the function `T()`. It makes the text go through the translation mechanism. You can also use the `T` function in your functions; to do this, you need to obtain it with `T = app.getT(request)`. For example, let's modify the `cars` function to return the page title:

```python
@app.get('/cars')
async def cars():
    T = app.getT(request)

    ...

    return {"cars": cars, "title": T("Car list")}
```

The Callithrix Framework automatically detects the user's language through their browser headers. For example, if you use a Portuguese browser, you should find, inside the `languages` folder, a `pt-BR.toml` file with the following format:

```toml
Home = "Home"
Admin = "Admin"
Account = "Account"
Logout = "Logout"
Cars = "Cars"
"Car list" = "Car list"
"Hello, World!" = "Hello, World!"
```

Depending on the tests you've done, your file may be slightly different from this. That's okay.

For performance reasons, translation loading is not dynamic. Therefore, stop the server before editing this file. Then translate the values like this:

```toml
Home = "Início"
Admin = "Admin"
Account = "Conta"
Logout = "Sair"
Cars = "Carros"
"Car list" = "Lista de Carros"
"Hello, World!" = "Olá, Mundo!"
```

Restart the server and load the list of cars; you will see that the page title has been translated.

## Session

The Callithrix Framework uses Starlette's `SessionMiddleware`. The session is exposed in `request.session`. You can read and assign values to the session as if it were a dictionary.

When you log in, your user ID is stored in `request.session.userid`.

When you access any page, your browser's language is stored in `request.session.language`. If you want to force a specific language, just assign it to this value.

**Caution**: If you come from environments like PHP or .Net, you're used to sessions stored on the server. The sessions in the Callithrix Framework are stored encrypted in a cookie (using the `secret_key` from `config.json`). Therefore, be cautious; store only simple values in the session. If you need a data structure, save it in the database or some other server-side persistence and store only the ID in the session.

## Forms

The Callithrix Framework automatically generates forms based on models. Edit the `app.py` file and add the following imports:

```python
from fastapi.responses import RedirectResponse
from callithrix.form import ModelForm
from callithrix.crud import save_obj
```

And at the end of the file, add:

```python
@app.gethtml('/newcar')
@app.requires()
async def newcar(request: Request):
    manufacturers = {
        m['id']: m['name'] for m in
        await app.repository.find('Manufacturer')
    }
    form = ModelForm(domain.model.Car, relations={'manufacturer': manufacturers.items()})
    return {"form": form, 'title': 'New Car'}

@app.post('/newcar')
@app.requires()
async def post_newcar(request: Request):
    T = app.getT(request)
    saved = await save_obj(request, 'car', app, domain)
    if saved:
        request.session['flash'] = T('New car inserted.')
        return RedirectResponse(request.url_for('cars'), status_code=302)
    else:
        return await newcar(request=request)
```

## Applications

You can create your applications in directories so that they can be reused in various different projects. Let's build an application with a list of projects. Create a folder named `projects` inside the `server` folder. Inside `projects`, create a file named `model.py` with the following content:

```python
from pydantic import BaseModel, Field
from typing import Optional


class MelBase(BaseModel):
    id: Optional[int] = None
    class Config:
        audit_table = 'user'


class Project(MelBase):
    user_id: int = Field(internal=True)
    name: str = Field(max_length=255)
    photo: str = Field(max_length=255, default='', inputtype='imageupload')
    description: str = Field(max_length=3000, inputtype='textarea')
    class Config:
        audit_table = 'project'
```

And a file named `app.py` with the following content:

```python
from callithrix import SubApp
from fastapi import Request

app = SubApp(globals())


@app.gethtml('/')
async def projects(request: Request):
    projects = await app.repository.find('project')
    return {
        'title': 'Projects',
        'projects': projects,
    }
```

With this, we have defined a new sub-application that has a `project` table and a route that lists the projects. To register this application, edit the `app.py` file in the `server` folder and include the following import:

```python
import projects.app as projects
```

At the very beginning of the file, you will find a block where sub-applications are registered. It ends with `optimage.app.register(app)`. Right after that line, include:

```python
projects.app.register(app)
```

Access the admin, and you will see that the `projects` table is available. Register some projects. Then, go to `http://127.0.0.1:8000/projects/` and you will see a list of projects (in JSON).

## Sub-Application Templates

You can place the sub-application templates inside the `templates` folder of `server` or you can create a `templates` folder inside the sub-application folder. The second way can make it easier to copy a sub-application to another project.

Create a folder named `templates` inside the `projects` folder, and then create a folder `templates/projects` inside it. Next, create the file `templates/projects/index.html` with the following content:

```html
{% extends "base/layout.html" %}

{% block content %}
  <div class="container">
    <div class="content">
      <h1>{{ T('Hello, World!') }}</h1>
      <ul>
        {% for project in projects %}
        <li>{{ project.name }}</li>
        {% endfor %}
      </ul>
    </div>
  </div>
{% endblock %}
```

Now you will be able to see the listing in HTML.

## Automatic CRUD

Insert into `projects/app.py`:

```python
from callithrix.crud import Crud
import domain

crud = Crud(
    app,
    domain,
    'projects',
    'adm',
    filters={
        'project': {
            'user_id': ('=', '{userid}'),
        },
    },
    defaults={
        'project': {
            'user_id': '{userid}',
        },
    },
    tables=['project'],
)
```

Then, in `projects/templates/projects`:

```cp -r ../../../callithrix/admin/templates/admin/ adm```

Then access `http://127.0.0.1:8000/projects/adm/`
