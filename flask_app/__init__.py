import os
from flask import Flask
from flask_restful import Api

basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
api = Api(app)


app.config['SECRET_KEY'] = 'bd6bcf5b25cab2f6fadcbf7bf052b6c1'

from flask_app import routes
