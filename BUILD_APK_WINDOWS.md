# Compiler l’APK sur Windows

1. Installe Android Studio.
2. Ouvre le dossier `android-app`.
3. Attends la synchronisation Gradle.
4. Va dans **Build > Build Bundle(s) / APK(s) > Build APK(s)**.
5. L’APK sera créé ici :

```text
android-app/app/build/outputs/apk/debug/app-debug.apk
```

Pour installer sur ton téléphone : envoie le fichier APK sur Android, puis autorise “installer des applications inconnues”.

# Compiler automatiquement avec GitHub

1. Mets ce projet sur ton GitHub.
2. Va dans l’onglet **Actions**.
3. Lance **Build Android APK**.
4. Télécharge l’artefact `TezmaAutoTubeAI-debug-apk`.
