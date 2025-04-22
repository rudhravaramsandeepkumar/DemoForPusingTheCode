from . import db
from sqlalchemy import Sequence


class DeliverySchedule(db.Model):
    __bind_key__ = 'db'
    id = db.Column(db.Integer, Sequence('DeliverySchedule_sequence'), unique=True, nullable=False, primary_key=True)
    delivery_time = db.Column(db.String(100), nullable=False)
    availability = db.Column(db.Boolean, default=True)
