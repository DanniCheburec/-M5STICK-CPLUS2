import 'dart:async';
import 'dart:convert';
import 'dart:developer';
import 'package:flutter/material.dart';
import 'package:flutter_blue_plus/flutter_blue_plus.dart';
import 'package:http/http.dart' as http;

const String _serviceUuid        = "4fafc201-1fb5-459e-8fcc-c5c9c331914b";
const String _characteristicUuid = "beb5483e-36e1-4688-b7f5-ea07361b26a8";


const String _serverUrl = "http://192.168.60.212:5050/api/records";

class DeviceScreen extends StatefulWidget {
  const DeviceScreen({super.key, required this.device});

  final BluetoothDevice device;

  @override
  State<DeviceScreen> createState() => _DeviceScreenState();
}

class _DeviceScreenState extends State<DeviceScreen> {
  StreamSubscription<BluetoothConnectionState>? _connectionSub;
  StreamSubscription<List<int>>?                _notifySub;

  BluetoothCharacteristic? _characteristic;

  // Записи, полученные по BLE notify (накапливаются)
  final List<Map<String, dynamic>> _pendingRecords = [];

  // Статус UI
  String  _status     = "Подключение...";
  bool    _isSending  = false;
  bool    _isReady    = false;   // характеристика найдена и notify включён

  @override
  void initState() {
    super.initState();
    _connectionSub = widget.device.connectionState.listen((state) {
      if (state == BluetoothConnectionState.disconnected) {
        _setStatus("Переподключение...");
        setState(() => _isReady = false);
        _connectAndSetup();
      }
    });
    _connectAndSetup();
  }

  @override
  void dispose() {
    _notifySub?.cancel();
    _connectionSub?.cancel();
    widget.device.disconnect();
    super.dispose();
  }

  // ─── Подключение и настройка BLE ────────────────────────────────────────
  Future<void> _connectAndSetup() async {
    try {
      // Подключаемся (если уже подключены — connect() игнорируется)
      await widget.device.connect(timeout: const Duration(seconds: 15));

      final services = await widget.device.discoverServices();

      // Ищем нужный сервис
      final service = services.firstWhere(
        (s) => s.serviceUuid.toString().toLowerCase() == _serviceUuid,
        orElse: () => throw Exception("Сервис $_serviceUuid не найден"),
      );

      // Ищем нужную характеристику
      _characteristic = service.characteristics.firstWhere(
        (c) => c.characteristicUuid.toString().toLowerCase() == _characteristicUuid,
        orElse: () => throw Exception("Характеристика $_characteristicUuid не найдена"),
      );

      // Включаем notify — устройство само будет присылать данные при saveSnapshot()
      await _characteristic!.setNotifyValue(true);

      // Отменяем старую подписку если была (переподключение)
      await _notifySub?.cancel();
      _notifySub = _characteristic!.onValueReceived.listen(
        _onNotify,
        onError: (e) => _setStatus("Ошибка notify: $e"),
      );

      setState(() => _isReady = true);
      _setStatus("Подключено. Ожидаю данные с устройства...");
    } catch (e) {
      log("BLE setup error: $e");
      _setStatus("Ошибка: $e");
    }
  }

  // ─── Обработка входящего BLE-пакета ─────────────────────────────────────
  void _onNotify(List<int> rawBytes) {
    final json = utf8.decode(rawBytes, allowMalformed: true).trim();
    log("BLE notify: $json");

    try {
      final record = jsonDecode(json) as Map<String, dynamic>;
      setState(() {
        _pendingRecords.add(record);
        _status = "Получено записей: ${_pendingRecords.length}. "
                  "Нажмите «Отправить» когда будете готовы.";
      });
    } catch (e) {
      log("JSON parse error: $e  raw: $json");
      _setStatus("Ошибка разбора пакета: $json");
    }
  }

