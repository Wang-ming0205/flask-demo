"""Service layer (business logic).

For now we keep the original implementation in `_legacy.py` and re-export key
functions from smaller modules. This keeps behavior stable while enabling
gradual refactoring.
"""

from .upload_service import init_upload_folders, load_uploaded_items, save_uploaded_items, append_uploaded_item, validate_ext, save_feedback_text
from .equipment_service import build_tree_items, build_room_equipments_ctx, get_case_context
from .report_service import get_case_room_report_context, parse_equipment_file

# Legacy exports still used by routes
from ._legacy import (
    roles_required,
    save_feedback_with_photos,
    create_location,
    create_upload,
    build_case_room_report_ctx,
    build_inspection_report_context,
)
