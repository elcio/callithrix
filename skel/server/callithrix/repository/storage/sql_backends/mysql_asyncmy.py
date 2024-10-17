"""Postgresql asyncpg backend."""
import asyncmy
from asyncmy.cursors import DictCursor
from . import query_builder
import typing

class SQLBackend:
    """SQL backend."""

    def __init__(self, connection_string: str, connection_params: dict):
        """Initialize."""
        self.connection_string = connection_string
        self.connection_params = connection_params
        self.pool: typing.Any = None

    async def init(self, **kwargs) -> object:
        """Initialize."""
        self.connection_params["port"] = (self.connection_params["port"]
                                          and int(self.connection_params["port"]) or 3306)
        self.pool = await asyncmy.create_pool(**self.connection_params, **kwargs)

    async def close(self) -> None:
        """Close."""
        self.pool.close()
        await self.pool.wait_closed()

    async def start_transaction(self) -> object:
        """Start transaction."""
        async with self.pool.acquire() as conn:
            cursor = conn.cursor(cursor=DictCursor)
            return {"connection": conn, "cursor": cursor}

    async def commit(self, connection: typing.Any) -> None:
        """Commit."""
        await connection["connection"].commit()

    async def rollback(self, connection: typing.Any) -> None:
        """Rollback."""
        await connection["connection"].rollback()

    async def end_transaction(self, _: typing.Any) -> None:
        """End transaction."""

    async def find(self, entity: str, f: dict, limit: int | None = None, fields: list = [],
                   offset: int | None = None, order_by: dict = {},
                   connection: typing.Any = None) -> list[dict]:
        """Find all models."""
        if connection:
            return await self.__find_transaction(entity, f, limit=limit, fields=fields,
                                                 offset=offset, order_by=order_by,
                                                 connection=connection)

        query, values = query_builder.select_query_builder(entity, f, limit=limit, fields=fields,
                                                           order_by=order_by, offset=offset,
                                                           param_style="%s")
        async with self.pool.acquire() as conn:
            async with conn.cursor(cursor=DictCursor) as cur:
                await cur.execute(query, values)
                result = await cur.fetchall()
                return result

    async def __find_transaction(self, entity: str, f: dict, limit: int | None = None,
                                 fields: list = [], offset: int | None = None,
                                 order_by: dict = {},
                                 connection: typing.Any = None) -> list[dict]:
        """Find transaction."""
        query, values = query_builder.select_query_builder(entity, f, limit=limit, fields=fields,
                                                           order_by=order_by, offset=offset,
                                                           param_style="%s")
        await connection["cursor"].execute(query, values)
        return await connection["cursor"].fetchall()

    async def save(self, entity: str, data: dict, connection: typing.Any) -> dict:
        """Save model."""
        if connection:
            return await self.__save_transaction(entity, data, connection)

        query, values = query_builder.insert_query_builder(
            entity, data, engine="mysql", param_style="%s")
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, tuple(values))
                await conn.commit()
                result = cur.lastrowid
                return {"id": result}

    async def __save_transaction(self, entity: str, data: dict, connection: typing.Any) -> dict:
        """Save transaction."""
        query, values = query_builder.insert_query_builder(
            entity, data, engine="mysql", param_style="%s")
        await connection["cursor"].execute(query, tuple(values))
        result = connection["cursor"].lastrowid
        return {"id": result}

    async def update(self, entity: str, entity_id: int, data: dict,
                     connection: typing.Any) -> None:
        """Update model."""
        if connection:
            return await self.__update_transaction(entity, entity_id, data, connection)

        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                query, values = query_builder.update_query_builder(
                    entity, entity_id, data, param_style="%s")
                await cur.execute(query, tuple(values))
                await conn.commit()

    async def __update_transaction(self, entity: str, entity_id: int, data: dict,
                                   connection: typing.Any) -> None:
        """Update transaction."""
        query, values = query_builder.update_query_builder(
            entity, entity_id, data, param_style="%s")
        await connection["cursor"].execute(query, tuple(values))

    async def delete(self, entity: str, entity_id: int, connection: typing.Any) -> None:
        """Delete model."""
        if connection:
            return await self.__delete_transaction(entity, entity_id, connection)

        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                query, values = query_builder.delete_query_builder(
                    entity, entity_id, param_style="%s")
                await cur.execute(query, tuple(values))
                await conn.commit()

    async def __delete_transaction(self, entity: str, entity_id: int,
                                   connection: typing.Any) -> None:
        """Delete transaction."""
        query, values = query_builder.delete_query_builder(
            entity, entity_id, param_style="%s")
        await connection["cursor"].execute(query, tuple(values))

    async def execute(self, query: str, values: tuple, connection: typing.Any) -> None:
        """Execute query."""
        if connection:
            return await self.__execute_transaction(query, values, connection)

        async with self.pool.acquire() as conn:
            async with conn.cursor(cursor=DictCursor) as cur:
                await cur.execute(query, *values)
                await conn.commit()
                return await cur.fetchall()

    async def __execute_transaction(self, query: str, values: tuple,
                                    connection: typing.Any) -> None:
        """Execute transaction."""
        await connection["cursor"].execute(query, *values)
        return await connection["cursor"].fetchall()

    async def truncate_db(self) -> None:
        """Truncate all tables in the database."""
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SET FOREIGN_KEY_CHECKS = 0")
                await cur.execute("SHOW TABLES")
                tables = await cur.fetchall()
                for table in tables:
                    await cur.execute(f"TRUNCATE table {table[0]}")
                await conn.commit()

    async def get_tables(self) -> list[str]:
        """Get tables."""
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SHOW TABLES")
                tables = await cur.fetchall()
                return [table[0] for table in tables]
