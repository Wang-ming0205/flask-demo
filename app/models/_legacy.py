#app/models.py
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from ..extensions import db
from sqlalchemy import UniqueConstraint


# ==========================================
# 1. 使用者表：User
# ==========================================
class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(45), nullable=False)

    # 密碼加密
    def set_password(self, pwd):
        self.password_hash = generate_password_hash(pwd)

    def check_password(self, pwd):
        return check_password_hash(self.password_hash, pwd)

    # 權限方法
    def is_super(self): return self.role == "superuser"
    def is_operator(self): return self.role == "operator"
    def is_user(self): return self.role == "user"

    # 功能權限
    def can_manage_users(self): return self.is_super()
    def can_upload_logs(self): return True
    def can_upload_changes(self): return self.is_user() or self.is_super()


# ==========================================
# 2. 案例場景表：CaseScene
# ==========================================
class CaseScene(db.Model):
    __tablename__ = "case_scene"

    id = db.Column(db.Integer, primary_key=True)
    country = db.Column(db.String(20), nullable=False)  
    location = db.Column(db.String(30), nullable=False)

    # 一個場景有多個房間
    rooms = db.relationship("Room", backref="case_scene", lazy=True)


# ==========================================
# 3. 房間表：Room
# ==========================================
class Room(db.Model):
    __tablename__ = "rooms"

    id = db.Column(db.Integer, primary_key=True)
    room_name = db.Column(db.String(40), nullable=False)

    # FK 指向場景
    case_scene_id = db.Column(db.Integer, db.ForeignKey("case_scene.id"), nullable=False)

    # 房間 → 多個設備資訊
    equipment_info = db.relationship("EquipmentInfo", backref="room", lazy=True)

    # 房間 → 多個設備變更紀錄
    equipment_manage = db.relationship("EquipmentManage", backref="room", lazy=True)

    __table_args__ = (
        UniqueConstraint("case_scene_id", "room_name", name="uq_room_case_roomname"),
    )    


# ==========================================
# 4. 設備分類：EquipmentType
# ==========================================
class EquipmentType(db.Model):
    __tablename__ = "equipment_type"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(40), nullable=False)

    # 一個設備類型可對應多台設備
    equipments = db.relationship("EquipmentInfo", 
                                backref="equipment_type", 
                                lazy=True)


# ==========================================
# 5. 設備資訊：EquipmentInfo
# ==========================================
class EquipmentInfo(db.Model):
    __tablename__ = "equipment_info"

    id = db.Column(db.Integer, primary_key=True)

    # SN 唯一，不當 FK-m 
    kaori_sn = db.Column(db.String(50), unique=True, nullable=False)
    supermicro_sn = db.Column(db.String(50), unique=True, nullable=False)

    ats = db.Column(db.String(45), nullable=True)
    macaddr = db.Column(db.String(30), nullable=True)
    firmware = db.Column(db.String(35), nullable=False)
    
    # FK 指向房間
    room_id = db.Column(db.Integer, db.ForeignKey("rooms.id"), nullable=True)

    # FK 指向設備類型
    equipment_type_id = db.Column(db.Integer, db.ForeignKey("equipment_type.id"), nullable=True)

    # 設備 → 多個管理紀錄
    manage_records = db.relationship("EquipmentManage", backref="equipment", lazy=True)


# ==========================================
# 6. 設備變更歷史：EquipmentManage
# ==========================================
class EquipmentManage(db.Model):
    __tablename__ = "equipment_manage"

    id = db.Column(db.Integer, primary_key=True)

    # FK 指向設備資訊
    equipment_info_id = db.Column(db.Integer, db.ForeignKey("equipment_info.id"), nullable=False)

    customer_changes = db.Column(db.Text, nullable=True)

    # FK 指向房間（紀錄當時位置）
    room_id = db.Column(db.Integer, db.ForeignKey("rooms.id"), nullable=False)

