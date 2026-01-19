# app/routes/_legacy.py
from flask import (
    Blueprint, render_template, redirect, url_for,Flask,
    request, flash, current_app, jsonify, send_from_directory, abort
)
from flask_login import login_user, logout_user, login_required, current_user,LoginManager
from sqlalchemy import or_
from werkzeug.utils import secure_filename
from werkzeug.exceptions import HTTPException
from ..http import api_ok, api_error
import os
from ..domain import CaseKey, EquipmentQuery
from ..extensions import db, login_manager
from ..models import User, CaseScene, Room, EquipmentInfo, EquipmentManage, EquipmentType
from ..services import (
    save_feedback_with_photos,
    load_uploaded_items,
    roles_required,
    build_tree_items,
    create_location,
    create_upload,
    build_case_room_report_ctx,
    build_inspection_report_context,
    build_room_equipments_ctx,
    get_case_context
)

main = Blueprint("main", __name__)
api = Blueprint("api", __name__)

# ------------------------------------------
# Small constants: avoid typo in active_tab
# ------------------------------------------
TAB_LIST = "list"
TAB_UPLOAD = "upload"
TAB_SEARCH = "search"
TAB_CASE = "case"
TAB_REPORT = "report"

CAT_INSPECTION = "inspection"
CAT_LOGS = "logs"

# ==========================================
# API: always JSON for auth/error
# ==========================================
@login_manager.unauthorized_handler
def _unauthorized():
    # 只要是 API blueprint 進來，回 JSON 401
    if request.blueprint == "api":
        return api_error(401, "UNAUTHORIZED", "login required")
    # UI 照舊導到 login
    return redirect(url_for("main.login"))

@api.app_errorhandler(HTTPException)
def _api_http_exception(e: HTTPException):
    return api_error(e.code or 500, e.name.upper().replace(" ", "_"), e.description)

@api.app_errorhandler(Exception)
def _api_exception(e: Exception):
    current_app.logger.exception("API crashed")
    return api_error(500, "INTERNAL_SERVER_ERROR", "unexpected server error")



# ==========================================
# Login
# ==========================================
@login_manager.user_loader
def load_user(user_id):
    # SQLAlchemy 2.0 style; if you use older SA, you can keep User.query.get(...)
    try:
        return db.session.get(User, int(user_id))
    except Exception:
        return User.query.get(int(user_id))


@main.route("/")
def index():
    if not current_user.is_authenticated:
        return redirect(url_for("main.login"))
    return redirect(url_for("main.dashboard"))


@main.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            flash("登入成功", "success")
            return redirect(url_for("main.index"))
        flash("帳號或密碼錯誤", "danger")
    return render_template("login.html")


@main.route("/logout")
@login_required
def logout():
    logout_user()
    flash("已登出", "info")
    return redirect(url_for("main.login"))


# ==========================================
# Role pages
# ==========================================
@main.route("/super")
@login_required
@roles_required("superuser")
def super_area():
    return render_template("super_area.html")


@main.route("/operator")
@login_required
@roles_required("superuser", "operator")
def operator_area():
    return render_template("operator_area.html")


# ==========================================
# Admin Users
# ==========================================
@main.route("/admin/users", methods=["GET", "POST"])
@login_required
@roles_required("superuser", "operator")
def manage_users():
    current_role = current_user.role

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        role = request.form.get("role", "user").strip()

        if not username or not password:
            flash("帳號與密碼必填", "danger")
            return redirect(url_for("main.manage_users"))

        if User.query.filter_by(username=username).first():
            flash("帳號已存在", "danger")
            return redirect(url_for("main.manage_users"))

        if current_role != "superuser":
            role = "user"

        u = User(username=username, role=role)
        u.set_password(password)
        db.session.add(u)
        db.session.commit()

        flash("新增使用者成功", "success")
        return redirect(url_for("main.manage_users"))

    users = User.query.order_by(User.id.asc()).all()
    return render_template("user_manage.html", users=users, current_role=current_role)


