# app/service.py
from dataclasses import dataclass
from typing import Optional, Tuple, Dict, Any
import os, json ,sys,re
from datetime import datetime
from flask import current_app,abort
from werkzeug.utils import secure_filename
from ..extensions import db
from ..models import CaseScene, Room, EquipmentInfo, EquipmentManage 
from functools import wraps
from flask_login import current_user
from ..domain import CaseKey, EquipmentQuery
from sqlalchemy import or_


ALLOWED_EXTENSIONS = {"csv", "xlsx", "txt", "log"} 

def get_case_room_report_context(case_scene_id: int, room_id: int, category: str):
    data = build_case_room_report_ctx(case_scene_id, room_id, category)

    return {
        "case_id": data["cs"].id,
        "room_id": data["room"].id,
        "case_key": data["cs_key"],
        "room_name": data["room"].room_name,
        "equipments": data["equipments"],
        "uploaded_items": data["uploaded_items"],
        "room_files": data["room_files"],
        "report_filename": data["report_filename"],
        "report_ctx": data["report_ctx"],
        "category": data["category"],
    }

def get_case_context(case_scene_id: int) -> Dict[str, Any]:
    """
    Case Â±§Á? contextÔºöCase + rooms + case_key
    ËÆ?routes ‰∏çË??™Â∑± query CaseScene/Room
    """
    cs = CaseScene.query.get_or_404(case_scene_id)
    rooms = (
        Room.query
        .filter(Room.case_scene_id == cs.id)
        .order_by(Room.id.asc())
        .all()
    )

    return dict(
        cs=cs,
        rooms=rooms,
        case_key=CaseKey.from_casescene(cs).display,
    )


def build_room_equipments_ctx(case_scene_id: int, room_id: int, query: EquipmentQuery) -> Dict[str, Any]:
    """
    Room equipments Ê∏ÖÂñÆ?ÄË¶ÅÁ??Ä?âË??ôÔ???uploaded_items / selected_filesÔº?
    """
    cs = CaseScene.query.get_or_404(case_scene_id)
    room = Room.query.filter_by(id=room_id, case_scene_id=case_scene_id).first_or_404()

    eq_q = EquipmentInfo.query.filter_by(room_id=room.id)

    if query.has_text():
        like = query.like()
        eq_q = eq_q.filter(or_(
            EquipmentInfo.vendor_sn.ilike(like),
            EquipmentInfo.oem_sn.ilike(like),
        ))

    if query.type_id:
        eq_q = eq_q.filter(EquipmentInfo.equipment_type_id == query.type_id)

    equipments = eq_q.order_by(EquipmentInfo.oem_sn.asc()).all()

    uploaded_items = load_uploaded_items() or {}
    cs_key = CaseKey.from_casescene(cs).display
    selected_files = (uploaded_items.get(cs_key, {}).get(room.room_name, []) or [])

    return dict(
        cs=cs,
        room=room,
        cs_key=cs_key,
        equipments=equipments,
        uploaded_items=uploaded_items,
        selected_files=selected_files,
    )

def build_tree_items(use_json_fallback: bool = True):
    """
    Áµ?sidebar tree ?ÑË??ô„Ä?
    ‰∏ª‰?Ê∫êÔ?DB ??CaseScene + Room
    ?∏È?ÔºöÁî® uploaded_items.json Ë£?DB Ê≤íÊ???roomÔºà‰??æÂú®?âÈÄôÊÆµ?ÄÊ±ÇÊ??ãÔ?
    """
    uploaded_items = {}
    if use_json_fallback:
        try:
            uploaded_items = load_uploaded_items() or {}
        except Exception:
            uploaded_items = {}

    # 1) DB ‰∏ª‰?Ê∫êÔ?CaseScene + Room
    cs_rows = CaseScene.query.order_by(CaseScene.id.asc()).all()
    room_rows = Room.query.order_by(Room.id.asc()).all()

    rooms_by_cs = {}
    for r in room_rows:
        rooms_by_cs.setdefault(r.case_scene_id, []).append(r)

    tree = []
    for cs in cs_rows:
        cs_key = f"{cs.country}({cs.location})"

        # DB rooms
        room_list = []
        for r in rooms_by_cs.get(cs.id, []):
            room_list.append({"id": r.id, "name": r.room_name, "equipments": []})

        # 2) JSON fallbackÔºàÂèØ?úÈ?Ôº?
        if use_json_fallback:
            json_rooms = (uploaded_items.get(cs_key, {}) or {}).keys()
            existing_names = {x["name"] for x in room_list}
            for rn in json_rooms:
                if rn not in existing_names:
                    room_list.append({"id": 0, "name": rn, "equipments": []})

        tree.append({"id": cs.id, "name": cs_key, "rooms": room_list})

    return tree

