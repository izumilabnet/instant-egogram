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

# --- 0. 解析回数設定（開発時:1 / 運用時:5） ---
ANALYSIS_TRIALS = 1 

# --- 1. ページ設定とスタイル ---
st.set_page_config(page_title="INSTANT EGOGRAM PRO", layout="wide")

st.markdown("""
    <style>
    /* 全体背景 */
    .stApp {
        background-color: #0d1117;
        color: #c9d1d9;
    }
    /* メインタイトル */
    .main-title {
        font-size: 2.5rem;
        font-weight: 800;
        letter-spacing: -0.05em;
        background: linear-gradient(90deg, #58a6ff, #ff7b72);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    /* カード装飾 */
    .res-card {
        background: #161b22;
        padding: 1.5rem;
        border-radius: 12px;
        border: 1px solid #30363d;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        margin-bottom: 1rem;
    }
    /* ボタンのカスタマイズ */
    div.stButton > button {
        width: 100%;
        background: linear-gradient(135deg, #238636 0%, #2ea043 100%);
        color: white;
        border: none;
        padding: 0.75rem;
        font-weight: bold;
        border-radius: 8px;
        transition: 0.3s;
    }
    div.stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(46, 160, 67, 0.4);
    }
    /* サイドバー背景 */
    section[data-testid="stSidebar"] {
        background-color: #010409;
    }
    /* 生データ表示エリア */
    .raw-data-area {
        font-family: 'Courier New', monospace;
        font-size: 0.85rem;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 状態管理 ---
if 'auth' not in st.session_state: st.session_state.auth = False
if 'diagnosis' not in st.session_state: st.session_state.diagnosis = None

# --- 3. 認証機能 ---
if not st.session_state.auth:
    st.markdown("<h1 class='main-title'>INSTANT EGOGRAM</h1>", unsafe_allow_html=True)
    pw = st.text_input("Access Password", type="password")
    if st.button("Authenticate"):
        if pw == "okok":
            st.session_state.auth = True
            st.rerun()
    st.stop()

# --- 4. 解析エンジン (独立サンプリング方式) ---
def get_single_analysis(text, gender, age, client):
    model_id = "gemini-2.5-flash" 
    prompt_content = f"""
    属性: {age}、{gender}。対象文章: '{text}'
    エゴグラム(CP,NP,A,FC,AC)を-10〜10で算出し性格診断せよ。
    必ずJSON形式のみで回答: {{"scores": {{"CP":0, "NP":0, "A":0, "FC":0, "AC":0}}, "性格類型": "...", "特徴": "...", "適職": "...", "恋愛のアドバイス": "..."}}
    """
    try:
        response = client.models.generate_content(
            model=model_id,
            contents=prompt_content,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.2 
            )
        )
        return json.loads(re.search(r'(\{.*\})', response.text.strip(), re.DOTALL).group(1))
    except:
        return None

def run_full_diagnosis(text, gender, age):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key: return None
    client = genai.Client(api_key=api_key)
    
    all_results = []
    progress_text = "Analyzing deep psychology..."
    my_bar = st.progress(0, text=progress_text)
    
    for i in range(ANALYSIS_TRIALS):
        res = get_single_analysis(text, gender, age, client)
        if res:
            all_results.append(res)
        my_bar.progress((i + 1) / ANALYSIS_TRIALS, text=f"Processing analysis {i+1}/{ANALYSIS_TRIALS}...")
        time.sleep(0.1)
    
    my_bar.empty()
    if not all_results: return None

    final_scores = {}
    confidences = {}
    raw_scores_list = [r["scores"] for r in all_results]
    
    for key in ["CP", "NP", "A", "FC", "AC"]:
        vals = [int(round(float(s.get(key, 0)))) for s in raw_scores_list]
        modes = statistics.multimode(vals)
        mode_val = statistics.mean(modes)
        final_scores[key] = round(mode_val, 2)
        count_mode = vals.count(int(round(mode_val)))
        confidences[key] = (count_mode / ANALYSIS_TRIALS) * 100

    base_res = all_results[0]
    return {
        "scores": final_scores,
        "confidences": confidences,
        "raw_samples": raw_scores_list,
        "性格類型": base_res.get("性格類型", "分析中"),
        "特徴": base_res.get("特徴", ""),
        "適職": base_res.get("適職", ""),
        "恋愛のアドバイス": base_res.get("恋愛のアドバイス", "")
    }

# --- 5. UIレイアウト ---
st.markdown("<h1 class='main-title'>INSTANT EGOGRAM PRO</h1>", unsafe_allow_html=True)
st.caption(f"Precision Analysis Engine | Trials: {ANALYSIS_TRIALS}")

with st.sidebar:
    st.markdown("### 👤 User Profile")
    gender = st.selectbox("性別", ["男性", "女性", "その他"], index=1)
    age = st.selectbox("年齢", ["10代", "20代", "30代", "40代", "50代", "60代", "70代以上"], index=2)
    st.divider()
    st.info("このAI診断は文章のトーンから深層心理の『揺らぎ』を統計的に算出します。")

input_text = st.text_area("解析文章を入力（SNS、自己紹介、セリフなど）", height=220, placeholder="ここに文章を入力してください...")

if st.button("🚀 診断プロファイルを開始"):
    if input_text:
        result = run_full_diagnosis(input_text, gender, age)
        if result:
            st.session_state.diagnosis = result
            st.rerun()
    else:
        st.warning("文章を入力してください。")

# --- 6. 診断結果の表示 ---
if st.session_state.diagnosis:
    res = st.session_state.diagnosis
    
    col1, col2 = st.columns([1.2, 1])
    
    with col1:
        st.markdown("<div class='res-card'>", unsafe_allow_html=True)
        st.subheader("📊 心理特性プロファイル")
        
        df = pd.DataFrame(list(res["scores"].items()), columns=['項目', '値'])
        fig = go.Figure()
        # 棒グラフ
        fig.add_trace(go.Bar(
            x=df['項目'], y=df['値'],
            marker_color='rgba(88, 166, 255, 0.3)',
            marker_line_color='#58a6ff',
            marker_line_width=2,
            name='Score'
        ))
        # 折れ線
        fig.add_trace(go.Scatter(
            x=df['項目'], y=df['値'],
            mode='lines+markers',
            line=dict(color='#ff7b72', width=4),
            marker=dict(size=10, color='#ff7b72', line=dict(color='white', width=2)),
            name='Vector'
        ))
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color="#c9d1d9"),
            yaxis=dict(range=[-10.5, 10.5], zeroline=True, zerolinecolor='#30363d', gridcolor='#30363d'),
            xaxis=dict(gridcolor='#30363d'),
            height=400, margin=dict(l=0, r=0, t=20, b=0),
            showlegend=False
        )
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
            <div class='res-card'>
                <h2 style='color: #ff7b72; margin-top:0;'>🏆 {res['性格類型']}</h2>
                <p style='font-size: 0.95rem; line-height: 1.6;'>{res['特徴']}</p>
            </div>
        """, unsafe_allow_html=True)
        
        with st.container():
            st.markdown("<div class='res-card'>", unsafe_allow_html=True)
            t1, t2 = st.tabs(["💼 適職", "❤️ 恋愛"])
            t1.write(res['適職'])
            t2.write(res['恋愛のアドバイス'])
            st.markdown("</div>", unsafe_allow_html=True)

    # 信頼性と生データの表示（デザインを統一）
    st.markdown("<div class='res-card'>", unsafe_allow_html=True)
    c1, c2 = st.columns([1, 1.5])
    with c1:
        st.markdown("#### 🎯 解析確信度")
        if ANALYSIS_TRIALS > 1:
            for key, conf in res["confidences"].items():
                st.write(f"{key}: {conf:.0f}%")
                st.progress(conf / 100)
        else:
            st.caption("※現在シングル試行モードのため、確信度は100%と表示されます。")
    
    with c2:
        st.markdown("#### 🔍 原数値（Raw Data）")
        st.markdown("<div class='raw-data-area'>", unsafe_allow_html=True)
        st.table(pd.DataFrame(res["raw_samples"]))
        st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    if st.button("🔄 新しい文章を解析する"):
        st.session_state.diagnosis = None
        st.rerun()