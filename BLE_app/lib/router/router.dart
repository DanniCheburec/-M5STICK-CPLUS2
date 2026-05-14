import 'package:ble_connect_m5/features/devices/devices.dart';
import 'package:ble_connect_m5/features/devices/view/main_page.dart';

final  route = {
        '/': (context) => const MainPage(),
        '/connectToM5': (context) => const DevicesListsScreen(),

      };