"""Repository sql storage backend."""
import urllib.parse
# from .sql_backends import postgresql_asyncpg, sqlite_aiosqlite, mysql_asyncmy
from . import migrations
import typing
import contextlib
import importlib

def _raise(*args, **kwargs):
    raise NotImplementedError(*args, **kwargs)


class Storage:
    """SQL storage."""

    def __init__(self, connection_string: str) -> None:
        """Initialize."""
        self.connection_string = connection_string
        self.connection_params = {}
        self.tables = {}
        self.backends = {
            "postgres": ".sql_backends.postgresql_asyncpg",
            "sqlite": ".sql_backends.sqlite_aiosqlite",
            "mysql": ".sql_backends.mysql_asyncmy",
        }
        self.backend: typing.Any = None

    async def init(self, **kwargs) -> None:
        """Initialize."""
        self.determine_engine()
        self.backend = self.backend.SQLBackend(
            self.connection_string, self.connection_params)
        await self.backend.init(**kwargs)

    def determine_engine(self) -> None:
        """Determine engine."""
        if ':memory:' in self.connection_string:
            self.backend = importlib.import_module(self.backends["sqlite"], __package__)
            return
        parsed = urllib.parse.urlparse(self.connection_string)
        self.backend = self.backends.get(parsed.scheme)
        _raise(f"Engine {parsed.scheme} not implemented") if not self.backend else None
        self.backend = importlib.import_module(self.backend, __package__)
        self.connection_params = {
            "user": parsed.username,
            "password": parsed.password,
            "host": parsed.hostname,
            "port": parsed.port,
            "database": parsed.path[1:],
        }

    @contextlib.asynccontextmanager
    async def transaction(self):
        """Transaction."""
        conn = await self.backend.start_transaction()
        try:
            yield conn
        except Exception:
            await self.backend.rollback(conn)
            raise
        else:
            await self.backend.commit(conn)
        finally:
            await self.backend.end_transaction(conn)

    async def save(self, entity: str, data: dict, connection: typing.Any = None) -> dict:
        """Save data."""
        return await self.backend.save(entity.lower(), data, connection=connection)

    async def find(self, entity: str, f: dict = {}, limit: int | None = None, fields: list = [],
                   offset: int | None = None, connection: typing.Any = None,
                   order_by: dict = {}) -> list[dict]:
        """Filter by the kwargs."""
        return await self.backend.find(
            entity.lower(), f, fields=fields, limit=limit, offset=offset, order_by=order_by,
            connection=connection)

    async def update(self, entity: str, entity_id: int, data: dict,
                     connection: typing.Any = None) -> None:
        """Update data."""
        await self.backend.update(entity.lower(), entity_id, data, connection=connection)

    async def delete(self, entity: str, entity_id: int, connection: typing.Any = None) -> None:
        """Delete data."""
        await self.backend.delete(entity.lower(), entity_id, connection=connection)

    async def migrate(self, model: object, migration_folder: str = "migrations",
                      migrate: bool = True, fake_migrate: bool = False) -> None:
        """Migrate the database."""
        create_table_executed_sql = migrations.migrate(
            model, self.connection_string, migration_folder, migrate, fake_migrate)
        if 'memory' in self.connection_string:
            await self.create_sqlite_in_memory_tables(create_table_executed_sql)

    async def execute(self, sql: str, values: tuple, connection: typing.Any = None) -> None:
        """Execute sql."""
        return await self.backend.execute(sql, values, connection=connection)

    async def create_sqlite_in_memory_tables(self, create_table_sql: list[str]) -> None:
        """Create tables in memory."""
        await self.backend.create_sqlite_in_memory_tables(create_table_sql)

    async def truncate_db(self) -> None:
        """Truncate all tables in the database."""
        await self.backend.truncate_db()

    async def get_tables(self) -> list[str]:
        """Get tables."""
        return await self.backend.get_tables()
