import functools
from urllib.parse import quote as escape
from fastapi.responses import RedirectResponse


class AuthApp:
    def requires(self, *permissions):

        def decorator(fn):
            @functools.wraps(fn)
            async def wrapper(*args, **kwargs):
                request = kwargs['request']

                if not request.session.get('userid'):
                    return self.auth_redirect('login', request)

                user = await self.repository.get('User', request.session['userid'])

                if user.get('validation_code'):
                    return self.auth_redirect('validate_email', request)

                if not await self.has_permission(request, *permissions):
                    request.session['flash'] = ('danger', 'You do not have permission to access this page')
                    return RedirectResponse('/')

                return await fn(*args, **kwargs)

            return wrapper

        return decorator


    async def get_roles(self, user_id):
        roles = await self.storage.execute(f'''
            SELECT
                role.name
            FROM
                role, userrole
            WHERE
                userrole.user_id = {user_id}
                AND userrole.role_id = role.id
        ''', ())
        return [role['name'] for role in roles]


    async def get_permissions(self, user_id):
        permissions = await self.storage.execute(f'''
            SELECT
                permission.name
            FROM
                permission, rolepermission, role, userrole
            WHERE
                userrole.user_id = {user_id}
                AND userrole.role_id = role.id
                AND role.id = rolepermission.role_id
                AND rolepermission.permission_id = permission.id
        ''', ())
        return [permission['name'] for permission in permissions]


    async def has_permission(self, request, *permissions):
        if not permissions:
            return True

        if not request.session.get('userid'):
            return False

        return bool(await self.storage.execute(f'''
            SELECT
                user.id
            FROM
                user, userrole, role, rolepermission, permission
            WHERE
                user.id = {request.session['userid']}
                AND userrole.user_id = user.id
                AND userrole.role_id = role.id
                AND role.id = rolepermission.role_id
                AND rolepermission.permission_id = permission.id
                AND permission.name IN ('{"','".join(permissions)}')
        ''', ()))


    def auth_redirect(self, fn_name, request):
        redir_url = f"{request.url_for(fn_name)}?next={request.url.path}"
        query_params = str(request.url.query)
        if query_params:
            redir_url += escape(f"?{query_params}")
        return RedirectResponse(redir_url)