@main.route("/admin/users/<int:user_id>/edit", methods=["GET", "POST"])
@login_required
@roles_required("superuser", "operator")
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    current_role = current_user.role

    if current_role == "operator" and user.id != current_user.id:
        abort(403)

    if request.method == "POST":
        if current_role == "superuser":
            new_username = request.form.get("username", "").strip()
            new_role = request.form.get("role", "user").strip()

            if not new_username:
                flash("帳號不可為空", "danger")
                return redirect(url_for("main.edit_user", user_id=user.id))

            if new_username != user.username:
                if User.query.filter_by(username=new_username).first():
                    flash("帳號已存在", "danger")
                    return redirect(url_for("main.edit_user", user_id=user.id))
                user.username = new_username

            if new_role not in ("user", "operator", "superuser"):
                new_role = "user"
            user.role = new_role

        password = request.form.get("password", "")
        if password:
            user.set_password(password)

        db.session.commit()
        flash("已儲存變更", "success")
        return redirect(url_for("main.manage_users"))

    return render_template("user_edit.html", user=user, current_role=current_role)


@main.route("/admin/users/<int:user_id>/delete", methods=["POST"])
@login_required
@roles_required("superuser")
def delete_user(user_id):
    if current_user.id == user_id:
        flash("不能刪除自己", "warning")
        return redirect(url_for("main.manage_users"))

    user = User.query.get_or_404(user_id)

    if user.role == "superuser":
        cnt = User.query.filter_by(role="superuser").count()
        if cnt <= 1:
            flash("至少要保留一位 superuser", "warning")
            return redirect(url_for("main.manage_users"))

    db.session.delete(user)
    db.session.commit()
    flash(f"已刪除使用者：{user.username}", "success")
    return redirect(url_for("main.manage_users"))


# ==========================================
# Account
# ==========================================
@main.route("/account/edit", methods=["GET", "POST"])
@login_required
def account_edit():
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()

        if not username:
            flash("帳號不可為空", "danger")
            return redirect(url_for("main.account_edit"))

        exists = User.query.filter(
            User.username == username,
            User.id != current_user.id,
        ).first()
        if exists:
            flash("此帳號已被他人使用", "danger")
            return redirect(url_for("main.account_edit"))

        current_user.username = username
        db.session.commit()
        flash("帳號已更新", "success")
        return redirect(url_for("main.index"))

    return render_template("account_edit.html", user=current_user)


@main.route("/account/password", methods=["GET", "POST"])
@login_required
def change_password():
    if request.method == "POST":
        old_password = (request.form.get("old_password") or "").strip()
        new_password = (request.form.get("new_password") or "").strip()
        confirm = (request.form.get("confirm") or "").strip()

        if not old_password or not new_password:
            flash("請輸入舊密碼與新密碼", "danger")
            return redirect(url_for("main.change_password"))

        if new_password != confirm:
            flash("兩次輸入的新密碼不一致", "danger")
            return redirect(url_for("main.change_password"))

        if not current_user.check_password(old_password):
            flash("舊密碼錯誤", "danger")
            return redirect(url_for("main.change_password"))

        current_user.set_password(new_password)
        db.session.commit()
        flash("密碼已更新", "success")
        return redirect(request.referrer or url_for("main.account_edit"))

    return render_template("change_password.html")


# ==========================================
# Dashboard / All
# ==========================================
@main.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html", username=current_user.username, role=current_user.role)


@main.route("/all")
@login_required
def all_view():
    return redirect(url_for("main.dashboard"), code=302)


@main.route("/dashboard/partial")
@login_required
def dashboard_partial():
    return render_template("dashboard_partial.html")


