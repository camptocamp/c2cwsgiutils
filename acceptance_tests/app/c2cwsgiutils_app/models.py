import sqlalchemy as sa
import sqlalchemy.ext.declarative

Base = sqlalchemy.ext.declarative.declarative_base()


class Hello(Base):
    __tablename__ = "hello"
    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    value = sa.Column(sa.Text, nullable=False)
