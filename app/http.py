# app/http.py
from flask import jsonify

def api_ok(data=None, status=200, headers=None):
    resp = jsonify(data if data is not None else {})
    resp.status_code = status
    if headers:
        for k, v in headers.items():
            resp.headers[k] = str(v)
    return resp

def api_error(status, code, message, details=None):
    payload = {"error": {"code": code, "message": message}}
    if details is not None:
        payload["error"]["details"] = details
    resp = jsonify(payload)
    resp.status_code = status
    return resp
