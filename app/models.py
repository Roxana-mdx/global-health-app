from datetime import datetime
from decimal import Decimal

from sqlalchemy import (BigInteger, DateTime, ForeignKey, Index, Numeric,
                        SmallInteger, String, Text, UniqueConstraint, func)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

import enum 

class Base(DeclarativeBase):
    pass

class Sex(str, enum.Enum):
    BOTH = "BTSX"
    MALE = "MLE"
    FEMALE = "FMLE"

class Source(Base):
    __tablename__ = "source"

    source_id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    url: Mapped[str | None] = mapped_column(Text)


class Country(Base):
    __tablename__ = "country"

    iso3: Mapped[str] = mapped_column(String(3), primary_key=True)
    iso2: Mapped[str | None] = mapped_column(String(2))
    gbd_location_id: Mapped[int | None] = mapped_column(unique=True)
    name: Mapped[str] = mapped_column(String(100))
    region: Mapped[str | None] = mapped_column(String(100))
    income_group: Mapped[str | None] = mapped_column(String(50))


class Indicator(Base):
    __tablename__ = "indicator"

    indicator_id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True)
    name: Mapped[str] = mapped_column(String(255))
    unit: Mapped[str | None] = mapped_column(String(50))
    measure: Mapped[str | None] = mapped_column(String(30))
    metric: Mapped[str | None] = mapped_column(String(30))
    age_group: Mapped[str | None] = mapped_column(String(30))
    source_id: Mapped[int] = mapped_column(ForeignKey("source.source_id"))

    source: Mapped[Source] = relationship()


class Observation(Base):
    __tablename__ = "observation"
    __table_args__ = (
        UniqueConstraint("country_iso3", "indicator_id", "year", "sex",
                         name="uq_observation"),
        Index("ix_observation_indicator_year", "indicator_id", "year"),
    )

    observation_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    country_iso3: Mapped[str] = mapped_column(ForeignKey("country.iso3"))
    indicator_id: Mapped[int] = mapped_column(ForeignKey("indicator.indicator_id"))
    year: Mapped[int] = mapped_column(SmallInteger)
    sex: Mapped[str] = mapped_column(String(10), server_default="BTSX")
    value: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    lower: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    upper: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    imported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    country: Mapped[Country] = relationship()
    indicator: Mapped[Indicator] = relationship()


class ImportLog(Base):
    __tablename__ = "import_log"

    import_id: Mapped[int] = mapped_column(primary_key=True)
    source_name: Mapped[str] = mapped_column(String(100))
    indicator_code: Mapped[str] = mapped_column(String(50))
    url: Mapped[str] = mapped_column(Text)
    rows_loaded: Mapped[int]
    imported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )