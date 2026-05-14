import 'package:ble_connect_m5/features/devices/devices.dart';
import 'package:ble_connect_m5/router/router.dart';
import 'package:flutter/material.dart';
import 'package:ble_connect_m5/theme/theme.dart';
// ignore: depend_on_referenced_packages
import 'package:flutter_blue_plus/flutter_blue_plus.dart';


void main() {
  FlutterBluePlus.setLogLevel(LogLevel.verbose, color:false);
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Flutter Demo',
      theme: m5theme,
      routes: route,
      onGenerateRoute: route_to_device_screen,
    );
  }

  Route<dynamic>? route_to_device_screen(settings) {
    if (settings.name == '/device_screen') {
      final device = settings.arguments as BluetoothDevice;
  
      return MaterialPageRoute(
        builder: (_) => DeviceScreen(device: device),
      );
    }
    return null;
  }
}

