import sqlalchemy
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Boolean, Date, ForeignKey

# Define the Postgres engine using Postgres Connector/Python
engine = sqlalchemy.create_engine(
    'postgres://root:password@127.0.0.1:5432/db',
    echo=True)

# Define and create the table
Base = declarative_base()


class User(Base):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(50))

    def __repr__(self):
        return "<User(id='%s', email='%s')>" % (
            self.id, self.email)


class Organization(Base):
    __tablename__ = 'organization'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    domain_url = Column(String(100))
    url = Column(String(500))

    def __repr__(self):
        return "<organization(id='%s', name='%s', domain_url='%s', url='%s')>" % (
            self.id, self.name, self.domain_url, self.url)


class Subscription(Base):
    __tablename__ = 'subscription'

    id = Column(Integer, primary_key=True, autoincrement=True)
    organization_id = Column(Integer, ForeignKey('organization.id'))
    user_id = Column(Integer, ForeignKey('user.id'))

    def __repr__(self):
        return "<Subscription(id='%s', organization_id='%s', user_id='%s')>" % (
            self.id, self.organization_id, self.user_id)


class Link(Base):
    __tablename__ = 'link'

    id = Column(Integer, primary_key=True, autoincrement=True)
    organization_id = Column(Integer, ForeignKey('organization.id'))
    body = Column(String(200), nullable=False)
    href = Column(String(200), nullable=False)
    processed = Column(Boolean, default=False)
    create_date = Column(Date, nullable=False)

    def __repr__(self):
        return "<Link(id='%s', organization_id='%s', body='%s', href='%s', processed='%s', create_date='%s')>" % (
            self.id, self.organization_id, self.body, self.href, self.processed, self.create_date)


class Content(Base):
    __tablename__ = 'content'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('user.id'))
    link_id = Column(Integer, ForeignKey('link.id'))
    relevant = Column(Boolean, default=False)
    processed = Column(Boolean, default=False)
    create_date = Column(Date, nullable=False)

    def __repr__(self):
        return "<Content(id='%s', user_id='%s', link_id='%s', relevant='%s', processed='%s', create_date='%s')>" % (
            self.id, self.user_id, self.link_id, self.relevant, self.processed, self.create_date)


class Keyword(Base):
    __tablename__ = 'keyword'

    id = Column(Integer, primary_key=True, autoincrement=True)
    organization_id = Column(Integer, ForeignKey('organization.id'))
    user_id = Column(Integer, ForeignKey('user.id'))
    keyword = Column(String(50), nullable=False)
    exclude = Column(Boolean, default=False)

    def __repr__(self):
        return "<Keyword(id='%s', organization_id='%s', user_id='%s', keyword='%s', exclude='%s')>" % (
            self.id, self.organization_id, self.user_id, self.keyword, self.exclude)


Base.metadata.create_all(engine)
