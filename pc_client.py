"""
pc_client.py — ПК-клиент.
Читает данные с M5Stick по Serial и отправляет на Streamlit API.

Запуск: python pc_client.py
Зависимости: pip install pyserial requests
"""

import json
import time
import serial
import requests
import serial.tools.list_ports

API_URL   = "http://localhost:5050/api/records"
BAUD_RATE = 9600
POLL_SEC  = 30   # как часто опрашивать устройство


#  Поиск порта 
def find_port() -> str | None:
    for p in serial.tools.list_ports.comports():
        if any(x in p.description for x in ["CP210", "CH910", "USB Serial", "UART"]):
            return p.device
    return None


#  Разбор строки JSON 
def parse_line(line: str) -> dict | None:
    line = line.strip()
    if not line or not line.startswith("{"):
        return None
    try:
        return json.loads(line)
    except json.JSONDecodeError as e:
        print(f"  [!] Не JSON: {line!r} — {e}")
        return None


#  Отправка пакета на сервер 
def send_to_server(records: list[dict]) -> bool:
    try:
        r = requests.post(
            API_URL,
            json={"records": records, "source": "serial"},
            timeout=10,
        )
        data = r.json()
        print(f"  [✓] Сервер принял: inserted={data.get('inserted')}, skipped={data.get('skipped')}")
        return r.status_code == 200
    except requests.RequestException as e:
        print(f"  [✗] Ошибка сервера: {e}")
        return False


#  Один цикл опроса 
def poll_once(ser: serial.Serial) -> None:
    print("→ Отправляю SEND...")
    ser.reset_input_buffer()
    ser.write(b"SEND\n")

    records  = []
    deadline = time.time() + 15  

    while time.time() < deadline:
        raw = ser.readline().decode("utf-8", errors="ignore").strip()
        if not raw:
            continue
        print(f"  << {raw!r}")   
        if raw == "END":
            break
        rec = parse_line(raw)
        if rec:
            records.append(rec)

    print(f"  Получено записей: {len(records)}")

    if not records:
        print("  Нет данных на устройстве.")
        return

    if send_to_server(records):
        ser.write(b"OK\n")
        print("  Отправил OK устройству — память очищена.")
    else:
        print("  Сервер недоступен, данные НЕ удалены с устройства.")


#  Главный цикл 
def main() -> None:
    print("=== Emotion Tracker PC Client ===")
    print(f"API: {API_URL}")

    port = find_port()
    if not port:
        # Список портов для выбора вручную
        ports = [p.device for p in serial.tools.list_ports.comports()]
        print(f"\nПорт M5Stick не найден автоматически.")
        print(f"Доступные порты: {ports or 'нет'}")
        port = input("Введите порт вручную (например COM3 или /dev/ttyUSB0): ").strip()
        if not port:
            return

    print(f"Порт: {port}\n")

    try:
        with serial.Serial(port, BAUD_RATE, timeout=5) as ser:
            ser.dtr = False
            ser.rts = False
            time.sleep(3) 
            ser.reset_input_buffer()
            print("Подключено. Начинаю опрос...\n")

            while True:
                try:
                    poll_once(ser)
                except serial.SerialException as e:
                    print(f"Ошибка порта: {e}")
                    break

                print(f"  Следующий опрос через {POLL_SEC} сек...\n")
                time.sleep(POLL_SEC)

    except serial.SerialException as e:
        print(f"Не удалось открыть порт {port}: {e}")


if __name__ == "__main__":
    main()