# ==========================================
# Helpers (equipment)
# ==========================================
def equipment_base_ctx(tree_items=None, uploaded_items=None, equipment_types=None):
    # uploaded_items
    if uploaded_items is None:
        try:
            uploaded_items = load_uploaded_items() or {}
        except Exception:
            uploaded_items = {}

    # tree_items
    if tree_items is None:
        tree_items = build_tree_items(use_json_fallback=True)

    # equipment_types
    if equipment_types is None:
        equipment_types = EquipmentType.query.order_by(EquipmentType.id.asc()).all()

    return dict(
        tree_items=tree_items,
        uploaded_items=uploaded_items,
        equipment_types=equipment_types,

        selected_country_id=None,
        selected_room_id=None,
        selected_country=None,
        selected_room=None,
        selected_files=[],
        equipments=[],
        case_rooms=[],

        prefill_country="",
        prefill_room="",
        can_upload=True,

        report_filename=None,
        report_ctx=None,
    )


def _upload_dir(kind: str) -> str:
    # Centralize upload folder paths
    base_dir = current_app.config["UPLOAD_FOLDER"]
    if kind == "inspection":
        return os.path.join(base_dir, "Inspection")
    if kind == "logs":
        return os.path.join(base_dir, "Logs")
    raise ValueError("Unknown upload kind")


# ==========================================
# Equipment entry (tool page)
# ==========================================
@main.route("/equipment")
@login_required
def equipment_page():
    return redirect(url_for("main.equipment_list"))


@main.route("/equipment/list")
@login_required
def equipment_list():
    ctx = equipment_base_ctx()
    ctx["active_tab"] = TAB_LIST
    return render_template("equipment.html", **ctx)

@main.route("/equipment/upload")
@login_required
def equipment_upload():
    ctx = equipment_base_ctx()
    ctx["active_tab"] = TAB_UPLOAD
    return render_template("equipment.html", **ctx)


# ==========================================
# Logs / Reports / Download
# ==========================================
@main.route("/equipment/logs/<path:filename>")
@login_required
def logs_summary(filename):
    # Ensure filename is safe to open
    fname = secure_filename(filename)
    logs_dir = _upload_dir("logs")
    file_path = os.path.join(logs_dir, fname)

    if not os.path.exists(file_path):
        return render_template("file_missing.html", filename=filename), 404

    from ..services import summarize_log_file
    result = summarize_log_file(file_path)
    return render_template("logs_summary.html", filename=fname, result=result)


@main.route("/equipment/logs/view/<path:filename>")
@login_required
def view_logs_summary(filename):
    return redirect(url_for("main.logs_summary", filename=filename), code=302)


# ✅ ADD BACK: canonical report page (used by /equipment/report/view/<filename>)
@main.route("/equipment/reports/<path:filename>")
@login_required
def report_page(filename):
    try:
        report_ctx = build_inspection_report_context(filename)
        # If report_ctx says it's logs, send to logs page
        if (report_ctx.get("category") or "").strip().lower() == "logs":
            return redirect(url_for("main.logs_summary", filename=filename))

        ctx = equipment_base_ctx()
        ctx.update(active_tab=TAB_REPORT, report_filename=filename, report_ctx=report_ctx)
        return render_template("equipment.html", **ctx)

    except FileNotFoundError:
        return render_template("file_missing.html", filename=filename), 404


@main.route("/equipment/report/view/<path:filename>")
@login_required
def view_inspection_report(filename):
    return redirect(url_for("main.report_page", filename=filename), code=302)


@main.route("/equipment/report/raw/<path:filename>")
@login_required
def download_inspection_file(filename):
    # Secure and rely on send_from_directory's safe path handling
    inspection_dir = _upload_dir("inspection")
    fname = secure_filename(filename)
    return send_from_directory(inspection_dir, fname, as_attachment=True)


@main.route("/equipment/download/<path:filename>")
@login_required
def download_log_file(filename):
    logs_dir = _upload_dir("logs")
    fname = secure_filename(filename)
    return send_from_directory(logs_dir, fname, as_attachment=True)


