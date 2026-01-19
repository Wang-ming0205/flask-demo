#app/models.py
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from ..extensions import db
from sqlalchemy import UniqueConstraint


# ==========================================
# 1. ä½¿ç”¨?…è¡¨ï¼šUser
# ==========================================
class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(45), nullable=False)

    # å¯†ç¢¼? å?
    def set_password(self, pwd):
        self.password_hash = generate_password_hash(pwd)

    def check_password(self, pwd):
        return check_password_hash(self.password_hash, pwd)

    # æ¬Šé??¹æ?
    def is_super(self): return self.role == "superuser"
    def is_operator(self): return self.role == "operator"
    def is_user(self): return self.role == "user"

    # ?Ÿèƒ½æ¬Šé?
    def can_manage_users(self): return self.is_super()
    def can_upload_logs(self): return True
    def can_upload_changes(self): return self.is_user() or self.is_super()


# ==========================================
# 2. æ¡ˆä??´æ™¯è¡¨ï?CaseScene
# ==========================================
class CaseScene(db.Model):
    __tablename__ = "case_scene"

    id = db.Column(db.Integer, primary_key=True)
    country = db.Column(db.String(20), nullable=False)  
    location = db.Column(db.String(30), nullable=False)

    # ä¸€?‹å ´?¯æ?å¤šå€‹æˆ¿??
    rooms = db.relationship("Room", backref="case_scene", lazy=True)


# ==========================================
# 3. ?¿é?è¡¨ï?Room
# ==========================================
class Room(db.Model):
    __tablename__ = "rooms"

    id = db.Column(db.Integer, primary_key=True)
    room_name = db.Column(db.String(40), nullable=False)

    # FK ?‡å??´æ™¯
    case_scene_id = db.Column(db.Integer, db.ForeignKey("case_scene.id"), nullable=False)

    # ?¿é? ??å¤šå€‹è¨­?™è?è¨?
    equipment_info = db.relationship("EquipmentInfo", backref="room", lazy=True)

    # ?¿é? ??å¤šå€‹è¨­?™è??´ç???
    equipment_manage = db.relationship("EquipmentManage", backref="room", lazy=True)

    __table_args__ = (
        UniqueConstraint("case_scene_id", "room_name", name="uq_room_case_roomname"),
    )    


# ==========================================
# 4. è¨­å??†é?ï¼šEquipmentType
# ==========================================
class EquipmentType(db.Model):
    __tablename__ = "equipment_type"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(40), nullable=False)

    # ä¸€?‹è¨­?™é??‹å¯å°æ?å¤šå°è¨­å?
    equipments = db.relationship("EquipmentInfo", 
                                backref="equipment_type", 
                                lazy=True)


# ==========================================
# 5. è¨­å?è³‡è?ï¼šEquipmentInfo
# ==========================================
class EquipmentInfo(db.Model):
    __tablename__ = "equipment_info"

    id = db.Column(db.Integer, primary_key=True)

    # SN ?¯ä?ï¼Œä???FK-m 
    vendor_sn = db.Column(db.String(50), unique=True, nullable=False)
    oem_sn = db.Column(db.String(50), unique=True, nullable=False)

    ats = db.Column(db.String(45), nullable=True)
    macaddr = db.Column(db.String(30), nullable=True)
    firmware = db.Column(db.String(35), nullable=False)
    
    # FK ?‡å??¿é?
    room_id = db.Column(db.Integer, db.ForeignKey("rooms.id"), nullable=True)

    # FK ?‡å?è¨­å?é¡å?
    equipment_type_id = db.Column(db.Integer, db.ForeignKey("equipment_type.id"), nullable=True)

    # è¨­å? ??å¤šå€‹ç®¡?†ç???
    manage_records = db.relationship("EquipmentManage", backref="equipment", lazy=True)


# ==========================================
# 6. è¨­å?è®Šæ›´æ­·å²ï¼šEquipmentManage
# ==========================================
class EquipmentManage(db.Model):
    __tablename__ = "equipment_manage"

    id = db.Column(db.Integer, primary_key=True)

    # FK ?‡å?è¨­å?è³‡è?
    equipment_info_id = db.Column(db.Integer, db.ForeignKey("equipment_info.id"), nullable=False)

    customer_changes = db.Column(db.Text, nullable=True)

    # FK ?‡å??¿é?ï¼ˆç??„ç•¶?‚ä?ç½®ï?
    room_id = db.Column(db.Integer, db.ForeignKey("rooms.id"), nullable=False)

