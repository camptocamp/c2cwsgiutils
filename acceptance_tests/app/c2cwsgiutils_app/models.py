from c2cwsgiutils import db
import sqlalchemy as sa
import sqlalchemy.ext.declarative

DBSession = None
Base = sqlalchemy.ext.declarative.declarative_base()


def init(config):
    global DBSession
    DBSession = db.setup_session(config, "sqlalchemy", "sqlalchemy_slave", force_slave=["POST /api/hello"])[0]


class Hello(Base):
    __tablename__ = "hello"
    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    value = sa.Column(sa.Text, nullable=False)
