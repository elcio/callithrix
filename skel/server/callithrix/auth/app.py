from fastapi import Request
from callithrix import SubApp
from callithrix.form import ModelForm, Form
from callithrix.types import FormField
from fastapi.responses import RedirectResponse
from ..utils import email
from datetime import datetime, timedelta
import domain
import string
import random
import uuid


app = SubApp(globals())


@app.gethtml('/login')
async def login(request: Request, next: str=None):
    T = app.getT(request)
    login_form = Form(
        {'name':'email', 'type':'email', 'label':'Email', 'autofocus': True},
        {'name':'password', 'type':'password', 'label':'Password'},
        method='post',
        action='Login',
        extra_buttons = [
            f'<a href="{request.url_for("forgot_password")}" class="button">' + \
                T("Forgot my password.") + '</a>',
            f'<a href="{request.url_for("signup")}" class="button">' + \
                T("Don't have an account? ") + T('Register') + '</a>'
        ]
    )
    return {
        'title':'Login page',
        'next': next or '/',
        'login_form': login_form,
    }


@app.posthtml('/login')
async def do_login(request: Request, email: FormField, password: FormField, next: str=None):
    T = app.getT(request)
    user = await app.repository.find_one('User', {'email': email})
    msg = ("danger", T("E-mail {email} is not a user. Please try again.").format(email=email))

    if user:
        password = app.repository.encode_password(password, user['id'])
        msg = ("danger", T("Invalid password. Please try again."))
        if password == user['password']:
            request.session['userid'] = user['id']
            request.session['flash'] = T("You have been logged in. Welcome.")
            return RedirectResponse(next or '/', status_code=302)

    request.session['flash'] = msg
    return await login(request, next or '/')


@app.gethtml('/account')
@app.requires()
async def account(request: Request):
    T = app.getT(request)
    account_form = ModelForm(domain.model.User, action='Save', T=T)
    user = await app.repository.get('User', request.session['userid'])
    account_form.load(user)
    return {
        'title':'Account page',
        'account_form': account_form,
    }


@app.posthtml('/account')
@app.requires()
async def post_account(request: Request):
    T = app.getT(request)
    form = await request.form()
    user = await app.repository.get('User', request.session['userid'])
    save_data = {
        'id': user['id'],
        'name': form.get('name'),
        'email': form.get('email'),
    }

    if save_data['email'] != user['email']:
        save_data['validation_code'] = generate_code()

    if form.get('password'):
        current_password = app.repository.encode_password(form['current_password'], user['id'])

        if current_password != user['password']:
            request.session['flash'] = ("danger", T("Invalid password. Please try again."))
            return await account(request=request)

        save_data['password'] = app.repository.encode_password(form['password'], user['id'])

    try:

        async with app.storage.transaction():
            await app.repository.save('User', save_data)

        request.session['flash'] = T("Account updated.")

        if save_data.get('validation_code'):
            await send_validation_code(user['id'])
            request.session['flash'] = ("warning", T("Account updated. A new validation code has been sent to your e-mail."))

        return RedirectResponse(request.url_for('account'), status_code=302)

    except Exception as e:
        request.session['flash'] = ("danger", T(str(e)))
        return await account(request=request)


@app.gethtml('/logout')
async def logout(request: Request):
    T = app.getT(request)
    del request.session['userid']
    request.session['flash'] = T("You have been logged out.")
    return RedirectResponse('/')


@app.gethtml('/signup')
async def signup(request: Request):
    signup_form = ModelForm(domain.model.User, action='Sign Up', T=app.getT(request))
    return {'title':'Signup page', 'signup_form': signup_form}


@app.posthtml('/signup')
async def post_signup(request: Request):
    T = app.getT(request)
    form = await request.form()
    user = await app.repository.find_one('User', {'email': form.get('email')})

    if user:

        if user['password'] == app.repository.encode_password(form.get('password'), user['id']):
            request.session['userid'] = user['id']
            return RedirectResponse(request.query_params.get('next', '/'), status_code=302)

        request.session['flash'] = ('danger', T("E-mail {email} is already in use.").format(email=form.get('email')))
        return await signup(request)

    users = await app.repository.find('User')
    roles = await app.repository.find('Role')
    permissions = await app.repository.find('Permission')
    first_user = not (users or roles or permissions)

    user = domain.model.User(
        name=form.get('name'),
        email=form.get('email'),
        password=form.get('password'),
        validation_code=generate_code(),
    )

    async with app.storage.transaction():
        saved = await app.repository.save('User', user)
        if first_user:
            await populate_first_user(saved['id'])

    await send_validation_code(saved['id'])
    request.session['userid'] = saved['id']

    return RedirectResponse(request.query_params.get('next', '/'), status_code=302)


async def populate_first_user(userid):
    permission = domain.model.Permission(name='dbadmin')
    role = domain.model.Role(name='dbadmin')
    async with app.storage.transaction():
        perm = await app.repository.save('Permission', permission)
        role = await app.repository.save('Role', role)
        await app.repository.save('RolePermission', {'role_id': role.id, 'permission_id': perm.id})
        await app.repository.save('UserRole', {'user_id': userid, 'role_id': role.id})


