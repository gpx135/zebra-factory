from . import db
from flask_login import UserMixin

class User(UserMixin, db.Model):
    __tablename__ = "user"
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String, unique=True)
    password = db.Column(db.String)
    name = db.Column(db.String)

class SalmonOrder(db.Model):
    __tablename__ = "salmon_orders"
    
    id = db.Column(db.Integer, primary_key=True)
    customer = db.Column(db.String)
    date = db.Column(db.Date)
    product = db.Column(db.String)
    price = db.Column(db.Float)
    quantity = db.Column(db.Integer)
    
    weights = db.relationship("SalmonOrderWeight", backref="order")

class SalmonOrderWeight(db.Model):
    __tablename__ = "salmon_order_weight"
    
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('salmon_orders.id'))
    quantity = db.Column(db.Float)
    production_time = db.Column(db.DateTime)
