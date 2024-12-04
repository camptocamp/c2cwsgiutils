import sqlalchemy as sa
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Hello(Base):
    __tablename__ = "hello"
    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    value = sa.Column(sa.Text, nullable=False)
