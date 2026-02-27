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
    .stApp { background-color: #f0f9f6; color: #2c3e50; }
    .main-title { font-size: 2.5rem; font-weight: 800; color: #2d6a4f; margin-bottom: 0.5rem; }
    .res-card { background: #ffffff; padding: 1.5rem; border-radius: 12px; border: 1px solid #d8e2dc; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 1rem; }
    div.stButton > button { width: 100%; background: linear-gradient(135deg, #52b788 0%, #40916c 100%); color: white; border: none; padding: 0.75rem; font-weight: bold; border-radius: 8px; transition: 0.3s; }
    div.stButton > button:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(82, 183, 136, 0.4); }
    section[data-testid="stSidebar"] { background-color: #e8f5f1; }
    </style>
    """, unsafe_allow_html=True)

if 'auth' not in st.session_state: st.session_state.auth = False
if 'diagnosis' not in st.session_state: st.session_state.diagnosis = None

if not st.session_state.auth:
    st.markdown("<h1 class='main-title'>INSTANT EGOGRAM</h1>", unsafe_allow_html=True)
    pw = st.text_input("Access Password", type="password")
    if st.button("Authenticate"):
        if pw == "okok":
            st.session_state.auth = True
            st.rerun()
    st.stop()

def get_single_analysis(text, gender, age, client):
    model_id = "gemini-2.5-flash" 
    prompt_content = f"""
    属性: {age}、{gender}。対象文章: '{text}'
    エゴグラム(CP,NP,A,FC,AC)を-10〜10で算出し性格診断せよ。
    必ずJSON形式のみで回答: {{
        "scores": {{"CP":0, "NP":0, "A":0, "FC":0, "AC":0}}, 
        "性格類型": "...", 
        "特徴": "...", 
        "適職": "...", 
        "恋愛のアドバイス": "...",
        "成長へ向けて": "今のこのエゴグラムがこれまでの人生で積み上げてきた大切な個性であることを肯定した上で、無理なく成長するための方向性を150字程度で"
    }}
    """
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
    my_bar = st.progress(0, text="Analyzing psychological vectors...")
    
    for i in range(ANALYSIS_TRIALS):
        res = get_single_analysis(text, gender, age, client)
        if res: all_results.append(res)
        my_bar.progress((i + 1) / ANALYSIS_TRIALS)
        time.sleep(0.1)
    
    my_bar.empty()
    if not all_results: return None

    final_scores = {}
    confidences = {}
    raw_scores_list = [r["scores"] for r in all_results]
    
    for key in ["CP", "NP", "A", "FC", "AC"]:
        vals = [int(round(float(s.get(key, 0)))) for s in raw_scores_list]
        # 最頻値を算出
        modes = statistics.multimode(vals)
        mode_val = statistics.mean(modes)
        final_scores[key] = round(mode_val, 2)
        # 信頼度計算: 最頻値（に近い値）±1の含有率
        count_in_range = sum(1 for v in vals if (mode_val - 1) <= v <= (mode_val + 1))
        confidences[key] = (count_in_range / ANALYSIS_TRIALS) * 100

    base_res = all_results[0]
    return {
        "scores": final_scores,
        "confidences": confidences,
        "raw_samples": raw_scores_list,
        "性格類型": base_res.get("性格類型", ""),
        "特徴": base_res.get("特徴", ""),
        "適職": base_res.get("適職", ""),
        "恋愛のアドバイス": base_res.get("恋愛のアドバイス", ""),
        "成長へ向けて": base_res.get("成長へ向けて", "")
    }

st.markdown("<h1 class='main-title'>INSTANT EGOGRAM PRO</h1>", unsafe_allow_html=True)
st.caption(f"Mint-Green Edition | Trials: {ANALYSIS_TRIALS}")

with st.sidebar:
    gender = st.selectbox("性別", ["男性", "女性", "その他"], index=1)
    age = st.selectbox("年齢", ["10代", "20代", "30代", "40代", "50代", "60代", "70代以上"], index=2)
    st.info("独立推論の結果から『最頻値』を特定し、その集中度を信頼度として算出します。")

input_text = st.text_area("解析文章を入力", height=200)

if st.button("🚀 診断プロファイルを開始"):
    if input_text:
        result = run_full_diagnosis(input_text, gender, age)
        if result:
            st.session_state.diagnosis = result
            st.rerun()

if st.session_state.diagnosis:
    res = st.session_state.diagnosis
    col1, col2 = st.columns([1.2, 1])
    
    with col1:
        st.markdown("<div class='res-card'>", unsafe_allow_html=True)
        st.subheader("📊 心理特性プロファイル")
        df = pd.DataFrame(list(res["scores"].items()), columns=['項目', '値'])
        fig = go.Figure()
        fig.add_trace(go.Bar(x=df['項目'], y=df['値'], marker_color='rgba(82, 183, 136, 0.3)', marker_line_color='#2d6a4f', marker_line_width=2))
        fig.add_trace(go.Scatter(x=df['項目'], y=df['値'], mode='lines+markers', line=dict(color='#ff7b72', width=4), marker=dict(size=10, color='#ff7b72')))
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color="#2c3e50"), yaxis=dict(range=[-10.5, 10.5], zeroline=True), height=400, margin=dict(l=0, r=0, t=20, b=0), showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        st.markdown(f"<div class='res-card'><h2 style='color: #2d6a4f; margin-top:0;'>🏆 {res['性格類型']}</h2><p>{res['特徴']}</p></div>", unsafe_allow_html=True)
        st.markdown("<div class='res-card'>", unsafe_allow_html=True)
        t1, t2, t3 = st.tabs(["💼 適職", "❤️ 恋愛", "🌱 成長へ向けて"])
        t1.write(res['適職']); t2.write(res['恋愛のアドバイス']); t3.write(res['成長へ向けて'])
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='res-card'>", unsafe_allow_html=True)
    c1, c2 = st.columns([1, 1.5])
    with c1:
        st.markdown("#### 🎯 解析確信度 (最頻値±1の含有率)")
        if ANALYSIS_TRIALS > 1:
            for key, conf in res["confidences"].items():
                st.write(f"**{key}**: {conf:.0f}% Match")
                st.progress(conf / 100)
        else: st.caption("※シングル試行モード")
    
    with c2:
        with st.expander("🔍 生データ（Raw Sampling Data）"):
            st.table(pd.DataFrame(res["raw_samples"]))
            st.caption("※これらの数値の『最頻値』を最終スコアとして採用しています。")
    st.markdown("</div>", unsafe_allow_html=True)

    if st.button("🔄 新しい文章を解析する"):
        st.session_state.diagnosis = None
        st.rerun()