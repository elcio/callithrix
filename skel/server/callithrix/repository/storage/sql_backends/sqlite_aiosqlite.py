"""Postgresql asyncpg backend."""
import aiosqlite
from . import query_builder
import typing

class SQLBackend:
    """SQL backend."""

    def __init__(self, connection_string: str, connection_params: dict):
        """Initialize."""
        self.connection_string = f'migrations/{connection_string.split("//")[1]}'
        if ':memory:' in connection_string:
            self.connection_string = ':memory:'
        self.connection_params = connection_params
        self.pool: typing.Any = None

    async def init(self, **kwargs) -> object:
        """Initialize."""
        self.pool = await aiosqlite.connect(self.connection_string, **kwargs)
        self.pool.row_factory = aiosqlite.Row

    async def close(self) -> None:
        """Close connection."""
        await self.pool.close()

    async def start_transaction(self) -> object:
        """Start transaction."""
        # pool = await aiosqlite.connect(self.connection_string)
        # pool.row_factory = aiosqlite.Row
        cursor = await self.pool.execute("BEGIN")
        return cursor

    async def commit(self, connection: typing.Any) -> None:
        """Commit."""
        await connection._conn.commit()

    async def rollback(self, connection: typing.Any) -> None:
        """Rollback."""
        await connection._conn.rollback()

    async def end_transaction(self, connection: typing.Any) -> None:
        """End transaction."""
        # await connection.close()
        # await connection._conn.close()

    async def find(self, entity: str, f: dict, limit: int | None = None, fields: list = [],
                   offset: int | None = None, order_by: dict = {},
                   connection: typing.Any = None) -> list[dict]:
        """Find all models."""
        if connection:
            return await self.__find_transaction(entity, f, connection=connection, fields=fields,
                                                 limit=limit, offset=offset)

        query, values = query_builder.select_query_builder(entity, f, limit=limit, offset=offset,
                                                           fields=fields, order_by=order_by)
        cursor = await self.pool.execute(query, tuple(values))
        cursor.row_factory = aiosqlite.Row
        result = await cursor.fetchall()
        await cursor.close()
        return result

    async def __find_transaction(self, entity: str, f: dict, limit: int | None = None,
                                 fields: list = [], offset: int | None = None,
                                 order_by: dict = {},
                                 connection: typing.Any = None) -> list[dict]:
        """Find all models when in a transaction. Internal use only."""
        query, values = query_builder.select_query_builder(entity, f, fields=fields, limit=limit,
                                                           offset=offset, order_by=order_by)
        connection.row_factory = aiosqlite.Row
        await connection.execute(query, tuple(values))
        result = await connection.fetchall()
        return result

    async def save(self, entity: str, data: dict, connection: typing.Any = None) -> dict:
        """Save model."""
        if connection:
            return await self.__save_transaction(entity, data, connection)

        query, values = query_builder.insert_query_builder(
            entity, data, engine="sqlite", param_style="?")
        cursor = await self.pool.execute(query, tuple(values))
        await cursor.fetchall()
        id_ = cursor.lastrowid
        await cursor.close()
        await self.pool.commit()
        return {"id": id_}

    async def __save_transaction(self, entity: str, data: dict,
                                 connection: typing.Any = None) -> dict:
        """Save model when in a transaction. Internal use only."""
        query, values = query_builder.insert_query_builder(
            entity, data, engine="sqlite", param_style="?")
        await connection.execute(query, tuple(values))
        await connection.fetchall()
        id_ = connection.lastrowid
        return {"id": id_}

    async def update(self, entity: str, entity_id: int, data: dict,
                     connection: typing.Any = None) -> None:
        """Update model."""
        if connection:
            return await self.__update_transaction(entity, entity_id, data, connection)
        query, values = query_builder.update_query_builder(
            entity, entity_id, data, param_style="?")
        cursor = await self.pool.execute(query, tuple(values))
        await cursor.close()
        await self.pool.commit()

    async def __update_transaction(self, entity: str, entity_id: int, data: dict,
                                   connection: typing.Any = None) -> None:
        """Update model when in a transaction. Internal use only."""
        query, values = query_builder.update_query_builder(
            entity, entity_id, data, param_style="?")
        await connection.execute(query, tuple(values))

    async def delete(self, entity: str, entity_id: int, connection: typing.Any = None) -> None:
        """Delete model."""
        if connection:
            return await self.__delete_transaction(entity, entity_id, connection)

        query, values = query_builder.delete_query_builder(entity, entity_id, param_style="?")
        cursor = await self.pool.execute(query, tuple(values))
        await cursor.close()
        await self.pool.commit()

    async def __delete_transaction(self, entity: str, entity_id: int,
                                   connection: typing.Any = None) -> None:
        """Delete model when in a transaction. Internal use only."""
        query, values = query_builder.delete_query_builder(entity, entity_id, param_style="?")
        await connection.execute(query, tuple(values))

    async def execute(self, query: str, values: tuple, connection: typing.Any = None) -> None:
        """Execute query."""
        if connection:
            return await self.__execute_transaction(query, values, connection)

        cursor = await self.pool.execute(query, values)
        cursor.row_factory = aiosqlite.Row
        result = await cursor.fetchall()
        await cursor.close()
        await self.pool.commit()
        return result

    async def __execute_transaction(self, query: str, values: tuple,
                                    connection: typing.Any = None) -> None:
        """Execute query when in a transaction. Internal use only."""
        connection.row_factory = aiosqlite.Row
        await connection.execute(query, tuple(values))
        result = await connection.fetchall()
        return result

    async def truncate_db(self) -> None:
        """Truncate all tables in the database."""
        cursor = await self.pool.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = await cursor.fetchall()
        await cursor.close()
        for table in tables:
            await self.pool.execute(f"DELETE FROM {table['name']}")
        await self.pool.commit()

    async def create_sqlite_in_memory_tables(self, create_table_sql: list[str]) -> None:
        """Create tables in memory."""
        for query in create_table_sql:
            query = query.replace("CREATE TABLE", "CREATE TABLE IF NOT EXISTS")
            await self.pool.execute(query)
        await self.pool.commit()

    async def get_tables(self) -> list[str]:
        """Get all tables in the database."""
        cursor = await self.pool.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = await cursor.fetchall()
        await cursor.close()
        return [table["name"] for table in tables if table["name"] != "sqlite_sequence"]
