# Tezma AutoTube AI — Android avec entrée des clés

Cette version ajoute un écran **Configuration API** dans l'application Android.
Tu peux coller tes clés directement dans l'app sans les mettre dans le code source.

## Ce que l'app fait

- Sauvegarde locale des clés API dans les préférences privées Android.
- Envoie les clés au serveur uniquement pendant la génération d'une vidéo.
- Génère script, voix et vidéo via le serveur Python.
- Peut uploader sur YouTube si OAuth est configuré.

## Clés à remplir dans l'app

- `OPENAI_API_KEY` : obligatoire pour générer le script.
- `ELEVENLABS_API_KEY` : optionnel, pour la voix IA.
- `ELEVENLABS_VOICE_ID` : optionnel, ID de la voix ElevenLabs.
- `YOUTUBE_TOKEN_JSON` : optionnel, avancé. Le plus simple est de connecter YouTube côté serveur au premier upload.

## Lancer le serveur

```bash
cd server
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

## URL serveur dans l'app

- Émulateur Android : `http://10.0.2.2:8000/generate-video`
- Téléphone réel sur le même Wi-Fi : `http://IP_DE_TON_PC:8000/generate-video`

Exemple : `http://192.168.1.25:8000/generate-video`

## Sécurité

Ne publie jamais ces fichiers sur GitHub :

```gitignore
server/.env
server/client_secret.json
server/token.json
```

Les clés stockées dans l'app ne sont pas écrites dans le code, mais ce n'est pas un coffre-fort bancaire. Pour une version pro, il faut un backend avec compte utilisateur et chiffrement serveur.
