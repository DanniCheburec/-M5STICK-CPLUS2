import 'dart:async';
import 'dart:developer';

import 'package:flutter/material.dart';
// ignore: depend_on_referenced_packages
import 'package:flutter_blue_plus/flutter_blue_plus.dart';



class DevicesListsScreen extends StatefulWidget {
  const DevicesListsScreen({
    super.key,
  });

  @override
  State<DevicesListsScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<DevicesListsScreen> {

  // ignore: non_constant_identifier_names
  var _ScanResults = <ScanResult>[];
  StreamSubscription<List<ScanResult>>? _devicesSub;

  @override
  void initState() {  
    super.initState();
  }

  @override
  void dispose(){
    _devicesSub?.cancel();
    super.dispose();
  }

  Future<void> _enableFlutterBle() async{
    final isSupported = await FlutterBluePlus.isSupported;
    if(!isSupported){
      log('Ble not supported on this device');
    }

    final state = await FlutterBluePlus.adapterState.first;
    log(state.toString());
    if(state != BluetoothAdapterState.on){
      log('Bluetooth off');
      return;
    }

    _devicesSub?.cancel();
    _devicesSub = FlutterBluePlus.onScanResults.listen(
      (results) {
        log(FlutterBluePlus.isScanningNow.toString());
        setState(() => _ScanResults = results);        
      },
      onError: (e) => log(e),
    );
    

    FlutterBluePlus.startScan(
      timeout: const Duration(seconds: 15),
    );

  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        centerTitle: true,
        title: const Text('Devices List', style: TextStyle(fontSize: 25.0, fontWeight: FontWeight.w500, fontFamily: "Agate Grotesk")),
      ),
      body: ListView.separated(
        itemCount: _ScanResults.length,
        itemBuilder: (context, index) {
          final result = _ScanResults[index];
          return ListTile(
            textColor: Colors.white,
            title: Text(result.device.advName),
            titleTextStyle: TextStyle(fontWeight: FontWeight.w900),
            subtitle: Text(result.device.platformName),
            onTap: () {
              Navigator.of(context).pushNamed('/device_screen', arguments: result.device);
            },
            );    
        },
        separatorBuilder: (context, index) => const Divider(height: 1),
        ),
      floatingActionButton: FloatingActionButton(
        onPressed: _enableFlutterBle,
        child: const Icon(Icons.refresh),
      ),
    );
  }
}
