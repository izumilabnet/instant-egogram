import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from google import genai
from google.genai import types
import json
import os
import re
import statistics
import time

# --- 0. 起動中メッセージ ---
if 'initialized' not in st.session_state:
    with st.spinner('🚀 システム起動中（1分程度かかる場合があります）...'):
        time.sleep(1.5)
    st.session_state.initialized = True

# --- 1. ページ設定とスタイル ---
st.set_page_config(page_title="INSTANT EGOGRAM", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #f0f9f6; color: #2c3e50; }
    .main-title { font-size: 2.5rem; font-weight: 800; color: #2d6a4f; margin-bottom: 0.5rem; text-align: center; }
    .main-subtitle { font-size: 1rem; color: #6d28d9; text-align: center; margin-bottom: 2rem; }
    .res-card { background: #ffffff; padding: 1.5rem; border-radius: 12px; border: 1px solid #d8e2dc; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 1rem; }
    .privacy-box { background-color: #eff6ff; border: 1px solid #bfdbfe; padding: 15px; border-radius: 10px; margin-bottom: 20px; }
    .feature-box { background-color: #ffffff; border: 1px solid #e5e7eb; padding: 15px; border-radius: 10px; margin-bottom: 20px; }
    div.stButton > button { width: 100%; background: linear-gradient(135deg, #52b788 0%, #40916c 100%); color: white; border: none; padding: 0.75rem; font-weight: bold; border-radius: 8px; transition: 0.3s; }
    .footer { text-align: center; color: #9ca3af; font-size: 0.8rem; margin-top: 2rem; }
    /* iOS読み上げボタン専用スタイル */
    .tts-btn { background: #f0fdf4; border: 1px solid #52b788; border-radius: 8px; color: #2d6a4f; cursor: pointer; padding: 8px; font-size: 1.2rem; width: 100%; height: 45px; transition: 0.2s; }
    .tts-btn:active { background: #dcfce7; }
    </style>
    """, unsafe_allow_html=True)

if 'auth' not in st.session_state: st.session_state.auth = False
if 'diagnosis' not in st.session_state: st.session_state.diagnosis = None

ANALYSIS_TRIALS = 1

# --- 2. 認証 ---
if not st.session_state.auth:
    st.markdown("<h1 class='main-title'>インスタント・エゴグラム</h1>", unsafe_allow_html=True)
    col_top_1, col_top_2, col_top_3 = st.columns([1, 2, 1])
    with col_top_2:
        pw = st.text_input("Password", type="password", key="login_pw")
        if st.button("分析を開始する"):
            if pw == "okok":
                st.session_state.auth = True
                st.rerun()
    st.stop()

# --- 3. 分析エンジン ---
def get_single_analysis(text, gender, age, client):
    model_id = "gemini-2.5-flash"
    prompt_content = f"属性: {age}、{gender}。対象文章: '{text}' エゴグラム(CP,NP,A,FC,AC)を-10〜10で算出し性格診断せよ。必ずJSON形式のみで回答し、回答構成: {{\"scores\": {{\"CP\":0, \"NP\":0, \"A\":0, \"FC\":0, \"AC\":0}}, \"性格類型\": \"...\", \"特徴\": \"...\", \"適職\": \"...\", \"恋愛のアドバイス\": \"...\", \"成長へ向けて\": \"...\"}}"
    try:
        response = client.models.generate_content(
            model=model_id, contents=prompt_content,
            config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0.2)
        )
        return json.loads(re.search(r'(\{.*\})', response.text.strip(), re.DOTALL).group(1))
    except: return None

def run_full_diagnosis(text, gender, age):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key: return None
    client = genai.Client(api_key=api_key)
    all_results = []
    progress_text = st.empty()
    my_bar = st.progress(0)
    for i in range(ANALYSIS_TRIALS):
        res = get_single_analysis(text, gender, age, client)
        if res: all_results.append(res)
        my_bar.progress((i + 1) / ANALYSIS_TRIALS)
    if not all_results: return None
    base_res = all_results[0]
    final_scores = {k: float(statistics.multimode([int(round(float(s.get(k, 0)))) for s in [r["scores"] for r in all_results]])[0]) for k in ["CP", "NP", "A", "FC", "AC"]}
    confidences = {k: (sum(1 for v in [int(round(float(s.get(k, 0)))) for s in [r["scores"] for r in all_results]] if (statistics.median([int(round(float(s.get(k, 0)))) for s in [r["scores"] for r in all_results]])-1) <= v <= (statistics.median([int(round(float(s.get(k, 0)))) for s in [r["scores"] for r in all_results]])+1)) / ANALYSIS_TRIALS) * 100 for k in ["CP", "NP", "A", "FC", "AC"]}
    return {**base_res, "scores": final_scores, "confidences": confidences, "raw_samples": [r["scores"] for r in all_results]}

# --- 4. メイン画面 ---
if st.session_state.diagnosis is None:
    gender = st.selectbox("性別", ["", "男性", "女性", "その他"], index=0)
    age = st.selectbox("年齢", ["", "10代", "20代", "30代", "40代", "50代", "60代以上"], index=0)
    input_text = st.text_area("文章を入力", height=200)
    if st.button("🚀 診断プロファイルを開始"):
        if input_text:
            result = run_full_diagnosis(input_text, gender, age)
            if result: st.session_state.diagnosis = result; st.rerun()
else:
    res = st.session_state.diagnosis
    col1, col2 = st.columns([1.2, 1])
    with col1:
        st.markdown("<div class='res-card'>", unsafe_allow_html=True)
        h_col1, h_col2 = st.columns([4, 1])
        h_col1.subheader("📊 心理特性プロファイル")
        with h_col2:
            # iOSの制限を回避するHTML/JS直接埋め込みボタン
            speech_msg = f"診断結果は{res['性格類型']}。{res['特徴']}".replace('"', '”').replace('\n', ' ')
            st.components.v1.html(f"""
                <button class="tts-btn" onclick="
                    const synth = window.speechSynthesis;
                    if (synth.speaking) {{ synth.cancel(); }}
                    else {{
                        const uttr = new SpeechSynthesisUtterance('{speech_msg}');
                        uttr.lang = 'ja-JP';
                        uttr.rate = 1.0;
                        // iOS用のアクティベーション
                        synth.speak(new SpeechSynthesisUtterance(' '));
                        synth.speak(uttr);
                    }}
                ">🔊</button>
                <style>
                .tts-btn {{ background: #f0fdf4; border: 1px solid #52b788; border-radius: 8px; color: #2d6a4f; cursor: pointer; width: 100%; height: 40px; font-size: 1.2rem; }}
                </style>
            """, height=45)

        df = pd.DataFrame(list(res["scores"].items()), columns=['項目', '値'])
        fig = go.Figure()
        fig.add_trace(go.Bar(x=df['項目'], y=df['値'], marker_color='rgba(82, 183, 136, 0.3)'))
        fig.add_trace(go.Scatter(x=df['項目'], y=df['値'], mode='lines+markers', line=dict(color='#ff7b72', width=4)))
        fig.update_layout(height=400, margin=dict(l=0,r=0,t=20,b=0), yaxis=dict(range=[-10.5, 10.5]))
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        
        with st.expander("🛠️ 解析データ表示"):
            st.dataframe(pd.DataFrame(res["raw_samples"]), use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
    with col2:
        st.markdown(f"<div class='res-card'><h2>🏆 {res['性格類型']}</h2><p>{res['特徴']}</p></div>", unsafe_allow_html=True)
        t3, t1, t2 = st.tabs(["🌱 成長", "💼 適職", "❤️ 恋愛"])
        t3.write(res['成長へ向けて']); t1.write(res['適職']); t2.write(res['恋愛のアドバイス'])

    if st.button("🔄 戻る"):
        st.session_state.diagnosis = None; st.rerun()