# ==========================================
# Feedback page
# ==========================================
@main.route("/equipment/feedback/<int:eq_id>", methods=["GET", "POST"])
@login_required
def equipment_feedback(eq_id):
    eq = EquipmentInfo.query.get_or_404(eq_id)

    if request.method == "POST":
        text = (request.form.get("feedback") or "").strip()
        before_file = request.files.get("before_photo")
        after_file = request.files.get("after_photo")

        if not text and not (before_file and before_file.filename) and not (after_file and after_file.filename):
            flash("請至少輸入描述或上傳一張照片", "danger")
            return redirect(request.referrer or url_for("main.equipment_feedback", eq_id=eq_id))

        try:
            save_feedback_with_photos(
                equipment=eq,
                text=text,
                before_file=before_file,
                after_file=after_file,
                user_id=current_user.id,
            )
            db.session.commit()
            flash("feedback 已寫入", "success")
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception("feedback 建立失敗")
            flash(f"feedback 建立失敗：{e}", "danger")

        return redirect(request.referrer or url_for("main.equipment_feedback", eq_id=eq_id))

    return render_template("feedback_form.html", equipment=eq)


@main.route("/equipment/manage/<int:eq_id>/feedback", methods=["GET", "POST"])
@login_required
def add_equipment_feedback(eq_id):
    return equipment_feedback(eq_id)


# ==========================================
# Canonical: equipment -> case-scenes -> rooms -> equipments
# ==========================================
@main.route("/equipment/case-scenes/<int:case_scene_id>")
@login_required
def equipment_case_scene_root(case_scene_id):
    ctx_case = get_case_context(case_scene_id)
    ctx=equipment_base_ctx()
    ctx.update(
        active_tab=TAB_CASE,
        category=CAT_INSPECTION,
        selected_country_id=ctx_case["cs"].id,
        selected_country=ctx_case["case_key"],
        prefill_country=ctx_case["case_key"],
        prefill_room="",
        case_rooms=ctx_case["rooms"],
        can_upload=True,
    )
    return render_template("equipment.html", **ctx)

@main.route("/equipment/case-scenes/<int:case_scene_id>/upload")
@login_required
def equipment_case_upload(case_scene_id):
    ctx_case = get_case_context(case_scene_id)
    ctx = equipment_base_ctx()
    ctx.update(
        active_tab="upload",
        selected_country_id=ctx_case["cs"].id,
        selected_country=ctx_case["case_key"],
        prefill_country=ctx_case["case_key"],
        prefill_room="",
        can_upload=True,
    )
    return render_template("equipment.html", **ctx)

@main.route("/equipment/case-scenes/<int:case_scene_id>/rooms/<int:room_id>")
@login_required
def equipment_case_room_report(case_scene_id, room_id):
    category = (request.args.get("category") or CAT_INSPECTION).strip().lower()
    data = build_case_room_report_ctx(case_scene_id, room_id, category)

    ctx = equipment_base_ctx(uploaded_items=data["uploaded_items"])
    ctx.update(
        active_tab=TAB_REPORT,
        report_filename=data["report_filename"],
        report_ctx=data["report_ctx"],
        selected_country=data["cs_key"],
        selected_room=data["room"].room_name,
        selected_country_id=data["cs"].id,
        selected_room_id=data["room"].id,
        equipments=data["equipments"],
        selected_files=data["room_files"],
        prefill_country=data["cs_key"],
        prefill_room=data["room"].room_name,
        category=data["category"],
        can_upload=True,
    )
    return render_template("equipment.html", **ctx)


@main.route("/equipment/case-scenes/<int:case_scene_id>/rooms/<int:room_id>/equipments")
@login_required
def equipment_case_room_equipments(case_scene_id, room_id):
    tab = (request.args.get("tab") or TAB_LIST).strip().lower()
    if tab not in (TAB_LIST, TAB_UPLOAD):
        tab = TAB_LIST

    category = (request.args.get("category") or CAT_INSPECTION).strip().lower()

    query = EquipmentQuery(
        q=(request.args.get("q") or "").strip(),
        type_id=request.args.get("type_id", type=int),
    )

    data = build_room_equipments_ctx(case_scene_id, room_id, query)

    ctx = equipment_base_ctx(uploaded_items=data["uploaded_items"])
    ctx.update(
        active_tab=tab,
        category=category,
        equipments=data["equipments"],
        q=query.q,
        selected_country_id=data["cs"].id,
        selected_room_id=data["room"].id,
        selected_country=data["cs_key"],
        selected_room=data["room"].room_name,
        selected_files=data["selected_files"],
        prefill_country=data["cs_key"],
        prefill_room=data["room"].room_name,
        can_upload=True,
    )
    return render_template("equipment.html", **ctx)


