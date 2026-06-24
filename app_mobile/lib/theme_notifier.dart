import 'package:flutter/material.dart';

class ThemeNotifier extends ValueNotifier<ThemeMode> {
  ThemeNotifier() : super(ThemeMode.system);

  void toggleTheme(ThemeMode mode) {
    value = mode;
  }
}

final themeNotifier = ThemeNotifier();