  // ─── Отправка накопленных записей на сервер ──────────────────────────────
  Future<void> _sendToServer() async {
    if (_pendingRecords.isEmpty) {
      _setStatus("Нет данных для отправки.");
      return;
    }

    setState(() {
      _isSending = true;
      _status    = "Отправка ${_pendingRecords.length} записей...";
    });

    try {
      final response = await http
          .post(
            Uri.parse(_serverUrl),
            headers: {
              "Content-Type": "application/json",
              "X-Source":     "mobile",
            },
            body: jsonEncode({
              "records": _pendingRecords,
              "source":  "mobile",
            }),
          )
          .timeout(const Duration(seconds: 15));

      if (response.statusCode == 200) {
        final body = jsonDecode(response.body) as Map<String, dynamic>;
        final inserted = body["inserted"] ?? 0;
        final skipped  = body["skipped"]  ?? 0;

        setState(() {
          _pendingRecords.clear();
          _status = "✓ Отправлено! inserted=$inserted, skipped=$skipped";
        });
      } else {
        _setStatus("Сервер вернул ${response.statusCode}: ${response.body}");
      }
    } on http.ClientException catch (e) {
      _setStatus("Сеть недоступна: $e");
    } on TimeoutException {
      _setStatus("Таймаут — сервер не ответил.");
    } catch (e) {
      _setStatus("Ошибка: $e");
    } finally {
      setState(() => _isSending = false);
    }
  }

  void _setStatus(String msg) {
    if (mounted) setState(() => _status = msg);
    log(msg);
  }

  // ─── UI ──────────────────────────────────────────────────────────────────
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        centerTitle: true,
        title: const Text(
          'M5StickC2',
          style: TextStyle(
            fontSize: 25.0,
            fontWeight: FontWeight.w500,
            fontFamily: "Agate Grotesk",
          ),
        ),
      ),
      body: Padding(
        padding: const EdgeInsets.all(24.0),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Индикатор подключения
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(
                  _isReady ? Icons.bluetooth_connected : Icons.bluetooth_searching,
                  color: _isReady ? Colors.green : Colors.orange,
                ),
                const SizedBox(width: 8),
                Text(
                  _isReady ? "BLE подключён" : "Подключение...",
                  style: TextStyle(
                    color: _isReady ? Colors.green : Colors.orange,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),

            const SizedBox(height: 32),

            // Счётчик записей
            Center(
              child: Column(
                children: [
                  Text(
                    "${_pendingRecords.length}",
                    style: Theme.of(context).textTheme.displayLarge?.copyWith(
                          fontWeight: FontWeight.bold,
                        ),
                  ),
                  const Text("записей ожидают отправки"),
                ],
              ),
            ),

            const SizedBox(height: 24),

            // Статус
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Theme.of(context).colorScheme.surfaceVariant,
                borderRadius: BorderRadius.circular(8),
              ),
              child: Text(
                _status,
                textAlign: TextAlign.center,
                style: const TextStyle(fontSize: 13),
              ),
            ),

            const SizedBox(height: 32),

            // Кнопка отправки
            ElevatedButton.icon(
              onPressed: (_isSending || _pendingRecords.isEmpty) ? null : _sendToServer,
              icon: _isSending
                  ? const SizedBox(
                      width: 18,
                      height: 18,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Icon(Icons.cloud_upload_outlined),
              label: Text(
                _isSending
                    ? "Отправка..."
                    : "Отправить на сервер (${_pendingRecords.length})",
              ),
              style: ElevatedButton.styleFrom(
                padding: const EdgeInsets.symmetric(vertical: 16),
              ),
            ),

            const SizedBox(height: 12),

            // Кнопка очистки (на случай если нужно сбросить без отправки)
            TextButton(
              onPressed: _pendingRecords.isEmpty
                  ? null
                  : () {
                      setState(() {
                        _pendingRecords.clear();
                        _status = "Буфер очищен.";
                      });
                    },
              child: const Text("Очистить буфер"),
            ),
          ],
        ),
      ),
    );
  }
}