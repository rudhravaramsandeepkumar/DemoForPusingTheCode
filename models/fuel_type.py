from . import db
from sqlalchemy import Sequence


class FuelType(db.Model):
    __bind_key__ = 'db'
    id = db.Column(db.Integer, Sequence('FuelType_sequence'), unique=True, nullable=False, primary_key=True)
    type_name = db.Column(db.String(100), nullable=False)
