from typing import Iterator

from sqlalchemy.orm import Session

from .db import get_session


def get_db() -> Iterator[Session]:
    yield from get_session()
