from . import db
from sqlalchemy import Sequence
from datetime import datetime

class User(db.Model):
    __bind_key__ = 'db'
    id = db.Column(db.Integer, Sequence('User_sequence'), unique=True, nullable=False, primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.TIMESTAMP, default=datetime.now)