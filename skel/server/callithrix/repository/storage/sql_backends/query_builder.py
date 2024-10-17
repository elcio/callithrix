"""Simple SQL query builder."""

def insert_query_builder(
        table_name: str, data: dict, engine: str, param_style: str = "$%d") -> tuple[str, list]:
    """Build insert query."""
    last_id_query = {
        "postgres": "RETURNING id",
        "mysql": "",
        "sqlite": "",
    }

    if param_style == '$%d':
        values = ', '.join(param_style % (i + 1) for i in range(len(data)))
    else:
        values = ', '.join(param_style for _ in range(len(data)))
    columns = ', '.join(data.keys())
    query = f"INSERT INTO {table_name} ({columns}) VALUES ({values}) {last_id_query[engine]}"
    values_tuple = data.values()
    return query, values_tuple  # type: ignore

def select_query_builder(table_name: str, data: dict = {}, fields: list = [],
                         limit: int | None = None,
                         offset: int | None = None, order_by: dict = {},
                         param_style: str = "$%d") -> tuple[str, list]:
    """Build select query.

    Fields, table_name and order_by are not sanitized, so be careful.
    """
    columns = "*" if not fields else ", ".join(fields)
    query = [f"SELECT {columns} FROM {table_name}"]
    values = []
    if data:
        query.append("WHERE")
    value_count = 0
    for key, value in data.items():
        value_count += 1
        first_clause = value_count == 1
        if not isinstance(value, tuple):
            value = ("=", value)

        and_or = __and_or(key)
        op, value_count = __get_operation(value, value_count, param_style)
        if and_or["token"] and not first_clause:
            query.append(and_or['token'])
        query.append(and_or['key'])
        query.append(op)
        _value = value[1]
        if not isinstance(_value, tuple) and not isinstance(_value, list):
            _value = (_value,)
        if value[0].lower() != 'sql':
            values.extend(_value)

    query.extend(__handle_order_by(order_by))
    query.extend(__handle_limit_offset(limit, offset))
    query = ' '.join(query)
    return query, values

def __and_or(key: str) -> dict:
    """Return AND or OR."""
    tokens = {
        "&": "AND",
        "|": "OR",
    }
    token = tokens.get(key[0], "AND")
    return {
        "key": key.replace("&", "").replace("|", ""),
        "token": token
    }

def __get_operation(value: tuple, value_count: int, param_style: str) -> tuple:
    """Return operation."""
    if value[0].lower() == 'sql':
        return value[1], value_count
    operations = {
        "=": "=",
        "!=": "!=",
        ">": ">",
        ">=": ">=",
        "<": "<",
        "<=": "<=",
        "in": "IN (",
        "not in": "NOT IN (",
        "like": "LIKE",
        "not like": "NOT LIKE",
        "ilike": "ILIKE",
        "not ilike": "NOT ILIKE",
    }
    op_key = value[0].lower()
    op = operations[op_key]
    # if op_key in ("in", "not_in"):
    if op_key == "in" or op_key == "not in":
        op, value_count = __handle_in_not_in(op, value, value_count, param_style)
    else:
        op += f" {__determine_placeholder(param_style, value_count)}"
    return op, value_count

def __handle_in_not_in(op: str, value: tuple, value_count: int, param_style: str) -> tuple:
    """Handle in."""
    for _ in range(len(value[1])):
        op += f"{__determine_placeholder(param_style, value_count)}, "
        value_count += 1
    value_count -= 1
    op = op[:-2] + ")"
    return op, value_count

def __determine_placeholder(param_style: str, count: int) -> str:
    """Determine placeholder."""
    if param_style == '$%d':
        return param_style % count
    return param_style

def __handle_limit_offset(limit: int | None, offset: int | None) -> list:
    """Build limit and offset."""
    query = []
    if limit:
        query.append(f"LIMIT {int(limit)}")
    if limit and offset:
        query.append(f"OFFSET {int(offset)}")
    return query

def __handle_order_by(order_by: dict | None) -> list:
    """Handle order by.

    Example:
        order_by = {"email": "DESC", "id": "ASC"}
    It will return:
        ["ORDER BY", "email", "ASC", "id", "DESC"]
    """
    if not order_by:
        return []
    query = ["ORDER BY"]
    allowed_order_by = ("ASC", "DESC")
    total = len(order_by)
    comma = ","
    for count, (key, value) in enumerate(order_by.items()):
        comma = "," if count < total - 1 else ""
        query.append(f"{key}")
        if value.upper() in allowed_order_by:
            query.append(f"{value}{comma}")

    return query

def update_query_builder(
        table_name: str, id_: int, data: dict, param_style: str = "$%d") -> tuple[str, list]:
    """Build update query."""
    if not data:
        raise ValueError("No data to update")
    query = [f"UPDATE {table_name} SET "]
    values = []
    _param = ''
    for key, value in data.items():
        _param = param_style
        if param_style == '$%d':
            _param = param_style % (len(values) + 1)
        if key == "id":
            continue
        query.append(f"{key} = {_param}, ")
        values.append(value)
    query[-1] = query[-1][:-2]
    if param_style == '$%d':
        _param = param_style % (len(values) + 1)

    query.append(f" WHERE id = {_param}")
    values.append(id_)
    query = ''.join(query)
    return query, values

def delete_query_builder(table_name: str, id_: int, param_style: str = "$%d") -> tuple[str, tuple]:
    """Build delete query."""
    if param_style == '$%d':
        param_style = param_style % 1
    query = f"DELETE FROM {table_name} WHERE id = {param_style}"
    return query, (id_,)
