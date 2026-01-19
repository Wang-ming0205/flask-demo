from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

# Extensions are created once and initialized in create_app().
db = SQLAlchemy()
login_manager = LoginManager()
