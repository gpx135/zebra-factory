from . import db
from flask_login import UserMixin
from datetime import datetime
from sqlalchemy.sql import func

class User(UserMixin, db.Model):
    """User model
    
    Represents a user with id, email, password and name.
    """
    __tablename__ = "salmon_user"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(45), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    name = db.Column(db.String(45), nullable=False)
    role = db.Column(db.String(45), nullable=False, default="viewer")


class Customer(db.Model):
    """Customer model 
    
    Represents a customer with id, customer name, address, 
    company name, phone number, priority level, and packing type.
    """
    __tablename__ = "salmon_customer"
    id = db.Column(db.Integer, primary_key=True)
    customer = db.Column(db.String)
    address = db.Column(db.String)
    company = db.Column(db.String)
    phone = db.Column(db.String)
    priority = db.Column(db.String)
    packing = db.Column(db.String)
    location_internal_id = db.Column(db.Integer)
    fish_size = db.Column(db.String)
    active = db.Column(db.Integer)
    note = db.Column(db.String)
    
    @classmethod
    def get_active_customers(cls):
        """
        Fetch all active customers, ordered alphabetically.
        """
        return cls.query.filter(cls.active == 1).order_by(cls.customer.asc()).all()
    
    @classmethod
    def get_distinct_fish_sizes(cls):
        """
        Fetch distinct fish sizes from active customers, ordered alphabetically.
        """
        fish_sizes = cls.query.with_entities(cls.fish_size).distinct().order_by(cls.fish_size.asc()).all()
        return [size[0] for size in fish_sizes if size[0]]

class Order(db.Model):
    """Order model
    
    Represents an order with id, customer, date, product, 
    price, quantity and weights (relationship to Weight).
    """
    __tablename__ = "salmon_orders"
    id = db.Column(db.Integer, primary_key=True)
    customer = db.Column(db.String, db.ForeignKey('salmon_customer.customer'))
    date = db.Column(db.Date)
    product = db.Column(db.String)
    price = db.Column(db.Numeric(precision=10, scale=4))
    quantity = db.Column(db.Integer)
    weights = db.relationship('Weight', backref='salmon_order', lazy=True, cascade='all, delete, delete-orphan')
    fish_size = db.Column(db.String)
    entry_time = db.Column(db.DateTime, default=datetime.utcnow)
    note = db.Column(db.String)

    __table_args__ = (
        db.UniqueConstraint('date', 'product', 'customer', 'price', name='unique_order'),
    )


class DeliveryNoteImage(db.Model):
    """Delivery note model
    """
    __tablename__ = "salmon_delivery_note_images"
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('salmon_orders.id'), nullable=False)
    image_url = db.Column(db.String, nullable=False, unique=True)
    uploaded_at = db.Column(db.DateTime, default=func.now(), nullable=False)


class Weight(db.Model):
    """Weight model
    
    Represents the weight details of an order with id, order_id (foreign key to Order), 
    quantity, production_time, and batch_number.
    """
    __tablename__ = "salmon_order_weight"
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('salmon_orders.id'), nullable=False)
    quantity = db.Column(db.Float)
    production_time = db.Column(db.DateTime)
    batch_number = db.Column(db.Integer)


class Product(db.Model):
    """Product model
    
    Represents a product name with id, product name, 
    and product type (relationship to Order product).
    """
    __tablename__ = "salmon_product_name"
    id = db.Column(db.Integer, primary_key=True)
    product_name = db.Column(db.String, db.ForeignKey('salmon_orders.product'))
    product_type = db.Column(db.String)
    active = db.Column(db.Integer)
    note = db.Column(db.String)
    display_name = db.Column(db.String)
    @classmethod
    def get_active_products(cls):
        """
        Fetch all active products, ordered alphabetically.
        """
        return cls.query.filter(cls.active == 1).order_by(cls.product_name.asc()).all()


class MaterialInfo(db.Model):
    """MaterialInfo model
    
    Represents the material information of an order with id, farmer, 
    date, and batch_number (foreign key to Weight).
    """
    __tablename__ = "salmon_material_info"
    id = db.Column(db.Integer, primary_key=True)
    farmer = db.Column(db.String)
    date = db.Column(db.Date)
    batch_number = db.Column(db.Integer, db.ForeignKey('salmon_order_weight.batch_number'))