def roles_required(*roles):
    """roles_required('superuser', 'operator')"""
    def deco(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            if current_user.role not in roles:
                abort(403)
            return fn(*args, **kwargs)
        return wrapper
    return deco

def init_upload_folders() -> None:
    """
    ?ùÂ??ñ‰??≥Ë??ôÂ§æÔºàÈÅø?çÁ¨¨‰∏ÄÊ¨°‰??≥Ê???mkdir ?†Ê?Ë∑ØÂ??èÈ?Ôº?
    ‰æù‰?Á≥ªÁµ±?ÑÂ?È°ûÂª∫Á´ãÔ?Inspection / Logs / Other / Feedback
    """
    upload_root = current_app.config.get("UPLOAD_FOLDER")
    if not upload_root:
        # ËÆìÈåØË™§Êó©‰∏ÄÈªûÁ?ÔºåÊñπ‰æøÊ??•Ë®≠ÂÆöÂ?È°?
        raise RuntimeError("UPLOAD_FOLDER is not configured in app.config")

    folders = ["Inspection", "Logs", "Other", "Feedback"]
    for name in folders:
        os.makedirs(os.path.join(upload_root, name), exist_ok=True)


def load_uploaded_items() -> dict:
    path = os.path.join(current_app.instance_path, "uploaded_items.json")
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, dict) else {}
        except Exception:
            return {}
    return {}


