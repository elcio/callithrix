"""Database migration module. Reads the domain model and generate migrations using pydal."""
from pydal import DAL, Field, SQLCustomType

def migrate(models, db_url: str,
            migration_folder: str = "migrations", migrate: bool = True,
            fake_migrate: bool = False) -> list[str]:
    """Instantiate pydal, reads the domain and create the tables in the database."""
    db = DAL(
        db_url.replace("sqlite://:memory:", "sqlite:memory"),
        folder=migration_folder,
        migrate=migrate,
        fake_migrate=fake_migrate,
    )
    create_tables_executed_sql = []
    ignored = ['MelBase', 'BaseModel']
    to_migrate = []
    for entity in models.__dict__.values():
        if hasattr(entity, "schema") and entity.__name__ not in ignored:
            to_migrate.append((-getattr(entity, 'priority', 0), str(entity), entity))
    to_migrate.sort()
    for _, __, entity in to_migrate:
        create_tables_executed_sql.append(create_table(
            db,
            entity.__name__.lower(),
            entity.schema()["properties"],
            audit_table=get_audit_table(entity)
        ))
    db._adapter.close_connection()
    return create_tables_executed_sql


def get_audit_table(entity):
    if 'Config' in dir(entity):
        return getattr(entity.Config, "audit_table", "")
    return ""


def create_table(db: DAL, entity: str, schema: dict, audit_table: str = ""):
    """Create table."""
    audit_columns = audit_table and [
        Field("created_at", "datetime"),
        Field("updated_at", "datetime"),
        Field("created_by", f"reference {audit_table}"),
        Field("updated_by", f"reference {audit_table}"),
    ] or []
    db.define_table(
        entity,
        *audit_columns,
        *[Field(col, determine_column_type(v, db), **col_metadata(v))
            for col, v in schema.items() if col != 'id'])
    return db._lastsql and db._lastsql[0]

def determine_column_type(meta: dict, db: DAL) -> str:
    """Determine the column type from pydantic schema."""
    meta_type = meta.get("type", meta.get('anyOf', [{}])[0].get('type', 'string'))
    types = {
        "string": "string",
        "integer": "integer",
        "number": "double",
        "boolean": boolean_field(),
        "datetime": "datetime",
    }
    meta_type = get_type_from_format(meta) or meta_type
    fk = foreign_key(meta)
    forced_type = translate_type_engine(meta.get("force_type"), db)  # type: ignore
    return fk or forced_type or types[meta_type]

def get_type_from_format(meta: dict) -> str | None:
    """Get type from format."""
    formats = {
        "date-time": 'datetime',
    }
    return formats.get(meta.get("format"))  # type: ignore

def foreign_key(meta: dict) -> str | None:
    """Get foreign key."""
    reference = meta.get("reference")
    return reference and f"reference {reference}"

def col_metadata(meta: dict) -> dict:
    """Get column metadata."""
    default_meta = {
        "notnull": meta.get("notnull", False),
        "unique": meta.get("unique", False),
        "length": meta.get("maxLength", 128),
    }
    return default_meta


def boolean_field():
    """Return a pydal custom boolean SQL type.

    Returns:
        SQLCustomType: boolean custom type.
    """
    realbool = SQLCustomType(
        type="boolean",
        native="boolean",
        encoder=(lambda x: "true" if x else "false"),
        decoder=(lambda x: True if str(x) == "True" else False),
    )
    return realbool

def translate_type_engine(type_: str, db: DAL) -> str | None:
    """Translate type for the differente db engines."""
    types = {
        "mysql": {
            "jsonb": "json"
        },
        "sqlite": {
            "jsonb": "json"
        }
    }
    return types.get(db._adapter.dbengine, {}).get(type_, type_)
