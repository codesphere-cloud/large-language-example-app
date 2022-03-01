from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import os
from flask_migrate import Migrate
from flask_restful import Api
import pandas as pd

basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
api = Api(app)


app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'app.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'bd6bcf5b25cab2f6fadcbf7bf052b6c1'
app.config['MAX_CONTENT_LENGTH'] = 4 * 1024 * 1024  # 4MB max-limit.

db = SQLAlchemy(app)

migrate = Migrate(app, db)


from flask_app import routes, models
