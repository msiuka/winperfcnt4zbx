from flask import Flask
from config import Config

mssqlix = Flask(__name__)
mssqlix.config.from_object(Config)

from app import routes