@app.gethtml('/validate')
async def validate_email(request: Request):
    if not request.session.get('userid'):
        return RedirectResponse(request.url_for('login'), status_code=302)
    return {'title':'Validate your e-mail'}


@app.posthtml('/validate')
async def post_validate_email(request: Request):
    T = app.getT(request)
    if not request.session.get('userid'):
        return RedirectResponse(request.url_for('login'), status_code=302)

    form = await request.form()
    user = await app.repository.get('User', request.session['userid'])

    if form.get('pin'):
        if form.get('pin') == user['validation_code']:
            user['validation_code'] = None
            async with app.storage.transaction():
                await app.repository.save('User', user)
            request.session['flash'] = T("E-mail validated.")
            await populate_first_user(user['id'])
            return RedirectResponse(request.query_params.get('next', '/'), status_code=302)
        else:
            request.session['flash'] = ('danger', T("Invalid validation code. Please try again."))

    if form.get('resend') and user['updated_at'] < str(datetime.now() - timedelta(minutes=1)):
        await send_validation_code(user['id'])
        request.session['flash'] = T("Validation code resent.")
        async with app.storage.transaction():
            await app.repository.save('User', user)

    return await validate_email(request)


@app.gethtml('/forgot')
async def forgot_password(request: Request):
    T = app.getT(request)
    forgot_form = Form(
        {'name':'email', 'type':'email', 'label':T('Email'), 'required': True, 'autofocus': True},
        method='post',
        action='Send',
    )
    return {'title':'Forgot password', 'forgot_form': forgot_form}


@app.posthtml('/forgot')
async def post_forgot_password(request: Request):
    T = app.getT(request)
    form = await request.form()
    user = await app.repository.find_one('User', {'email': form.get('email')})

    if user:
        user['recovery_code'] = str(uuid.uuid4())
        async with app.storage.transaction():
            await app.repository.save('User', user)
        email.init(app.config)
        email.enviar_email(
            subject=T('Recover your password'),
            to=user['email'],
            message=str('''<p>{greeting}</p>
                           <p>{message}</p>
                           <a href="{url}">{link_text}</a>
                           <p>{post_message}</p>
            ''').format(
                url=f"{request.url_for('recover_password')}?code={user['recovery_code']}",
                greeting=T('Hello,'),
                message=T('Someone (probably you) requested to recover your password.'),
                link_text=T('Click here to recover your password.'),
                post_message=T('If you did not request this, please just ignore this message.'),
            ),
        )
        request.session['flash'] = T("Recovery code sent to your e-mail.")
    else:
        request.session['flash'] = ('danger', T("E-mail {email} is not a user. Please try again.").format(email=form.get('email')))
    return await forgot_password(request)


@app.gethtml('/recover')
async def recover_password(request: Request):
    T = app.getT(request)
    code = request.query_params.get('code')
    if not code:
        return RedirectResponse(request.url_for('forgot_password'), status_code=302)

    user = await app.repository.find_one('User', {'recovery_code': code})

    if not user:
        request.session['flash'] = ('danger', T("Invalid recovery code. Please try again."))
        return RedirectResponse(request.url_for('forgot_password'), status_code=302)

    recover_form = Form(
        {'name':'password', 'type':'password', 'label':T('New password'), 'required': True, 'autofocus': True},
        method='post',
        action='Recover',
    )
    return {'title':'Recover password', 'recover_form': recover_form}


@app.posthtml('/recover')
async def post_recover_password(request: Request):
    T = app.getT(request)
    form = await request.form()
    code = request.query_params.get('code')
    user = await app.repository.find_one('User', {'recovery_code': code})

    if not user:
        request.session['flash'] = ('danger', T("Invalid recovery code. Please try again."))
        return RedirectResponse(request.url_for('forgot_password'), status_code=302)

    user['recovery_code'] = None
    user['password'] = app.repository.encode_password(form.get('password'), user['id'])
    async with app.storage.transaction():
        await app.repository.save('User', user)

    request.session['flash'] = T("Password recovered.")
    return RedirectResponse(request.url_for('login'), status_code=302)


async def populate_first_user(userid):
    permissions = await app.repository.find('Permission')

    if not permissions:
        async with app.storage.transaction():
            perm = await app.repository.save('Permission', {'name': 'dbadmin'})
            role = await app.repository.save('Role', {'name': 'dbadmin'})
            await app.repository.save('RolePermission', {'role_id': role['id'], 'permission_id': perm['id']})
            await app.repository.save('UserRole', {'user_id': userid, 'role_id': role['id']})


async def send_validation_code(userid):
    user = await app.repository.get('User', userid)
    email.init(app.config)
    email.enviar_email(
        subject='Validate your e-mail',
        to=user['email'],
        message=f"Your validation code is {user['validation_code']}",
    )


def generate_code():
    return ''.join(random.choices(string.digits, k=8))
