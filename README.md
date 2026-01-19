# mapwebsever (MPA: Flask + Jinja2)
## Project Overview

This repository is a Flask-based Equipment Management System demo project, focusing on backend architecture and maintainable system design.

Key highlights:
- Role-based access control (Superuser / Operator / User)
- Resource hierarchy: CaseScene → Room → Equipment
- Domain / Service / Route layered architecture
- MPA pages + API design (REST-style routing)
- File upload & inspection report workflow demo


這份是 **傳統多頁面（MPA）** 版本：每次切換案場/房間/頁面會發出 `document` 請求並重新載入整頁 HTML。
你在 DevTools Network 看到大量 `document` / `302 -> 200` 都屬於正常行為。

## Quick start

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate

pip install -r requirements.txt
python run.py
```

打開：http://127.0.0.1:5000

## Default accounts (初始化會自動建立)

- superuser / 1234
- operator  / 1234
- user      / 1234

> 密碼可在 `app/__init__.py` 看到初始化邏輯。

## Notes
- DB 位置：`instance/eq_manage.db`
- Upload 位置：`instance/uploads/`
