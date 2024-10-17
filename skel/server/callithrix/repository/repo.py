"""Base repository."""
from datetime import datetime
from pydantic import BaseModel, SecretStr
import typing
import hashlib

class Repository:
    """Base repository."""

    def __init__(self, storage, secret_key: str = None):
        """Initialize repository."""
        self.storage = storage
        self.secret_key = secret_key

    async def get(self, entity: str, entity_id: int, connection: typing.Any = None,
                  serialize: bool = True) -> dict | None:
        """Get model."""
        result = await self.find(entity, {"id": entity_id}, connection=connection,
                                 serialize=serialize)
        return result[0] if result else None

    async def find(self, entity: str, f: dict = {}, fields: list = [],
                   connection: typing.Any = None, limit: int | None = None,
                   offset: int | None = None, order_by: dict = {},
                   serialize: bool = True) -> list[dict]:
        """Find all models."""
        result = await self.storage.find(entity, f, fields=fields, limit=limit, offset=offset,
                                         order_by=order_by, connection=connection)
        if serialize:
            result = list(map(dict, result))
        return result

    async def find_one(self, entity: str, f: dict = {}, fields: list = [],
                       offset: int | None = None, connection: typing.Any = None,
                       order_by: dict = {"id": "ASC"}, serialize: bool = True) -> list[dict]:
        """Filter by the kwargs and return one item, if available."""
        response = await self.storage.find(
            entity.lower(), f, fields=fields, limit=1, offset=offset, order_by=order_by,
            connection=connection)
        if response:
            return list(map(dict, response))[0] if serialize else response[0]
        return None

    def encode_password(self, password: str, id: int) -> str:
        """Encode password."""
        return hashlib.sha256(f"{password}{self.secret_key}{id}".encode()).hexdigest()

    def dict_from_entity(self, entity: BaseModel) -> dict:
        data = entity.dict()
        has_password = False
        for k, v in data.items():
            if isinstance(v, SecretStr):
                data[k] = self.encode_password(v.get_secret_value(), data.get('id'))
                has_password = True
        return data, has_password

    async def save(self, entity: str, data: dict | BaseModel, connection: typing.Any = None) -> dict:
        """Save model."""
        has_password = False
        if not isinstance(data, dict):
            original = data
            data, has_password = self.dict_from_entity(data)
        if data.get('id'):
            return await self.update(entity, data['id'], data, connection=connection)
        data["created_at"] = datetime.now()
        data["updated_at"] = datetime.now()
        saved = await self._save(entity, data, connection=connection)
        if has_password:
            original.id = saved['id']
            data, _ = self.dict_from_entity(original)
            await self._update(entity, data['id'], data, connection=connection)
        return saved

    async def _save(self, entity: str, data: dict, connection: typing.Any = None) -> dict:
        """Save model. Do not update created_at or updated_at."""
        return await self.storage.save(entity, data, connection=connection)

    async def update(self, entity: str, entity_id: int, data: dict | BaseModel,
                     connection: typing.Any = None) -> None:
        if not isinstance(data, dict):
            data, _ = self.dict_from_entity(data)
        """Update model."""
        data["updated_at"] = datetime.now()
        await self._update(entity, entity_id, data, connection=connection)
        return {'id': data['id']}

    async def _update(self, entity: str, entity_id: int, data: dict,
                      connection: typing.Any = None) -> None:
        """Update model. Do not update updated_at."""
        return await self.storage.update(entity, entity_id, data, connection=connection)

    async def delete(self, entity: int, entity_id: int, connection: typing.Any = None) -> None:
        """Delete model."""
        return await self.storage.delete(entity, entity_id, connection=connection)

    async def get_tables(self) -> list[str]:
        """Get tables."""
        return await self.storage.get_tables()
