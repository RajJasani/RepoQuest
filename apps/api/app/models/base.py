import uuid
from datetime import datetime
from typing import Annotated, Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, mapped_column

uuid_pk = Annotated[
    uuid.UUID,
    mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    ),
]

timestamptz_now = Annotated[
    datetime,
    mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    ),
]

timestamptz_null = Annotated[
    Optional[datetime],
    mapped_column(
        DateTime(timezone=True),
        nullable=True,
    ),
]

embedding_768 = Annotated[
    Optional[list[float]],
    mapped_column(Vector(768), nullable=True),
]


class Base(DeclarativeBase):
    pass
