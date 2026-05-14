import 'package:flutter/material.dart';

class MainPage extends StatelessWidget {
  const MainPage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        centerTitle: true,
        title: const Text('Send Emotions Data', style: TextStyle(fontSize: 25.0, fontWeight: FontWeight.w500, fontFamily: "Agate Grotesk")),
      ),
      body: Center(
        child: ElevatedButton(
          child: const Text('Connect to M5'),
          onPressed: () {
            Navigator.of(context).pushNamed('/connectToM5');
            },

        ),
        )
    );
  }
}