from typing import Annotated
from fastapi import Form

FormField = Annotated[str, Form()]
