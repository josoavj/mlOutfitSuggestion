# Integration Flutter Android - Smart Mirror Outfit ML

## Objectif

Cette documentation explique comment integrer l'API ML de suggestion de tenues dans une application Flutter Android avec camera integree.

Flux cible en production:

1. Capture camera dans Flutter
2. Appel `POST /mirror/recommend-from-camera`
3. Identification utilisateur par visage
4. Recuperation profil + agenda + meteo
5. Retour des suggestions de tenue

## Prerequis Backend

Dans le projet backend (`mlOutfitSuggestion`):

1. Installer les dependances Python:

```bash
~/.pyenv/bin/python -m pip install -r requirements.txt
```

2. Entrainer le modele (si pas deja fait):

```bash
~/.pyenv/bin/python -m src.outfit_ml.train --samples 4000
```

3. Installer la reconnaissance faciale:

```bash
~/.pyenv/bin/python -m pip install face-recognition
```

4. Configurer les variables d'environnement:

```bash
cp .env.example .env
```

Exemple `.env` minimal (mode fichier local, sans API MagicMirror):

```env
OPENWEATHER_API_KEY=ta_cle_openweather

MAGICMIRROR_DATA_SOURCE=file
MAGICMIRROR_PROFILE_FILE_TEMPLATE=data/users/{user_id}/profile.json
MAGICMIRROR_AGENDA_FILE_TEMPLATE=data/users/{user_id}/agenda_today.json

FACE_REGISTRY_PATH=data/vision/face_registry.json
```

5. Lancer le serveur API:

```bash
uvicorn src.outfit_ml.api:app --reload
```

## Endpoints utiles

### 1. Enroler un visage

`POST /vision/enroll`

Payload:

```json
{
  "user_id": "u-001",
  "image_base64": "data:image/jpeg;base64,..."
}
```

Usage: a faire une fois (ou lors d'une mise a jour du visage de reference).

### 2. Identifier un visage

`POST /vision/identify`

Payload:

```json
{
  "image_base64": "data:image/jpeg;base64,...",
  "threshold": 0.45,
  "max_results": 1
}
```

### 3. Endpoint unifie recommande

`POST /mirror/recommend-from-camera`

Payload:

```json
{
  "image_base64": "data:image/jpeg;base64,...",
  "location": "Lyon",
  "threshold": 0.45,
  "top_k": 3
}
```

Ce endpoint execute toute la chaine automatiquement.

## Integration Flutter Android

## 1. pubspec.yaml

```yaml
dependencies:
  flutter:
    sdk: flutter
  camera: ^0.11.0+2
  http: ^1.2.2
```

## 2. Service API (Dart)

```dart
import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;

class MirrorApiService {
  MirrorApiService({required this.baseUrl});

  final String baseUrl; // Emulateur Android: http://10.0.2.2:8000

  Future<Map<String, dynamic>> recommendFromCamera({
    required File imageFile,
    String? location,
    double threshold = 0.45,
    int topK = 3,
  }) async {
    final bytes = await imageFile.readAsBytes();
    final imageBase64 = 'data:image/jpeg;base64,${base64Encode(bytes)}';

    final payload = {
      'image_base64': imageBase64,
      'location': location,
      'threshold': threshold,
      'top_k': topK,
    };

    final response = await http.post(
      Uri.parse('$baseUrl/mirror/recommend-from-camera'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode(payload),
    );

    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw Exception('API error ${response.statusCode}: ${response.body}');
    }

    return jsonDecode(response.body) as Map<String, dynamic>;
  }
}
```

## 3. Capture camera + appel endpoint (Dart)

```dart
import 'dart:convert';
import 'dart:io';

import 'package:camera/camera.dart';
import 'package:flutter/material.dart';

class CameraRecoPage extends StatefulWidget {
  const CameraRecoPage({super.key});

  @override
  State<CameraRecoPage> createState() => _CameraRecoPageState();
}

class _CameraRecoPageState extends State<CameraRecoPage> {
  CameraController? _controller;
  bool _loading = false;
  Map<String, dynamic>? _result;

  final api = MirrorApiService(baseUrl: 'http://10.0.2.2:8000');

  @override
  void initState() {
    super.initState();
    _initCamera();
  }

  Future<void> _initCamera() async {
    final cameras = await availableCameras();
    final front = cameras.firstWhere(
      (c) => c.lensDirection == CameraLensDirection.front,
      orElse: () => cameras.first,
    );

    _controller = CameraController(
      front,
      ResolutionPreset.medium,
      enableAudio: false,
    );

    await _controller!.initialize();
    if (mounted) setState(() {});
  }

  Future<void> _captureAndRecommend() async {
    if (_controller == null || !_controller!.value.isInitialized) return;

    setState(() => _loading = true);
    try {
      final picture = await _controller!.takePicture();
      final reco = await api.recommendFromCamera(
        imageFile: File(picture.path),
        location: 'Lyon',
        threshold: 0.45,
        topK: 3,
      );
      setState(() => _result = reco);
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Erreur: $e')),
      );
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  void dispose() {
    _controller?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (_controller == null || !_controller!.value.isInitialized) {
      return const Scaffold(
        body: Center(child: CircularProgressIndicator()),
      );
    }

    return Scaffold(
      appBar: AppBar(title: const Text('Smart Mirror Reco')),
      body: Column(
        children: [
          AspectRatio(
            aspectRatio: _controller!.value.aspectRatio,
            child: CameraPreview(_controller!),
          ),
          const SizedBox(height: 12),
          ElevatedButton(
            onPressed: _loading ? null : _captureAndRecommend,
            child: _loading
                ? const CircularProgressIndicator()
                : const Text('Identifier + Recommander'),
          ),
          if (_result != null)
            Expanded(
              child: SingleChildScrollView(
                padding: const EdgeInsets.all(12),
                child: Text(const JsonEncoder.withIndent('  ').convert(_result)),
              ),
            ),
        ],
      ),
    );
  }
}
```

## Android: adresse backend

- Emulateur Android: `http://10.0.2.2:8000`
- Smartphone physique: `http://IP_LOCALE_PC:8000`

## Recommandations pour robustesse

1. Garder une image frontale, bien eclairee, un seul visage.
2. Enroler 2 a 3 images par utilisateur (et conserver la meilleure reference).
3. Ajouter anti-spoofing/liveness avant validation d'identite.
4. Utiliser HTTPS en production.
5. Ajouter consentement explicite et option de desactivation biometrie.

## Reponses d'erreur frequentes

- 400: image invalide, aucun visage, plusieurs visages.
- 404: aucun utilisateur reconnu dans la registry.
- 501: package `face-recognition` non installe.
- 502: erreur OpenWeather ou source profil/agenda.

## Checklist integration

1. `requirements.txt` installe
2. Modele entraine (`models/outfit_ranker.joblib`)
3. `OPENWEATHER_API_KEY` configuree
4. Registry visage configuree (`FACE_REGISTRY_PATH`)
5. Test `POST /vision/enroll` puis `POST /mirror/recommend-from-camera`
6. Integration Flutter OK (camera + http)
