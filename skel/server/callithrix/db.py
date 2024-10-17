from fastapi import FastAPI
from .repository import repo
from .repository.storage.sql import Storage


class DBApp(FastAPI):

    def __init__(self, model, *args, **kwargs):

        async def lifespan(_):
            await self.storage.init()
            await self.storage.migrate(self.model)
            yield
            await self.storage.backend.close()

        self.model = model
        kwargs['lifespan'] = lifespan
        super().__init__(*args, **kwargs)
        self.init_repository()

    def init_repository(self):
        self.storage = Storage(self.config['dbconn'])
        self.repository = repo.Repository(self.storage, secret_key=self.config['secret_key'])


