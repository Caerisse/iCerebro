from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, DateTime, Sequence, ForeignKey, Table, UniqueConstraint
from sqlalchemy.orm import relationship, backref

class IgDb:
    def __init__(
        self,
        db_string='postgres://caerisse@localhost:5432/instagram'
    ):
        engine = create_engine(db_string)

        Session = sessionmaker(engine)
        self.session = Session()

Base = declarative_base()

follow_relations = Table(
    'follow_relations',
    Base.metadata,
    Column('follower_id', Integer, ForeignKey('users.id'), primary_key=True),
    Column('followed_id', Integer, ForeignKey('users.id'), primary_key=True),
    UniqueConstraint('follower_id', 'followed_id', name='unique_follows'),
)

class User(Base):
    __tablename__ = 'users'
    id = Column('id', Integer, Sequence('user_id_seq'), primary_key=True)
    date_checked = Column(DateTime, nullable=False)
    username = Column(String(50), nullable=False, unique=True)
    followers_count = Column(Integer, nullable=False, default=0)
    following_count = Column(Integer, nullable=False, default=0)
    posts_count = Column(Integer, nullable=False, default=0)

    following = relationship('User',
                             secondary='follow_relations',
                             primaryjoin=id == follow_relations.c.follower_id,
                             secondaryjoin=id == follow_relations.c.followed_id,
                             backref=backref('followers')
                             )
    posts = relationship('Post')
    comments = relationship('Comment')

class Post(Base):
    __tablename__ = 'posts'

    id = Column('id', Integer, Sequence('post_id_seq'), primary_key=True)
    date_posted = Column('date_posted', DateTime, nullable=False)
    user_id = Column('user_id', ForeignKey('users.id'), nullable=False)
    src = Column('src', String(200), nullable=False)
    caption = Column('caption', String(2200), nullable=True)

    user = relationship('User', foreign_keys=[user_id])
    comments = relationship('Comment')

    ig_desciption = Column('ig_desciption', String(500))
    objects_detected = Column('objects_detected', String(500))
    classified_as = Column('classified_as', String(500))


class Comment(Base):
    __tablename__ = 'comments'

    id = Column('id', Integer, Sequence('comment_id_seq'), primary_key=True)
    date_posted = Column('date_posted', DateTime, nullable=False)
    user_id = Column('user_id', ForeignKey('users.id'))
    post_id = Column('post_id', ForeignKey('posts.id'))
    text = Column('text', String(2200))

    user = relationship('User', foreign_keys=[user_id])
    post = relationship('Post', foreign_keys=[post_id])


db_string = 'postgres://caerisse@localhost:5432/instagram'
Base.metadata.create_all(create_engine(db_string))

'''
Usage:
from database import IgDb, User, Post, Comment

db = IgDb()
try:
    try:
        do things 
        commit
    expect
        db.session.rollback()
finally:
    db.session.close()

user = User(
    date_checked = datetime.datetime.now(),
    username = 'test1',
    followers_count = 0,
    following_count = 10,
    posts_count = 6,
)
db.session.add(user)
db.session.commit()

user = User(
    date_checked = datetime.datetime.now(),
    username = 'test10',
    followers_count = 0,
    following_count = 10,
    posts_count = 6,
)
db.session.add(user)
db.session.commit()

user2 = User(
    date_checked = datetime.datetime.now(),
    username = 'test21',
    followers_count = 30,
    following_count = 1,
    posts_count = -5,
)
db.session.add(user)
db.session.commit()

user1 = User(
    date_checked = datetime.datetime.now(),
    username = 'test31',
    followers_count = 0,
    following_count = None,
    posts_count = 6,
)
db.session.add(user)
db.session.commit()

db.session.add_all( [user1, user2, user3, ...] )
db.session.commit()

user1.following.append(user2) === user2.followers.append(user1)
db.session add
db.session commit

'''


