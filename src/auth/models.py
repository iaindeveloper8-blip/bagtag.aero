from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base


class User(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(254), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(256), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    bags: Mapped[list["Bag"]] = relationship("Bag", back_populates="user")  # type: ignore[name-defined]  # noqa: F821
    trips: Mapped[list["Trip"]] = relationship("Trip", back_populates="user")  # type: ignore[name-defined]  # noqa: F821
    packing_templates: Mapped[list["PackingTemplate"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "PackingTemplate", back_populates="user"
    )
    notifications: Mapped[list["Notification"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Notification", back_populates="user", cascade="all, delete-orphan"
    )