def save_uploaded_items(data: dict) -> None:
    os.makedirs(current_app.instance_path, exist_ok=True)
    path = os.path.join(current_app.instance_path, "uploaded_items.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def append_uploaded_item(country: str, room: Optional[str], filename: str) -> dict:
    """JSON storeÔºöÊõ¥??uploaded_items ‰∏¶ÂØ´Ê™îÔ??ûÂÇ≥?¥Êñ∞Âæ?dict"""
    items = load_uploaded_items()
    items.setdefault(country, {})
    if room:
        items[country].setdefault(room, [])
        if filename not in items[country][room]:
            items[country][room].append(filename)
    save_uploaded_items(items)
    return items


def validate_ext(filename: str) -> str:
    if "." not in filename:
        raise ValueError("Ê™îÂ?Ê≤íÊ??ØÊ???)
    ext = filename.rsplit(".", 1)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError("?™ËÉΩ‰∏äÂÇ≥ CSV / XLSX / TXT / LOG")
    return ext


def save_feedback_text(country: str, room: str, feedback_text: str) -> str:
    upload_root = current_app.config["UPLOAD_FOLDER"]
    feedback_dir = os.path.join(upload_root, "Feedback")
    os.makedirs(feedback_dir, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    stored_filename = f"feedback_{country}_{room}_{ts}.txt".replace(" ", "_")
    file_path = os.path.join(feedback_dir, stored_filename)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(feedback_text)

    return stored_filename

def parse_equipment_file(file_path: str, max_lines: int = 200) -> dict:
    """
    ?¨Áî®Ëß??:
    1) ?ØÊè¥ 'A,B' ?óË??ºÂ?
    2) ?ØÊè¥ 'A: B' ?íË??ºÂ?
    3) ?ØÊè¥ 'A B' Á©∫ÁôΩ?ÜÈ??ºÂ?
    4) Key Â§ßÂ?ÂØ´ÁÑ°?ú„ÄÅÁ©∫?ΩÁÑ°??
    5) ?™Ë???max_lines Ë°åÔ??øÂ?Ë∂ÖÂ§ßÊ™îÊ??°Ê≠ª
    """

    FIELD_MAP = {
        "inspection details": "inspection_details",
        "last inspect": "last_inspect",
        "serial number": "serial_number",
        "Vendor SN": "vendor_sn",
        "model": "model",
        "part number": "part_number",
        "eth1": "eth1",
        "eth2": "eth2",
        "eth3": "eth3",
        "system software": "system_software",
        "control firmware": "control_firmware",
    }

    # init dict
    info = {v: "" for v in FIELD_MAP.values()}

    if not os.path.exists(file_path):
        # ?ôË£°‰∏?raiseÔºåË?‰∏äÂ±§Ê±∫Â?Ë¶Å‰?Ë¶?FileNotFoundError
        return info

    line_count = 0
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        for raw in f:
            line_count += 1
            if line_count > max_lines:
                break

            line = raw.strip()
            if not line:
                continue

            key = None
            val = None

            # 1) ?óË?
            if "," in line:
                parts = line.split(",", 1)
                key = parts[0].strip().lower()
                val = parts[1].strip()

            else:
                # 2) ?íË?
                if ":" in line:
                    parts = line.split(":", 1)
                    key = parts[0].strip().lower()
                    val = parts[1].strip().strip("'\" ")

                else:
                    # 3) Á©∫ÁôΩ
                    parts = line.split(None, 1)
                    if len(parts) == 2:
                        key = parts[0].strip().lower()
                        val = parts[1].strip().strip("'\" ")
                    else:
                        continue

            if not key:
                continue

            # match field
            for pattern, field_name in FIELD_MAP.items():
                if pattern in key:
                    info[field_name] = val
                    break

    # ‰Ω†Â??¨Á??????firmware
    info["firmware"] = f"{info.get('system_software','')},{info.get('control_firmware','')}".strip(",")

    print(f"?? parse_equipment_file info = {info}", file=sys.stderr)
    return info


def build_inspection_report_context(filename: str) -> Dict[str, Any]:
    """?™Â???contextÔºà‰???redirect / ‰∏çÊãº HTMLÔº?""
    base_dir = current_app.config["UPLOAD_FOLDER"]
    inspection_dir = os.path.join(base_dir, "Inspection")
    logs_dir = os.path.join(base_dir, "Logs")

    inspection_path = os.path.join(inspection_dir, filename)
    log_path = os.path.join(logs_dir, filename)

    if os.path.exists(inspection_path):
        file_path = inspection_path
        category = "Inspection"
    elif os.path.exists(log_path):
        file_path = log_path
        category = "Logs"
    else:
        raise FileNotFoundError(filename)

    info = parse_equipment_file(file_path)

    serial_number = info.get("serial_number") or ""
    vendor_sn = info.get("vendor_sn") or ""

    eq = None
    if serial_number:
        eq = EquipmentInfo.query.filter_by(oem_sn=serial_number).first()
    if not eq and vendor_sn:
        eq = EquipmentInfo.query.filter_by(vendor_sn=vendor_sn).first()

    fields = [
        ("Serial Number", "serial_number"),
        ("Vendor SN", "vendor_sn"),
        ("Model", "model"),
        ("Part Number", "part_number"),
        ("Last Inspect", "last_inspect"),
        ("Eth1", "eth1"),
        ("Eth2", "eth2"),
        ("Eth3", "eth3"),
        ("System Software", "system_software"),
        ("Control Firmware", "control_firmware"),
    ]

    return {
        "filename": filename,
        "category": category,   # route ?ãÂà∞ Logs Â∞?redirect
        "info": info,
        "fields": fields,
        "eq": eq,               # template ??eq.id ??feedback_url
    }

def touch_location(country: str, room: Optional[str]) -> dict:
    items = load_uploaded_items()
    items.setdefault(country, {})
    if room:
        items[country].setdefault(room, [])
    save_uploaded_items(items)
    return items

def upload_and_register_auto(
    file_storage,
    country_raw: str,
    room_raw: str,
    customer_changes: str = "",
    equipment_type_id: int | None = None,
    file_category: str | None = None,
    equipment_id: int | None = None,   # ??logs ?®‰?Á∂ÅË®≠??
):
    if not file_storage or not file_storage.filename:
        raise ValueError("Ê≤íÊ?Ê™îÊ?")

    stored_path = None
    manage_record=None
    c,loc = parse_case_scene(country_raw)
    #cs_key = f'{c}({loc})'

    try:
        # ??Á¢∫‰? location/room Â≠òÂú®
        cs, r = ensure_case_room(c,loc , room_raw)
        if not r:
            raise ValueError("room ÂøÖÂ°´ÔºàEquipmentManage.room_id nullable=FalseÔº?)

        filename = secure_filename(file_storage.filename)
        validate_ext(filename)

        # ??Áµ±‰??ÜÈ?ÔºöÁî®‰Ω†ÂØ´??classify_upload
        category = classify_upload(filename, file_category)

        upload_root = current_app.config["UPLOAD_FOLDER"]
        category_dir = os.path.join(upload_root, category.capitalize() if category != "logs" else "Logs")
        os.makedirs(category_dir, exist_ok=True)

        stored_path = os.path.join(category_dir, filename)
        if os.path.exists(stored_path):
            base, ext = os.path.splitext(filename)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{base}_{ts}{ext}"
            stored_path = os.path.join(category_dir, filename)

        # Â≠òÊ?
        file_storage.seek(0)
        with open(stored_path, "wb") as f:
            f.write(file_storage.read())

        equipment = None

        # ??inspectionÔºöËß£?ê‰∏¶ upsert
        if category == "inspection":
            info = parse_equipment_file(stored_path)

            oem_sn = (info.get("serial_number") or "").strip()
            vendor_sn = (info.get("vendor_sn") or "").strip()
            firmware = (info.get("firmware") or "").strip()

            if not oem_sn:
                raise ValueError("Ê™îÊ?Áº∫Â? Serial Number (oem_sn)")
            if not vendor_sn:
                raise ValueError("Ê™îÊ?Áº∫Â? Vendor SN (vendor_sn)")
            if not firmware:
                raise ValueError("Ê™îÊ?Áº∫Â? firmware (system_software/control_firmware)")

            equipment = EquipmentInfo.query.filter_by(oem_sn=oem_sn).first() \
                        or EquipmentInfo.query.filter_by(vendor_sn=vendor_sn).first()

            if not equipment:
                equipment = EquipmentInfo(
                    oem_sn=oem_sn,
                    vendor_sn=vendor_sn,
                    firmware=firmware,
                    room_id=r.id,
                    equipment_type_id=equipment_type_id,
                )
                db.session.add(equipment)
                db.session.flush()
            else:
                equipment.firmware = firmware
                equipment.room_id = r.id
                if equipment_type_id is not None:
                    equipment.equipment_type_id = equipment_type_id
                db.session.flush()

        # ??logsÔºöÁ?Ê≠¢Êñ∞Âª∫Ë®≠?ôÔ?ÂøÖÈ?Á∂ÅÊó¢??inspection ??equipment
        elif category == "logs":
            if not equipment_id:
                raise ValueError("Logs ÂøÖÈ??áÂ? equipment_idÔºàË??à‰???inspection ‰∏¶ÈÅ∏ÂÆöË®≠?ôÔ?")

            equipment = EquipmentInfo.query.get(equipment_id)
            if not equipment:
                raise ValueError("?æ‰??∞Â??âË®≠?ôÔ?Ë´ãÂ?‰∏äÂÇ≥ inspection")

        # ??otherÔºö‰??Ø‰ª•?àÁï∂‰Ωú‰?ÂØ?DBÔºàÊ?Ë¶èÂ?ÂøÖÈ? equipment_idÔº?
        else:
            # ?à‰??ïÔ??øÂ?‰Ω†È?Ê±ÇÊì¥??
            pass

        # ??logs / inspection ?ΩÂèØÂØ´‰?Á≠?manage recordÔºàÂèØ?∏Ô?
        if equipment:
            manage_record = EquipmentManage(
                equipment_info_id=equipment.id,
                room_id=r.id,
                customer_changes=customer_changes or None,
            )
            db.session.add(manage_record)

#        db.session.commit()
        db.session.flush()
        current_app.logger.warning(
           "[upload_and_register_auto] cs_id=%s room_id=%s category=%s file=%s equipment_id=%s",
            getattr(cs, "id", None),
            getattr(r, "id", None),
            category,
            filename,
            getattr(equipment, "id", None),
        )
        return stored_path, equipment, manage_record 
    
    except Exception:
#        db.session.rollback()
        if stored_path and os.path.exists(stored_path):
            try:
                os.remove(stored_path)
            except Exception:
                pass
        raise

def save_feedback_with_photos(equipment, text: str, before_file, after_file, user_id: int):
    upload_root = current_app.config["UPLOAD_FOLDER"]
    photo_dir = os.path.join(upload_root, "FeedbackPhotos")
    os.makedirs(photo_dir, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    saved_paths = []  # ??Ë®òÈ??ôÊ¨°ÂØ´Âá∫?ªÁ?Ê™îÊ?ÔºåÂ§±?óÂ∞±?™Ê?

    def _save_one(file_obj, tag: str):
        if not file_obj or not getattr(file_obj, "filename", ""):
            return None

        fname = secure_filename(file_obj.filename)
        stored = f"{equipment.id}_{tag}_{ts}_{fname}"
        path = os.path.join(photo_dir, stored)

        file_obj.seek(0)
        with open(path, "wb") as f:
            f.write(file_obj.read())

        saved_paths.append(path)  # ???†ÂÖ• cleanup ?çÂñÆ
        return stored

    try:
        before_name = _save_one(before_file, "before")
        after_name  = _save_one(after_file, "after")

        extra = []
        if before_name: extra.append(f"before_photo={before_name}")
        if after_name:  extra.append(f"after_photo={after_name}")
        suffix = ("\n" + "\n".join(extra)) if extra else ""

        rec = EquipmentManage(
            equipment_info_id=equipment.id,
            room_id=equipment.room_id,
            customer_changes=(text or "") + suffix
        )

        db.session.add(rec)
        db.session.flush()
        return rec

    except Exception:
        db.session.rollback()

        # ??cleanupÔºöÊ??õÂØ´?∫Âéª?ÑÁÖß?áÂà™?âÔ??øÂ?Â≠§Â?Ê™?
        for p in saved_paths:
            try:
                if os.path.exists(p):
                    os.remove(p)
            except Exception:
                pass

        raise


def parse_case_scene(raw: str):
    """
    ?ØÊè¥Ôº?
      1) USA(Quincy) -> ("USA", "Quincy")
      2) USA / Quincy -> ("USA", "Quincy")  (?ØÈÅ∏)
    """
    raw = (raw or "").strip()
    if not raw:
        raise ValueError("country/case_scene ‰∏çÂèØ?∫Á©∫")

    m = re.match(r"^(?P<country>[^()]+)\((?P<location>[^()]+)\)$", raw)
    if m:
        country = re.sub(r"\s+", " ", m.group("country")).strip()
        location = re.sub(r"\s+", " ", m.group("location")).strip()
        return country,location

    raw = re.sub(r'\s+',' ',raw).strip()
    # Ê≤íÊã¨?üÔ?Â∞±Â??®ÈÉ®??countryÔºålocation ?®Â??ºÈ??óÔ??≥Â?‰∏çÁÇ∏Ôº?
    return raw, raw

def ensure_case_room(
        country_or_country: str, 
        location_or_room: str | None = None, 
        room_raw: str | None = None):
     # --- ?§Êñ∑?ØÂì™Á®ÆÂëº??---
    if room_raw is None:
        # ?©Â??∏Ô?country_or_country = "USA(quincy)", location_or_room = room
        country_raw = country_or_country
        room_name = location_or_room
        country, location = parse_case_scene(country_raw)
    else:
        # ‰∏âÂ??∏Ô?country_or_country = "USA", location_or_room = "quincy", room_raw = room
        country = country_or_country
        location = location_or_room or ""
        room_name = room_raw

    # --- Ê∏ÖÊ? ---
    country  = re.sub(r"\s+", " ", (country or "")).strip()
    location = re.sub(r"\s+", " ", (location or "")).strip()
    room_name = re.sub(r"\s+", " ", (room_name or "")).strip() or None

    # 1) CaseScene upsert
    cs = CaseScene.query.filter_by(country=country, location=location).first()
    if not cs:
        cs = CaseScene(country=country, location=location)
        db.session.add(cs)
        db.session.flush()

    # 2) Room upsert
    r = None
    if room_name:
        r = Room.query.filter_by(case_scene_id=cs.id, room_name=room_name).first()
        if not r:
            r = Room(case_scene_id=cs.id, room_name=room_name)
            db.session.add(r)
            db.session.flush()

    return cs, r

def ensure_case_room_committed(cs_name: str, room_name: str):
    """
    Á¢∫‰? CaseScene/Room Â≠òÂú®Ôºå‰∏¶ÂÆåÊ? commit??
    ?ûÂÇ≥ (cs, r)
    """
    print(">>> ensure_case_room_committed CALLED", cs_name, room_name)
    cs, r = ensure_case_room(cs_name, room_name)
#    db.session.commit()
    return cs, r

def resolve_case_context(cs_name: str) -> Dict[str, Any]:
    """
    ?ûÂÇ≥?åÊ??¥Ê?‰Ωú‰?‰∏ãÊ?ÔºàCase-levelÔºâ„ÄçÔ?
    - Case Â≠ò‰?Â≠òÂú®
    - ?âÂì™‰∫?rooms
    - ?ØÂê¶?ÅË®±?≤ÂÖ• upload ?´Èù¢
    - ?ØÂê¶??submit ?ÇÂ??àÊ?ÂÆ?room
    ??‰∏?commit
    ??‰∏?redirect
    """

    country, location = parse_case_scene(cs_name)

    cs: Optional[CaseScene] = CaseScene.query.filter_by(
        country=country,
        location=location
    ).first()

    # Case ‰∏çÂ?????‰ªçÁÑ∂?ÅË®±??uploadÔºàÁî± submit ?ÇÂª∫Á´ãÔ?
    if not cs:
        return {
            "case": None,
            "case_key": cs_name,
            "rooms": [],
            "has_rooms": False,

            # Ë°åÁÇ∫Ë™ûÊ?
            "can_enter_upload": True,
            "require_room_on_submit": True,
        }

    # Case Â≠òÂú®
    rooms = (
        Room.query
        .filter_by(case_scene_id=cs.id)
        .order_by(Room.room_name.asc())
        .all()
    )

    return {
        "case": cs,
        "case_key": cs_name,
        "rooms": rooms,
        "has_rooms": len(rooms) > 0,

        # Ë°åÁÇ∫Ë™ûÊ?
        "can_enter_upload": True,          # ??Case Â±§Ê∞∏?†ÂèØ??upload
        "require_room_on_submit": True,    # ???üÊ≠£?ÅÂá∫‰∏ÄÂÆöË? room
    }

def classify_upload(filename: str, file_category: str | None = None) -> str:
    # file_category ‰æÜËá™?çÁ´Ø labelÔºà‰?Â∑≤Ê? file_categoryÔº?
    if file_category:
        fc = file_category.strip().lower()
        if fc in {"inspection", "logs", "feedback", "other"}:
            return fc

    lower = (filename or "").lower()
    if "inspection" in lower:
        return "inspection"
    if lower.endswith(".log") or "log" in lower:
        return "logs"
    return "other"


def create_location(raw_country: str, raw_room: str | None):
    """
    Âª∫Á?/?¥Êñ∞Ê°àÂ†¥??roomÔºå‰∏¶?åÊ≠• JSON tree
    ?ûÂÇ≥Áµ?API ?®Á? dict
    """
    c, loc = parse_case_scene(raw_country)
    country_key = f"{c}({loc})"

    try:
        cs, r = ensure_case_room(country_key, raw_room)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    # DB ?êÂ?ÂæåÂ??Ø‰??®Ô?treeÔº?
    items = touch_location(country_key, raw_room)
    current_app.uploaded_items = items

    return dict(
        country=country_key,
        room=raw_room,
        country_id=cs.id,
        room_id=(r.id if r else None),
    )


def create_upload(req):
    """
    ‰∏äÂÇ≥/?ûÈ?ÂØ´ÂÖ•?Ñ‰∏ªÊµÅÁ?
    ?ûÂÇ≥ dict: {filename: "..."}
    """
    file_category = (req.form.get("file_category") or "inspection").lower()
    file = req.files.get("file")
    feedback_text = (req.form.get("feedback_text") or "").strip()

    country = (req.form.get("country") or "").strip()
    room = (req.form.get("room") or "").strip()

    if not country:
        raise ValueError("country ÂøÖÂ°´")

    if not room and file_category in ("inspection", "logs", "feedback", "other"):
        raise ValueError("Ë´ãÂ??∏Ê?/Ëº∏ÂÖ• RoomÔºà‰??ØÁÇ∫Á©∫Ô?")

    c, loc = parse_case_scene(country)
    country_key = f"{c}({loc})"

    if file_category == "logs" and not req.form.get("equipment_id"):
        raise ValueError("Logs ÂøÖÈ??∏Ê?Ë®≠Â?")

    try:
        if file_category == "feedback":
            if not feedback_text:
                raise ValueError("Feedback ?ßÂÆπ‰∏çÂèØ?∫Á©∫")

            stored_filename = save_feedback_text(country_key, room, feedback_text)
            db.session.commit()

        else:
            if not file or file.filename == "":
                raise ValueError("Ê≤íÊ??∏Ê?Ê™îÊ?")

            validate_ext(file.filename)

            stored_path, equipment, manage_record = upload_and_register_auto(
                file_storage=file,
                country_raw=country_key,
                room_raw=room,
                customer_changes=feedback_text,
                equipment_type_id=req.form.get("equipment_type_id", type=int),
                file_category=file_category,
                equipment_id=req.form.get("equipment_id", type=int),
            )
            db.session.commit()
            stored_filename = os.path.basename(stored_path)

    except Exception:
        db.session.rollback()
        raise

    # DB/Ê™îÊ??êÂ?ÂæåÊõ¥??tree
    items = append_uploaded_item(country_key, room, stored_filename)
    current_app.uploaded_items = items

    return dict(filename=stored_filename)

def pick_latest_inspection(room_files: list[str], inspection_dir: str) -> str | None:
    cand = []
    for fname in room_files or []:
        lower = fname.lower()
        if "inspection" in lower or lower.endswith(".csv") or lower.endswith(".txt"):
            cand.append(fname)

    latest = None
    latest_mtime = -1

    for fname in cand:
        fpath = os.path.join(inspection_dir, fname)
        if os.path.exists(fpath):
            mt = os.path.getmtime(fpath)
            if mt > latest_mtime:
                latest_mtime = mt
                latest = fname
    return latest

def build_case_room_report_ctx(case_scene_id: int, room_id: int, category: str):
    cs = CaseScene.query.get_or_404(case_scene_id)
    room = Room.query.filter_by(id=room_id, case_scene_id=case_scene_id).first_or_404()
    cs_key = f"{cs.country}({cs.location})"

    uploaded_items = load_uploaded_items() or {}
    room_files = (uploaded_items.get(cs_key, {}).get(room.room_name, []) or [])

    base_dir = current_app.config.get("UPLOAD_FOLDER")
    inspection_dir = os.path.join(base_dir, "Inspection") if base_dir else ""

    latest = pick_latest_inspection(room_files, inspection_dir) if inspection_dir else None

    report_ctx = {}
    report_filename = latest or ""
    if latest:
        report_ctx = build_inspection_report_context(latest)

    equipments = EquipmentInfo.query.filter_by(room_id=room.id).order_by(
        EquipmentInfo.oem_sn.asc()
    ).all()

    return dict(
        cs=cs,
        room=room,
        cs_key=cs_key,
        uploaded_items=uploaded_items,
        room_files=room_files,
        report_filename=report_filename,
        report_ctx=report_ctx,
        equipments=equipments,
        category=category,
    )
