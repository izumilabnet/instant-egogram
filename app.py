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
    .main-title { font-size: 2.5rem; font-weight: 800; color: #2d6a4f; margin-bottom: 0.5rem; text-align: center; }
    .main-subtitle { font-size: 1rem; color: #6d28d9; text-align: center; margin-bottom: 2rem; }
    .res-card { background: #ffffff; padding: 1.5rem; border-radius: 12px; border: 1px solid #d8e2dc; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 1rem; }
    .privacy-box { background-color: #eff6ff; border: 1px solid #bfdbfe; padding: 15px; border-radius: 10px; margin-bottom: 20px; }
    .feature-box { background-color: #ffffff; border: 1px solid #e5e7eb; padding: 15px; border-radius: 10px; margin-bottom: 20px; }
    div.stButton > button { width: 100%; background: linear-gradient(135deg, #52b788 0%, #40916c 100%); color: white; border: none; padding: 0.75rem; font-weight: bold; border-radius: 8px; transition: 0.3s; }
    div.stButton > button:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(82, 183, 136, 0.4); }
    section[data-testid="stSidebar"] { background-color: #e8f5f1; }
    .footer { text-align: center; color: #9ca3af; font-size: 0.8rem; margin-top: 2rem; }
    </style>
    """, unsafe_allow_html=True)

if 'auth' not in st.session_state: st.session_state.auth = False
if 'diagnosis' not in st.session_state: st.session_state.diagnosis = None

# --- 2. トップページ（認証前） ---
if not st.session_state.auth:
    st.markdown("<h1 class='main-title'>心理ゲーム・アナライザ</h1>", unsafe_allow_html=True)
    st.markdown("<p class='main-subtitle'>〜 交流分析理論に基づく深層心理の解明 〜</p>", unsafe_allow_html=True)

    col_top_1, col_top_2, col_top_3 = st.columns([1, 2, 1])
    
    with col_top_2:
        st.markdown("""
            <div class='privacy-box'>
                <p style='color: #1e3a8a; font-weight: bold; margin-bottom: 5px;'>🛡️ プライバシーへの配慮</p>
                <p style='font-size: 0.85rem; margin: 0;'>本アプリでは、<b>氏名・メールアドレス等の個人情報の入力は一切不要</b>です。入力データも解析終了後に破棄され、サーバーに残ることはありません。</p>
            </div>
        """, unsafe_allow_html=True)

        st.markdown("""
            <div class='feature-box'>
                <div style='display: flex; justify-content: space-around; font-size: 0.85rem; color: #6d28d9;'>
                    <div>✓ ゲームの特定<br>✓ OK牧場の変遷<br>✓ 具体的な対応策</div>
                    <div>✓ 無意識の利得<br>✓ 残酷な結末予測<br>✓ 心の処方箋</div>
                </div>
            </div>
        """, unsafe_allow_html=True)

        st.markdown("<p style='text-align: center; color: #6b7280; font-size: 0.7rem; font-weight: bold; margin-bottom: 0;'>PRIVATE ACCESS</p>", unsafe_allow_html=True)
        pw = st.text_input("", type="password", placeholder="パスワードを入力してください", key="login_pw")
        if st.button("分析を開始する", key="login_btn"):
            if pw == "okok":
                st.session_state.auth = True
                st.rerun()
            else:
                st.error("パスワードが正しくありません")

        with st.expander("📘 使用マニュアルを表示"):
            st.markdown("""
                <div style='font-size: 0.85rem; color: #374151;'>
                    <p style='color: #1e3a8a; font-weight: bold; margin-top: 10px;'>■ アプリの概要</p>
                    <ul><li>Eric Berne氏の“交流分析”に基づき、AIが対人関係の心理パターンを自動分析します。</li></ul>
                    <p style='color: #1e3a8a; font-weight: bold;'>■ 使い方</p>
                    <ul>
                        <li>ログイン：パスワードを入力して分析画面へ。</li>
                        <li>属性選択：対象の性別と年齢を選択。</li>
                        <li>内容入力：文章を具体的（100〜300字）に入力。</li>
                        <li>分析実行：ボタン押下後、スキャンが開始されます。</li>
                    </ul>
                    <p style='color: #b91c1c; font-weight: bold;'>■ ⚠️ 注意事項</p>
                    <ul>
                        <li>データ：個人を特定する情報の入力は控えてください。</li>
                        <li>免責：本ツールは気づきのためのもので、医学的診断ではありません。</li>
                    </ul>
                </div>
            """, unsafe_allow_html=True)

        st.divider()
        st.markdown("""
            <div class='footer'>
                <p style='color: #1e3a8a; font-weight: bold; font-size: 0.75rem; margin-bottom: 5px;'>免責事項</p>
                <p style='font-size: 0.7rem;'>AIによる分析は気づきを支援するもので、医学的診断や治療を代替しません。本ツールの利用により生じたいかなる結果についても運営者は責任を負いません。</p>
                © 2026 PsychoGameAnalyzers（代表：和泉光則）<br>
                Based on Eric Berne’s Transactional Analysis
            </div>
        """, unsafe_allow_html=True)
    st.stop()

# --- 3. 分析エンジン ---
def get_single_analysis(text, gender, age, client):
    model_id = "gemini-2.5-flash" 
    prompt_content = f"""
    属性: {age}、{gender}。対象文章: '{text}'
    エゴグラム(CP,NP,A,FC,AC)を-10〜10で算出し性格診断せよ。
    必ずJSON形式のみで回答し、余計な指示文を含めないこと。
    回答構成: {{
        "scores": {{"CP":0, "NP":0, "A":0, "FC":0, "AC":0}}, 
        "性格類型": "...", 
        "特徴": "...", 
        "適職": "...", 
        "恋愛のアドバイス": "...",
        "成長へ向けて": "今のエゴグラムが人生で積み上げた大切な個性であることを肯定する文章から始め、無理なく成長するための方向性を150字程度で具体的に記述してください"
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
        modes = statistics.multimode(vals)
        mode_val = statistics.mean(modes)
        final_scores[key] = round(mode_val, 2)
        count_in_range = sum(1 for v in vals if (mode_val - 1) <= v <= (mode_val + 1))
        confidences[key] = (count_in_range / ANALYSIS_TRIALS) * 100

    base_res = all_results[0]
    return {
        "scores": final_scores, "confidences": confidences, "raw_samples": raw_scores_list,
        "性格類型": base_res.get("性格類型", ""), "特徴": base_res.get("特徴", ""),
        "適職": base_res.get("適職", ""), "恋愛のアドバイス": base_res.get("恋愛のアドバイス", ""),
        "成長へ向けて": base_res.get("成長へ向けて", "")
    }

# --- 4. メイン画面（認証後） ---
st.markdown("<h1 class='main-title'>INSTANT EGOGRAM PRO</h1>", unsafe_allow_html=True)

if st.session_state.diagnosis is None:
    with st.sidebar:
        gender = st.selectbox("性別", ["男性", "女性", "その他"], index=1)
        age = st.selectbox("年齢", ["10代", "20代", "30代", "40代", "50代", "60代", "70代以上"], index=2)
        st.info("独立推論の結果から『最頻値』を特定し、その集中度を信頼度として算出します。")

    input_text = st.text_area("解析文章を入力", height=200, key="main_input")

    if st.button("🚀 診断プロファイルを開始", key="diag_btn"):
        if input_text:
            result = run_full_diagnosis(input_text, gender, age)
            if result:
                st.session_state.diagnosis = result
                st.rerun()
        else:
            st.warning("文章を入力してください。")
else:
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
        t3, t1, t2 = st.tabs(["🌱 成長へ向けて", "💼 適職", "❤️ 恋愛"])
        t3.write(res['成長へ向けて']); t1.write(res['適職']); t2.write(res['恋愛のアドバイス'])
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
    st.markdown("</div>", unsafe_allow_html=True)

    if st.button("🔄 新しい文章を解析する", key="reset_btn"):
        st.session_state.diagnosis = None
        st.rerun()