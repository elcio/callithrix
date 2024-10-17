"""Postgresql asyncpg backend."""
import asyncpg
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
        self.pool = await asyncpg.create_pool(**self.connection_params, **kwargs)

    async def close(self) -> None:
        """Close."""
        await self.pool.close()

    async def start_transaction(self) -> object:
        """Start transaction."""
        conn = await self.pool.acquire()
        transaction = conn.transaction()
        await transaction.start()
        return {"connection": conn, "transaction": transaction}

    async def commit(self, connection: typing.Any) -> None:
        """Commit."""
        await connection["transaction"].commit()

    async def rollback(self, connection: typing.Any) -> None:
        """Rollback."""
        await connection["transaction"].rollback()

    async def end_transaction(self, connection: typing.Any) -> None:
        """End transaction."""
        await self.pool.release(connection["connection"])

    async def find(self, entity: str, f: dict, fields: list = [], limit: int | None = None,
                   offset: int | None = None, order_by: dict = {},
                   connection: typing.Any = None) -> list[dict]:
        """Find all models."""
        conn = connection and connection["connection"] or await self.pool.acquire()
        query, values = query_builder.select_query_builder(entity, f, fields=fields, limit=limit,
                                                           offset=offset, order_by=order_by)
        result = await conn.fetch(query, *values)
        await self.pool.release(conn) if not connection else None
        return result

    async def save(self, entity: str, data: dict, connection: typing.Any = None) -> dict:
        """Save model."""
        conn = connection and connection["connection"] or await self.pool.acquire()
        query, values = query_builder.insert_query_builder(entity, data, engine="postgres")
        result = await conn.fetchrow(query, *values)
        await self.pool.release(conn) if not connection else None
        return result

    async def update(self, entity: str, entity_id: int, data: dict,
                     connection: typing.Any = None) -> None:
        """Update model."""
        conn = connection and connection["connection"] or await self.pool.acquire()
        query, values = query_builder.update_query_builder(entity, entity_id, data)
        result = await conn.execute(query, *values)
        await self.pool.release(conn) if not connection else None
        return result

    async def delete(self, entity: str, entity_id: int, connection: typing.Any = None) -> None:
        """Delete model."""
        conn = connection and connection["connection"] or await self.pool.acquire()
        query, values = query_builder.delete_query_builder(entity, entity_id)
        result = await conn.execute(query, *values)
        await self.pool.release(conn) if not connection else None
        return result

    async def execute(self, query: str, values: tuple, connection: typing.Any = None) -> None:
        """Execute query."""
        conn = connection and connection["connection"] or await self.pool.acquire()
        result = await conn.fetch(query, *values)
        await self.pool.release(conn) if not connection else None
        return result

    async def truncate_db(self) -> None:
        """Truncate all tables in the database."""
        async with self.pool.acquire() as conn:
            q = "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
            tables = await conn.fetch(q)
            for table in tables:
                await conn.execute(f"TRUNCATE {table['table_name']} RESTART IDENTITY CASCADE")

    async def get_tables(self) -> list[str]:
        """Get tables."""
        async with self.pool.acquire() as conn:
            q = "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
            tables = await conn.fetch(q)
            return [table["table_name"] for table in tables]
