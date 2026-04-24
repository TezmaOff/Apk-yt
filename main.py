import os, json, base64, uuid, subprocess
from pathlib import Path
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips

load_dotenv()
BASE = Path(__file__).resolve().parent
OUT = BASE / "outputs"
OUT.mkdir(exist_ok=True)

app = FastAPI(title="Tezma AutoTube AI")
app.mount("/outputs", StaticFiles(directory=str(OUT)), name="outputs")

class VideoRequest(BaseModel):
    # Clés optionnelles envoyées par l’app Android. Si vide, le serveur utilise .env.
    openai_api_key: Optional[str] = Field(default=None, exclude=True)
    elevenlabs_api_key: Optional[str] = Field(default=None, exclude=True)
    elevenlabs_voice_id: Optional[str] = Field(default=None, exclude=True)
    youtube_token_json: Optional[str] = Field(default=None, exclude=True)

    niche: str = "histoire de France"
    topic: str = "un fait historique incroyable"
    duration_seconds: int = 60
    style: str = "mystérieux, accrocheur, simple"
    format: str = "short"  # short = 9:16
    upload_youtube: bool = False
    privacy_status: str = "private"  # private, unlisted, public

class VideoResponse(BaseModel):
    job_id: str
    title: str
    script: str
    description: str
    video_url: str
    local_path: str
    youtube_video_id: Optional[str] = None


def openai_client(api_key: Optional[str] = None):
    from openai import OpenAI
    key = api_key or os.getenv("OPENAI_API_KEY")
    if not key or key.startswith("sk-REMPLACE"):
        raise HTTPException(400, "OPENAI_API_KEY manquante: ajoute-la dans l’app Android ou dans server/.env")
    return OpenAI(api_key=key)


def generate_script(req: VideoRequest):
    client = openai_client(req.openai_api_key)
    prompt = f"""
Crée une vidéo YouTube Shorts en français.
Niche: {req.niche}
Sujet: {req.topic}
Durée cible: {req.duration_seconds} secondes.
Style: {req.style}.
Format attendu JSON strict avec title, description, script, image_prompts (5 prompts).
Le script doit être naturel, captivant, avec hook au début et conclusion courte.
"""
    r = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role":"user","content":prompt}],
        temperature=0.8,
    )
    txt = r.choices[0].message.content.strip()
    txt = txt.replace("```json","").replace("```","").strip()
    try:
        data = json.loads(txt)
    except Exception:
        data = {"title": req.topic[:90], "description":"Vidéo générée avec Tezma AutoTube AI", "script": txt, "image_prompts":[req.topic]*5}
    return data


def generate_voice(script: str, out_mp3: Path, req: VideoRequest):
    api_key = req.elevenlabs_api_key or os.getenv("ELEVENLABS_API_KEY")
    voice_id = req.elevenlabs_voice_id or os.getenv("ELEVENLABS_VOICE_ID")
    if not api_key or not voice_id or "REMPLACE" in api_key or "REMPLACE" in voice_id:
        # voix placeholder muette si ElevenLabs n'est pas configuré
        subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", "20", str(out_mp3)], check=True)
        return
    import requests
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    payload = {"text": script, "model_id":"eleven_multilingual_v2", "voice_settings":{"stability":0.45,"similarity_boost":0.75}}
    headers = {"xi-api-key": api_key, "Content-Type":"application/json"}
    resp = requests.post(url, headers=headers, json=payload, timeout=120)
    if resp.status_code >= 400:
        raise HTTPException(resp.status_code, f"Erreur ElevenLabs: {resp.text[:300]}")
    out_mp3.write_bytes(resp.content)


def generate_placeholder_images(prompts: List[str], job_dir: Path):
    paths = []
    for i, prompt in enumerate(prompts[:5]):
        img = Image.new("RGB", (1080, 1920), (18, 18, 28))
        draw = ImageDraw.Draw(img)
        text = f"TEZMA AI\n\n{prompt[:180]}"
        draw.multiline_text((80, 520), text, fill=(240,240,240), spacing=18)
        p = job_dir / f"image_{i+1}.jpg"
        img.save(p, quality=92)
        paths.append(p)
    return paths


def create_video(images: List[Path], audio_path: Path, out_mp4: Path):
    audio = AudioFileClip(str(audio_path))
    duration = max(audio.duration, 20)
    per = duration / len(images)
    clips = [ImageClip(str(p)).set_duration(per).resize((1080,1920)) for p in images]
    video = concatenate_videoclips(clips, method="compose").set_audio(audio)
    video.write_videofile(str(out_mp4), fps=30, codec="libx264", audio_codec="aac")


def upload_to_youtube(video_path: Path, title: str, description: str, privacy: str, token_json: Optional[str] = None):
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    from google.oauth2.credentials import Credentials
    token_file = BASE / os.getenv("YOUTUBE_TOKEN_FILE", "token.json")
    secrets_file = BASE / os.getenv("YOUTUBE_CLIENT_SECRETS_FILE", "client_secret.json")
    scopes = ["https://www.googleapis.com/auth/youtube.upload"]
    if token_json:
        token_file.write_text(token_json, encoding="utf-8")
        creds = Credentials.from_authorized_user_file(str(token_file), scopes)
    elif token_file.exists():
        creds = Credentials.from_authorized_user_file(str(token_file), scopes)
    else:
        if not secrets_file.exists():
            raise HTTPException(400, "client_secret.json manquant pour YouTube OAuth")
        flow = InstalledAppFlow.from_client_secrets_file(str(secrets_file), scopes)
        creds = flow.run_local_server(port=0)
        token_file.write_text(creds.to_json(), encoding="utf-8")
    youtube = build("youtube", "v3", credentials=creds)
    body = {"snippet":{"title": title[:100], "description": description, "categoryId":"22"}, "status":{"privacyStatus": privacy}}
    media = MediaFileUpload(str(video_path), chunksize=-1, resumable=True, mimetype="video/mp4")
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    response = None
    while response is None:
        _, response = request.next_chunk()
    return response.get("id")

@app.post("/generate-video", response_model=VideoResponse)
def generate_video(req: VideoRequest):
    job_id = str(uuid.uuid4())[:8]
    job_dir = OUT / job_id
    job_dir.mkdir(exist_ok=True)
    data = generate_script(req)
    audio = job_dir / "voice.mp3"
    generate_voice(data["script"], audio, req)
    images = generate_placeholder_images(data.get("image_prompts", [req.topic]*5), job_dir)
    video = job_dir / "video.mp4"
    create_video(images, audio, video)
    yt_id = None
    if req.upload_youtube:
        yt_id = upload_to_youtube(video, data["title"], data["description"], req.privacy_status, req.youtube_token_json)
    return VideoResponse(job_id=job_id, title=data["title"], script=data["script"], description=data["description"], video_url=f"/outputs/{job_id}/video.mp4", local_path=str(video), youtube_video_id=yt_id)

@app.get("/")
def root():
    return {"status":"ok", "name":"Tezma AutoTube AI", "endpoint":"POST /generate-video"}