# ==========================================
# Legacy aliases (only redirect; remove after UI migrated)
# ==========================================
@main.route("/case-scenes/<int:case_scene_id>")
@login_required
def case_scene_root(case_scene_id):
    return redirect(url_for("main.equipment_case_scene_root", case_scene_id=case_scene_id), code=302)


@main.route("/case-scenes/<int:case_scene_id>/rooms/<int:room_id>")
@login_required
def case_room_report(case_scene_id, room_id):
    return redirect(url_for("main.equipment_case_room_report", case_scene_id=case_scene_id, room_id=room_id), code=302)


@main.route("/case-scenes/<int:case_scene_id>/rooms/<int:room_id>/equipments")
@login_required
def case_room_equipments(case_scene_id, room_id):
    return redirect(
        url_for("main.equipment_case_room_equipments", case_scene_id=case_scene_id, room_id=room_id, **request.args),
        code=302
    )


# ==========================================
# Admin reset
# ==========================================
@main.route("/admin/reset", methods=["POST"])
@login_required
def reset_system():
    if current_user.role != "superuser":
        return jsonify(success=False, message="你沒有權限執行重置"), 403

    try:
        EquipmentManage.query.delete()
        EquipmentInfo.query.delete()
        Room.query.delete()
        CaseScene.query.delete()
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify(success=False, message=f"清除資料庫失敗: {e}"), 500

    upload_root = current_app.config.get("UPLOAD_FOLDER")
    if upload_root and os.path.exists(upload_root):
        for root, _, files in os.walk(upload_root):
            for fname in files:
                try:
                    os.remove(os.path.join(root, fname))
                except Exception:
                    pass

    # clear any in-memory cache
    if hasattr(current_app, "uploaded_items"):
        try:
            current_app.uploaded_items.clear()
        except Exception:
            pass

    json_path = os.path.join(current_app.instance_path, "uploaded_items.json")
    if os.path.exists(json_path):
        try:
            os.remove(json_path)
        except Exception:
            pass

    return jsonify(success=True, message="系統已完全重置")


# ==========================================
# API
# ==========================================
@api.route("/", methods=["GET"])
def api_root():
    return api_ok({"ok": True}, status=200)


@api.route("/locations", methods=["POST"])
@login_required
def api_locations_create():
    data = request.get_json(silent=True) or {}
    raw_country = (data.get("country") or "").strip()
    raw_room = (data.get("room") or "").strip() or None

    if not raw_country:
        return api_error(400, "VALIDATION_ERROR", "country 不可為空")

    try:
        out = create_location(raw_country, raw_room)
        # 你原本回 success=True, **out；我就照你原本回法，只是統一走 api_ok
        payload = {"success": True, **out}
        return api_ok(payload, status=200)

    except ValueError as e:
        return api_error(400, "VALIDATION_ERROR", str(e))

    except Exception:
        current_app.logger.exception("api_locations_create failed")
        return api_error(500, "INTERNAL_SERVER_ERROR", "create location failed")


# legacy alias; remove after frontend migrated
@api.route("/location", methods=["POST"])
@login_required
def api_add_location():
    return api_locations_create()


@api.route("/uploads", methods=["POST"])
@login_required
def api_uploads_create():
    try:
        out = create_upload(request)
        payload = {"success": True, **out}
        return api_ok(payload, status=200)

    except ValueError as e:
        return api_error(400, "VALIDATION_ERROR", str(e))

    except Exception:
        current_app.logger.exception("api_uploads_create failed")
        return api_error(500, "INTERNAL_SERVER_ERROR", "upload failed")


# legacy alias; remove after frontend migrated
@api.route("/equipment/upload", methods=["POST"])
@login_required
def api_equipment_upload():
    return api_uploads_create()
