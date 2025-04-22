from . import db
from sqlalchemy import Sequence


class Fuel(db.Model):
    __bind_key__ = 'db'
    id = db.Column(db.Integer, Sequence('Fuele_sequence'), unique=True, nullable=False, primary_key=True)
    name = db.Column(db.String(100))
    price = db.Column(db.Float)
    stock = db.Column(db.Float)
    fuel_type_id = db.Column(db.Integer)
    image_url = db.Column(db.String(255))  # optional
