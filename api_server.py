"""
api_server.py — Flask REST API.
Запускается в отдельном потоке из app.py (или самостоятельно).

Эндпоинты:
  POST /api/records        — принять пакет с устройства / ПК / мобилки
  GET  /api/records        — отдать все записи (JSON)
  GET  /api/health         — проверка жизни
"""

import threading
from flask import Flask, request, jsonify
from database import init_db, insert_records, fetch_all, fetch_stats

#  Инициализация 
init_db()

flask_app = Flask(__name__)

# Разрешаем CORS для Web Bluetooth / мобильного клиента
@flask_app.after_request
def add_cors(response):
    response.headers["Access-Control-Allow-Origin"]  = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response


#  POST /api/records 
@flask_app.route("/api/records", methods=["POST", "OPTIONS"])
def post_records():
    if request.method == "OPTIONS":
        return jsonify({"ok": True}), 200

    body = request.get_json(silent=True)
    if not body:
        return jsonify({"error": "Пустое тело запроса"}), 400

    records = body.get("records") if isinstance(body.get("records"), list) else [body]

    if not records:
        return jsonify({"error": "Нет записей"}), 400

    # source — откуда пришли данные (serial / ble / web / mobile)
    source = body.get("source", request.headers.get("X-Source", "unknown"))

    inserted, skipped = insert_records(records, source=source)

    return jsonify({
        "ok":       True,
        "inserted": inserted,
        "skipped":  skipped,
    }), 200


#  GET /api/records 
@flask_app.route("/api/records", methods=["GET"])
def get_records():
    return jsonify(fetch_all()), 200


#  GET /api/stats 
@flask_app.route("/api/stats", methods=["GET"])
def get_stats():
    return jsonify(fetch_stats()), 200


#  GET /api/health 
@flask_app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"ok": True}), 200


#  Запуск в фоновом потоке (вызывается из app.py) 
API_HOST = "0.0.0.0"
API_PORT = 5050

def run_api_server():
    """Запустить Flask в daemon-потоке. Вызывать один раз из app.py."""
    t = threading.Thread(
        target=lambda: flask_app.run(
            host=API_HOST,
            port=API_PORT,
            debug=False,
            use_reloader=False,   # обязательно — иначе конфликт с Streamlit
        ),
        daemon=True,
        name="FlaskAPIThread",
    )
    t.start()
    return t


#  Автономный запуск (python api_server.py) 
if __name__ == "__main__":
    print(f"API сервер: http://{API_HOST}:{API_PORT}")
    flask_app.run(host=API_HOST, port=API_PORT, debug=True)