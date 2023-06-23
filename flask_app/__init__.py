import os
from flask import Flask


basedir = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__)
app.config['SECRET_KEY'] = 'bd6bcf5b25cab2f6fadcbf7bf052b6c1'

from flask_app import routes
