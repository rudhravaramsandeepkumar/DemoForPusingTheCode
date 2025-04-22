from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def init_app(app):
    # Configure the DB here or in app.py
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_BINDS'] = {
        'db': "sqlite:///OnlineFuelOrderingSystem.sqlite"
    }
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///OnlineFuelOrderingSystem.sqlite'

    db.init_app(app)
    app.logger.info('Initialized models')

    with app.app_context():
        from .user import User
        from .fuel_type import FuelType
        from .order import Order
        from .delivery_schedule import DeliverySchedule
        from .review import Review
        from .fuel import Fuel

        db.create_all()
        db.session.commit()
        app.logger.debug('All tables are created')
