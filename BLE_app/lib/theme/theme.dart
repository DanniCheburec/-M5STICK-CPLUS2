import 'package:flutter/material.dart';

final m5theme = ThemeData(
  elevatedButtonTheme: ElevatedButtonThemeData(
          style: ElevatedButton.styleFrom(
            backgroundColor: const Color.fromARGB(255, 255, 196, 46),
            foregroundColor: const Color.fromARGB(255, 0, 0, 0),
            minimumSize: const Size(200, 60),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(15)
            ),

          )
        ),

  scaffoldBackgroundColor: const Color.fromARGB(255, 96, 96, 96),
  primarySwatch: Colors.amber,
  appBarTheme: const AppBarTheme(backgroundColor: Colors.amber, titleTextStyle: TextStyle(fontWeight: FontWeight.w700),),
  colorScheme: .fromSeed(seedColor: Colors.deepPurple),
  useMaterial3: true,
      );

