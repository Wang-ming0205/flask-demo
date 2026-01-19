import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from flask import url_for

app = create_app()

with app.test_request_context():
    print("logout url:", url_for('main.logout'))
