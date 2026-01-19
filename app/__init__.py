import os

from flask import Flask

from .config import Config
from .extensions import db, login_manager


def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(Config)

    # instance folder
    os.makedirs(app.instance_path, exist_ok=True)

    # ===== 資料庫路徑：instance/eq_manage.db =====
    db_path = os.path.join(app.instance_path, "eq_manage.db")
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"

    # ===== 統一 uploads 到 instance/uploads =====
    upload_root = os.path.join(app.instance_path, "uploads")
    os.makedirs(upload_root, exist_ok=True)
    app.config["UPLOAD_FOLDER"] = upload_root

    # init extensions
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "main.login"

    # import models so SQLAlchemy registers tables
    from .models import User, EquipmentType  # noqa

    # register blueprints
    from .routes import register_blueprints
    register_blueprints(app)

    # register error handlers
    from .errors import register_error_handlers
    register_error_handlers(app)

    # 禁止快取（方便開發）
    @app.after_request
    def add_header(response):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    # create tables + seed
    with app.app_context():
        db.create_all()

        # 初始化使用者
        initial_users = [
            {"username": "superuser", "role": "superuser", "password": "superpass"},
            {"username": "operator", "role": "operator", "password": "operatorpass"},
            {"username": "user", "role": "user", "password": "userpass"},
        ]

        for u in initial_users:
            if not User.query.filter_by(username=u["username"]).first():
                user = User(username=u["username"], role=u["role"])
                user.set_password(u["password"])
                db.session.add(user)

        # 初始化設備類型
        initial_types = [
            {"id": 1, "name": "Sidecar"},
            {"id": 2, "name": "In-Row CDU"},
            {"id": 3, "name": "ChillerDoor"},
        ]

        for t in initial_types:
            if not EquipmentType.query.filter_by(id=t["id"]).first():
                db.session.add(EquipmentType(id=t["id"], name=t["name"]))

        db.session.commit()

    return app
