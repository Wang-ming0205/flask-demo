# tests/test_upload_shell.py
import os
from app import create_app, db
from app.models import EquipmentInfo
from app.service import upload_and_register_auto
from werkzeug.datastructures import FileStorage

def test_upload_and_query():
    app = create_app()
    app.app_context().push()

    # 正確檔案路徑
    file_path = "app/uploads/LU015K15330000170A_Inspection_Result_20251024_131806.csv"
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"{file_path} 不存在")

    # 包裝 FileStorage
    with open(file_path, "rb") as f:
        file_storage = FileStorage(stream=f, filename=os.path.basename(file_path))
        upload_and_register_auto(file_storage)

    # 查詢 EquipmentInfo
    equipments = EquipmentInfo.query.all()
    for e in equipments:
        print(e.id, e.kaori_sn, e.supermicro_sn, e.firmware, e.room_id, e.equipment_type_id)

if __name__ == "__main__":
    test_upload_and_query()
