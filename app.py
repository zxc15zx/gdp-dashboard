# 📁 파일명 예시: app.py

import streamlit as st
import openai
import requests
import os
from moviepy.editor import *
import whisper
import uuid
import traceback

# 📌 API 키는 .streamlit/secrets.toml 에 설정해둔다
openai.api_key = st.secrets["openai_api_key"]
UNSPLASH_ACCESS_KEY = st.secrets["unsplash_api_key"]
TYPECAST_API_KEY = st.secrets["typecast_api_key"]

# 📁 디렉토리 생성
os.makedirs("audio", exist_ok=True)
os.makedirs("assets", exist_ok=True)
os.makedirs("output", exist_ok=True)

# 📄 에러 발생 시 로그를 기록하는 함수
def write_log(file_path, error_message):
    log_path = file_path.replace(".mp4", "_log.txt").replace(".mp3", "_log.txt").replace(".jpg", "_log.txt")
    with open(log_path, "w", encoding="utf-8") as f:
        f.write(error_message)

# ✅ 세션 상태 초기화
def init_session():
    keys = ['script', 'edited_script', 'audio_path', 'image_path', 'segments']
    for key in keys:
        if key not in st.session_state:
            st.session_state[key] = '' if key in ['script', 'edited_script'] else None

init_session()

# ✏️ 대본 생성 함수
def generate_script(topic):
    try:
        prompt = f"'{topic}'에 대해 30초 분량의 유튜브 쇼츠 대본을 만들어줘."
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )
        return response["choices"][0]["message"]["content"].strip()
    except Exception as e:
        write_log("output/script_error.txt", traceback.format_exc())
        st.error("대본 생성 중 오류가 발생했습니다.")
        return ""

# 🎧 Typecast 음성 생성 함수
def generate_typecast_voice(text, api_key, path, voice="seoyeon"):
    try:
        url = "https://typecast.ai/api/speak"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "voice": voice,
            "text": text,
            "speed": 1.0,
            "pitch": 1.0,
            "volume": 1.0,
            "format": "mp3"
        }
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 200:
            with open(path, "wb") as f:
                f.write(response.content)
            return True
        else:
            st.error(f"Typecast API 오류: {response.text}")
            write_log(path, response.text)
            return False
    except Exception:
        write_log(path, traceback.format_exc())
        return False

# 🖼️ Unsplash 이미지 다운로드
def download_unsplash_image(keyword, access_key, save_path):
    try:
        url = f"https://api.unsplash.com/photos/random?query={keyword}&client_id={access_key}"
        response = requests.get(url)
        data = response.json()
        if 'urls' not in data:
            raise ValueError("이미지 URL을 찾을 수 없습니다.")
        image_url = data['urls']['regular']
        image_data = requests.get(image_url).content
        with open(save_path, 'wb') as f:
            f.write(image_data)
    except Exception:
        write_log(save_path, traceback.format_exc())
        st.error("이미지 다운로드 중 오류가 발생했습니다.")

# 🎙️ Whisper 자막 추출
def extract_subtitles(audio_path):
    try:
        model = whisper.load_model("base")
        result = model.transcribe(audio_path)
        if 'segments' in result:
            return result['segments']
        else:
            raise ValueError("자막 구간이 없습니다.")
    except Exception:
        write_log(audio_path, traceback.format_exc())
        st.error("자막 추출 중 오류가 발생했습니다.")
        return []

# 🎞️ 영상 생성
def create_video(image_path, audio_path, subtitles, output_path):
    try:
        bg = ImageClip(image_path).set_duration(30).resize((1080, 1920))
        audio = AudioFileClip(audio_path)
        subtitle_clips = []

        for s in subtitles:
            txt_clip = TextClip(s['text'], fontsize=50, color='white', size=(1000, None), method='caption')
            txt_clip = txt_clip.set_position(('center', 'bottom')).set_start(s['start']).set_duration(s['end'] - s['start'])
            subtitle_clips.append(txt_clip)

        video = CompositeVideoClip([bg, *subtitle_clips])
        video = video.set_audio(audio)
        video.write_videofile(output_path, fps=24, codec='libx264', audio_codec='aac')
    except Exception:
        write_log(output_path, traceback.format_exc())
        st.error("영상 생성 중 오류가 발생했습니다.")

# 🖥️ Streamlit UI
st.title("🎬 AI 유튜브 쇼츠 생성기")

# 주제 입력
topic = st.text_input("주제를 입력하세요", "스마트폰 배터리 절약 방법")

# 대본 작성
st.subheader("📝 대본 입력/수정")
st.session_state['edited_script'] = st.text_area("대본을 입력하거나 생성해보세요", value=st.session_state.get('edited_script', ''), height=200)

if st.button("1️⃣ 대본 자동 생성"):
    script = generate_script(topic)
    st.session_state['script'] = script
    st.session_state['edited_script'] = script
    st.experimental_rerun()

# AI 음성 생성
st.subheader("🎧 AI 음성 생성")
if st.button("2️⃣ AI 음성 생성 (Typecast)") and st.session_state['edited_script']:
    audio_path = f"audio/{uuid.uuid4()}.mp3"
    if generate_typecast_voice(st.session_state['edited_script'], TYPECAST_API_KEY, audio_path):
        st.session_state['audio_path'] = audio_path
        st.audio(audio_path)

# 이미지 다운로드
st.subheader("🖼️ 배경 이미지 자동 다운로드")
if st.button("3️⃣ 배경 이미지 가져오기"):
    image_path = f"assets/{uuid.uuid4()}.jpg"
    download_unsplash_image(topic, UNSPLASH_ACCESS_KEY, image_path)
    st.session_state['image_path'] = image_path

if st.session_state['image_path']:
    st.image(st.session_state['image_path'], use_column_width=True)

# 자막 추출
st.subheader("🈸 자막 생성")
if st.button("4️⃣ 자막 생성 (Whisper)") and st.session_state['audio_path']:
    segments = extract_subtitles(st.session_state['audio_path'])
    st.session_state['segments'] = segments
    subtitle_text = "\n".join([f"[{s['start']:.1f}~{s['end']:.1f}] {s['text']}" for s in segments])
    st.text_area("📝 자막 확인", value=subtitle_text, height=300)

# 영상 생성
st.subheader("🎞️ 영상 생성")
if st.button("5️⃣ 영상 생성 및 다운로드") and all([
    st.session_state['segments'],
    st.session_state['image_path'],
    st.session_state['audio_path']
]):
    output_path = f"output/{uuid.uuid4()}.mp4"
    create_video(st.session_state['image_path'], st.session_state['audio_path'], st.session_state['segments'], output_path)
    st.video(output_path)
    with open(output_path, "rb") as f:
        st.download_button("📥 영상 다운로드", f, file_name="shorts_output.mp4")
