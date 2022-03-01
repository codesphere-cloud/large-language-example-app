from flask_app import db
from datetime import datetime


class Receipt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(20))
    receipt_file = db.Column(db.String(20), nullable=False, default="receipt6-jpeg")
    submit_time = db.Column(db.DateTime, default=datetime.utcnow)
    results = db.relationship('Results', backref='Parent', lazy='dynamic')


class Results(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey('receipt.id'))
    description = db.Column(db.String())
    total = db.Column(db.String())
    quantity = db.Column(db.Integer())
    product = db.Column(db.String())
    footprint_per_100g = db.Column(db.Integer())
    typical_weight = db.Column(db.Integer())
    typical_footprint = db.Column(db.Integer())
    value_from = db.Column(db.String())
    category = db.Column(db.String())
    similarity_ratio = db.Column(db.Integer())
    footprint = db.Column(db.Integer())


