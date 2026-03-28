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

# --- 0. 起動中メッセージ（読み込み完了まで表示） ---
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
    div.stButton > button:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(82, 183, 136, 0.4); }
    section[data-testid="stSidebar"] { background-color: #e8f5f1; }
    .footer { text-align: center; color: #9ca3af; font-size: 0.8rem; margin-top: 2rem; }

    /* iOS読み上げボタン専用スタイル */
    .tts-btn { background: #f0fdf4; border: 1px solid #52b788; border-radius: 8px; color: #2d6a4f; cursor: pointer; width: 100%; height: 38px; font-size: 1.1rem; transition: 0.2s; display: flex; align-items: center; justify-content: center; }
    .tts-btn:active { background: #dcfce7; }

    @media print {
        section[data-testid="stSidebar"], .stButton, header, footer, .footer { display: none !important; }
        .stApp { background-color: white !important; }
        .res-card { border: 1px solid #eee !important; box-shadow: none !important; break-inside: avoid; }
    }
    </style>
    """, unsafe_allow_html=True)

if 'auth' not in st.session_state: st.session_state.auth = False
if 'diagnosis' not in st.session_state: st.session_state.diagnosis = None
if 'partial_results' not in st.session_state: st.session_state.partial_results = []
if 'last_input_hash' not in st.session_state: st.session_state.last_input_hash = None

ANALYSIS_TRIALS = 5

# --- 2. 認証・トップページ ---
if not st.session_state.auth:
    st.markdown("<h1 class='main-title'>インスタント・エゴグラム</h1>", unsafe_allow_html=True)
    st.markdown("<p class='main-subtitle'>〜 交流分析理論に基づく自己理解ツール 〜</p>", unsafe_allow_html=True)

    col_top_1, col_top_2, col_top_3 = st.columns([1, 2, 1])
    with col_top_2:
        st.markdown("<div class='privacy-box'><p style='color: #1e3a8a; font-weight: bold; margin-bottom: 5px;'>🛡️ プライバシーへの配慮</p><p style='font-size: 0.85rem; margin: 0;'>本アプリでは、<b>氏名・メールアドレス等の個人情報の入力は一切不要</b>です。入力データも解析終了後に破棄され、サーバーに残ることはありません。</p></div>", unsafe_allow_html=True)
        st.markdown("<div class='feature-box'><div style='display: flex; justify-content: space-around; font-size: 0.85rem; color: #6d28d9;'><div>✓ 5つの自我状態<br>✓ 自律状態のバランス<br>✓ 対話の傾向</div><div>✓ 無意識のクセ<br>✓ 成長へ向けて<br>✓ 適職・恋愛</div></div></div>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #6b7280; font-size: 0.7rem; font-weight: bold; margin-bottom: 0;'>PRIVATE ACCESS</p>", unsafe_allow_html=True)
        pw = st.text_input("Password", type="password", placeholder="パスワードを入力してください", key="login_pw", label_visibility="collapsed")
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
                    <ul><li>Eric Berne氏の“交流分析”に基づき、AIが対人関係の心理パターンを自動分析します。</li><li>入力した文章に対し分析を5回行い、その中の最頻値を各自我状態に採用しています。信頼度はそのばらつきの度合いで決めています。</li><li>このアプリでは、各自我状態を「建設的(+)」「破壊的(-)」「不活性(0)」の3次元で解析し、エネルギーの量と質を同時に可視化します。</li></ul>
                    <p style='color: #1e3a8a; font-weight: bold;'>■ 使い方</p>
                    <ul>
                        <li>ログイン：パスワードを入力して分析画面へ。</li>
                        <li>属性選択：対象の性別と年齢を選択。</li>
                        <li>内容入力：文章を具体的（100〜300字）に入力。</li>
                        <li>分析実行：ボタン押下後、スキャンが開始されます。</li>
                        <li>グラフの「活動量」は表出の強さ、「適応度」は適切さを表します。</li>
                    </ul>
                    <p style='color: #b91c1c; font-weight: bold;'>■ ⚠️ 注意事項</p>
                    <ul>
                        <li>データ：個人を特定する情報の入力は控えてください。</li>
                        <li>免責：本ツールは気づきのためのもので、医学的診断ではありません。</li>
                    </ul>
                </div>
            """, unsafe_allow_html=True)

        st.divider()
        st.markdown("<div class='footer'>© 2026 PsychoGameAnalyzers（代表：和泉光則）<br>Based on Eric Berne’s Transactional Analysis</div>", unsafe_allow_html=True)
    st.stop()

# --- 3. 分析エンジン ---
def get_single_analysis(text, gender, age, client):
    model_id = "gemini-2.5-flash"
    prompt_content = f"""属性: {age}、{gender}。対象文章: '{text}' 
    エゴグラムの5つの自我状態(CP,NP,A,FC,AC)について、以下の3要素を0〜10で算出せよ。
    - P: 建設的・望ましい思考・行動（光）
    - M: 破壊的・望ましくない思考・行動（影）
    - Z: 欠乏・不活性な状態（無）
    必ずJSON形式のみで回答し、回答構成: {{"scores": {{"CP":{{"P":0,"M":0,"Z":0}}, "NP":{{"P":0,"M":0,"Z":0}}, "A":{{"P":0,"M":0,"Z":0}}, "FC":{{"P":0,"M":0,"Z":0}}, "AC":{{"P":0,"M":0,"Z":0}}}}, "性格類型": "...", "特徴": "...", "適職": "...", "恋愛のアドバイス": "...", "成長へ向けて": "..."}}"""
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
    
    current_input_hash = hash(f"{text}{gender}{age}")
    if st.session_state.last_input_hash != current_input_hash:
        st.session_state.partial_results = []
        st.session_state.last_input_hash = current_input_hash

    all_results = st.session_state.partial_results
    progress_text = st.empty()
    my_bar = st.progress(len(all_results) / ANALYSIS_TRIALS)
    
    start_count = len(all_results)
    for i in range(start_count, ANALYSIS_TRIALS):
        progress_text.markdown(f"<p style='color: #2d6a4f; font-size: 0.9rem;'>Analyzing psychological vectors... ({i+1} / {ANALYSIS_TRIALS})</p>", unsafe_allow_html=True)
        res = get_single_analysis(text, gender, age, client)
        
        if res is None:
            st.error(f"⚠️ API制限（429等）により{i+1}回目で中断しました。30秒ほど置いて、再度「診断を開始」ボタンを押してください。続きから再開します。")
            return None
            
        all_results.append(res)
        st.session_state.partial_results = all_results
        my_bar.progress((i + 1) / ANALYSIS_TRIALS)
        time.sleep(3.0)
    
    progress_text.empty()
    my_bar.empty()
    
    final_scores = {}
    confidences = {}
    for ego in ["CP", "NP", "A", "FC", "AC"]:
        ego_scores = {"P": [], "M": [], "Z": []}
        activity_vals = []
        for r in all_results:
            p_val = r["scores"].get(ego, {}).get("P", 0)
            m_val = r["scores"].get(ego, {}).get("M", 0)
            z_val = r["scores"].get(ego, {}).get("Z", 0)
            ego_scores["P"].append(p_val); ego_scores["M"].append(m_val); ego_scores["Z"].append(z_val)
            activity_vals.append(round(float(p_val + m_val)))
        
        final_scores[ego] = {
            sub: float(statistics.multimode([round(float(v)) for v in vals])[0])
            for sub, vals in ego_scores.items()
        }
        median_val = statistics.median(activity_vals)
        count_in_range = sum(1 for v in activity_vals if (median_val - 1) <= v <= (median_val + 1))
        confidences[ego] = (count_in_range / ANALYSIS_TRIALS) * 100

    base_res = all_results[0]
    st.session_state.partial_results = []
    return {
        "scores": final_scores, "confidences": confidences, "raw_samples": [r["scores"] for r in all_results],
        "性格類型": base_res.get("性格類型", ""), "特徴": base_res.get("特徴", ""),
        "適職": base_res.get("適職", ""), "恋愛のアドバイス": base_res.get("恋愛のアドバイス", ""),
        "成長へ向けて": base_res.get("成長へ向けて", ""), "input_text": text
    }

# --- 4. メイン画面 ---
st.markdown("<h1 class='main-title'>INSTANT EGOGRAM PRO</h1>", unsafe_allow_html=True)

if st.session_state.diagnosis is None:
    col_input_1, col_input_2 = st.columns(2)
    with col_input_1: gender = st.selectbox("性別", ["", "男性", "女性", "その他", "回答しない"], index=0)
    with col_input_2: age = st.selectbox("年齢", ["", "10代", "20代", "30代", "40代", "50代", "60代", "70代以上"], index=0)
    input_text = st.text_area("Analysis Text", height=200, key="main_input", label_visibility="collapsed", placeholder="分析する文章をここに入力してください")
    
    btn_label = "🚀 診断を開始" if not st.session_state.partial_results else f"🔄 診断を再開 ({len(st.session_state.partial_results)}/{ANALYSIS_TRIALS} 完了済み)"
    if st.button(btn_label, key="diag_btn"):
        if input_text:
            result = run_full_diagnosis(input_text, gender, age)
            if result:
                st.session_state.diagnosis = result
                st.rerun()
        else: st.warning("文章を入力してください。")
else:
    res = st.session_state.diagnosis
    col1, col2 = st.columns([1.2, 1])
    with col1:
        st.markdown("<div class='res-card'>", unsafe_allow_html=True)
        head_col1, head_col2 = st.columns([4, 1])
        with head_col1: st.subheader("📊 あなたのエゴグラム")
        with head_col2:
            speech_msg = f"診断結果は、{res['性格類型']}です。".replace('"', '”')
            st.components.v1.html(f"""
                <button class="tts-btn" onclick="
                    const synth = window.speechSynthesis;
                    if (synth.speaking) {{ synth.cancel(); }}
                    else {{
                        const uttr = new SpeechSynthesisUtterance('{speech_msg}');
                        uttr.lang = 'ja-JP';
                        uttr.rate = 1.0;
                        uttr.pitch = 1.0;
                        synth.speak(new SpeechSynthesisUtterance(' '));
                        synth.speak(uttr);
                    }}
                ">🔊</button>
            """, height=40)

        plot_data = [{"項目": k, "Total": v["P"] + v["M"], "Positive": v["P"], "Block": -v["Z"]} for k, v in res["scores"].items()]
        df = pd.DataFrame(plot_data)
        fig = go.Figure()
        fig.add_trace(go.Bar(x=df['項目'], y=df['Positive'], name='建設的な活用(①)', marker_color='rgba(255, 167, 38, 0.3)', marker_line_color='#ef6c00', marker_line_width=1, width=0.6))
        fig.add_trace(go.Bar(x=df['項目'], y=df['Total'], name='非建設的な活用(②)', marker_color='rgba(33, 150, 243, 0.8)', width=0.6))
        fig.add_trace(go.Scatter(x=df['項目'], y=df['Total'], name='エゴグラム波形(①+②)', mode='lines+markers', line=dict(color='#2d6a4f', width=2), marker=dict(size=8, symbol='circle')))

        fig.add_trace(go.Bar(x=df['項目'], y=df['Block'], name='不活性度(③)', marker_color='rgba(158, 158, 158, 0.5)', width=0.6))
        fig.update_layout(barmode='overlay', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color="#2c3e50"), yaxis=dict(range=[-10.5, 20.5], zeroline=True, fixedrange=True), xaxis=dict(fixedrange=True), height=450, margin=dict(l=0, r=0, t=20, b=0), showlegend=True, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1), dragmode=False)
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        
        conf_html = "".join([f"<span style='margin-right:15px;'>{k}: {v:.0f}%</span>" for k, v in res["confidences"].items()])
        st.markdown(f"<div style='font-size: 0.75rem; color: #6b7280; text-align: center; border-top: 1px solid #eee; padding-top: 8px;'>信頼度: {conf_html}</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        st.markdown(f"<div class='res-card'><h2 style='color: #2d6a4f; margin-top:0;'>🏆 {res['性格類型']}</h2><p>{res['特徴']}</p></div>", unsafe_allow_html=True)
        st.markdown("<div class='res-card'>", unsafe_allow_html=True)
        t3, t1, t2 = st.tabs(["🌱 成長へ向けて", "💼 適職", "❤️ 恋愛"])
        t3.write(res['成長へ向けて']); t1.write(res['適職']); t2.write(res['恋愛のアドバイス'])
        st.markdown("</div>", unsafe_allow_html=True)

        with st.expander("🛠️ 解析データをすべて表示"):
            row_list = []
            for i, sample in enumerate(res["raw_samples"]):
                row = {k: (sample[k]["P"] + sample[k]["M"]) for k in ["CP", "NP", "A", "FC", "AC"]}
                row_list.append(pd.Series(row, name=f"{i+1}回目"))
            st.table(pd.concat(row_list, axis=1).T)
            st.caption(f"※各自我状態における「活動量（①+②）」の独立試行データを表示しています。")

    st.markdown("<div class='res-card'><p style='font-size: 0.85rem; font-weight: bold; color: #2d6a4f; margin-bottom: 5px;'>📝 解析対象の文章</p><div style='font-size: 0.9rem; color: #4b5563; background: #f9fafb; padding: 10px; border-radius: 8px; border: 1px inset #f3f4f6;'>"+res['input_text']+"</div></div>", unsafe_allow_html=True)

    if st.button("🔄 新しい文章を解析する", key="reset_btn"):
        st.session_state.diagnosis = None
        st.session_state.partial_results = []
        st.rerun()