import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from google import genai
from google.genai import types
import json
import os
import re
import statistics

# --- 1. ページ設定 ---
st.set_page_config(page_title="インスタント・エゴグラム", layout="wide")

if 'auth' not in st.session_state: st.session_state.auth = False
if 'diagnosis' not in st.session_state: st.session_state.diagnosis = None
if 'scores' not in st.session_state: st.session_state.scores = {"CP":0.0, "NP":0.0, "A":0.0, "FC":0.0, "AC":0.0}
if 'raw_samples' not in st.session_state: st.session_state.raw_samples = []

# --- 2. 認証 ---
if not st.session_state.auth:
    st.title("インスタント・エゴグラム")
    pw = st.text_input("パスワードを入力してください", type="password")
    if st.button("ログイン"):
        if pw == "okok":
            st.session_state.auth = True
            st.rerun()
    st.stop()

# --- 3. 分析エンジン (構造化出力を強化) ---
def get_batch_analysis(text, gender, age):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key: return None
    try:
        client = genai.Client(api_key=api_key)
        model_id = "gemini-2.5-flash"
        
        prompt_content = f"""
        属性: {age}、{gender}。
        以下の文章から、書き手のエゴグラム（CP, NP, A, FC, AC）を推論し、性格診断を行ってください。
        
        【重要：出力形式】
        必ず以下のJSON構造のみを返してください。
        {{
          "sampling_data": [
            {{"CP": 0, "NP": 0, "A": 0, "FC": 0, "AC": 0}},
            {{"CP": 0, "NP": 0, "A": 0, "FC": 0, "AC": 0}},
            {{"CP": 0, "NP": 0, "A": 0, "FC": 0, "AC": 0}},
            {{"CP": 0, "NP": 0, "A": 0, "FC": 0, "AC": 0}},
            {{"CP": 0, "NP": 0, "A": 0, "FC": 0, "AC": 0}}
          ],
          "性格類型": "...",
          "特徴": "...",
          "適職": "...",
          "恋愛のアドバイス": "..."
        }}
        
        【精密解析ルール】
        1. 内部で5回プロファイリングし、その全スコア（各-10〜10）を「sampling_data」に入れてください。
        2. マイナス値は「反転したエネルギー（例：NPなら冷徹、ACなら反抗心）」として解釈すること。
        
        【対象文章】
        '{text}'
        """

        response = client.models.generate_content(
            model=model_id,
            contents=prompt_content,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.7
            )
        )
        
        raw_data = json.loads(re.search(r'(\{.*\})', response.text.strip(), re.DOTALL).group(1))
        
        samples = raw_data.get("sampling_data", [])
        if not samples or len(samples) < 1: return None
        
        final_scores = {}
        for key in ["CP", "NP", "A", "FC", "AC"]:
            values = [float(s.get(key, 0)) for s in samples]
            final_scores[key] = round(statistics.mean(values), 2)
        
        return {
            "scores": final_scores,
            "raw_samples": samples,
            "性格類型": raw_data.get("性格類型", "不明"),
            "特徴": raw_data.get("特徴", ""),
            "適職": raw_data.get("適職", ""),
            "恋愛のアドバイス": raw_data.get("恋愛のアドバイス", "")
        }
    except Exception:
        return None

# --- 4. 画面レイアウト ---
st.title("⚡ インスタント・エゴグラム (高密度サンプリング版)")
st.caption("1回の通信で5層の心理プロファイリングを行い、統計的平均から個性を可視化します。")

st.sidebar.title("👤 プロフィール設定")
gender = st.sidebar.selectbox("対象の性別", ["男性", "女性", "その他", "回答しない"], index=None, placeholder="選択してください")
age = st.sidebar.selectbox("対象の年齢", ["10代", "20代", "30代", "40代", "50代", "60代", "70代以上"], index=2)

input_text = st.text_area("解析したい文章を入力してください", height=300, placeholder="ここに文章をペーストしてください...")

if st.button("🚀 精密診断を開始する"):
    if input_text:
        with st.spinner("AIが5層の心理データを一括展開中..."):
            result = get_batch_analysis(input_text, gender if gender else "未指定", age)
            if result and "scores" in result:
                st.session_state.diagnosis = result
                st.session_state.scores = result["scores"]
                st.session_state.raw_samples = result["raw_samples"]
                st.rerun()
            else:
                st.error("解析に失敗しました。文章を少し変えるか、もう一度お試しください。")
    else:
        st.warning("文章を入力してください。")

# --- 5. 結果表示 ---
if st.session_state.diagnosis:
    col1, col2 = st.columns([1, 1])
    with col1:
        st.subheader("📊 統合平均エゴグラム")
        df = pd.DataFrame(list(st.session_state.scores.items()), columns=['項目', '値'])
        fig = go.Figure()
        fig.add_trace(go.Bar(x=df['項目'], y=df['値'], marker_color='rgba(135, 206, 250, 0.4)', marker_line_color='rgba(135, 206, 250, 1)', marker_line_width=1.5))
        fig.add_trace(go.Scatter(x=df['項目'], y=df['値'], mode='lines+markers', line=dict(color='#ff4b4b', width=4), marker=dict(size=10, color='#ff4b4b')))
        fig.update_layout(yaxis=dict(range=[-10.1, 10.1], zeroline=True, zerolinewidth=2), height=450, margin=dict(l=10, r=10, t=10, b=10), showlegend=False, plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig, width="stretch")

    with col2:
        res = st.session_state.diagnosis
        st.success(f"### 🏆 {res.get('性格類型', '診断結果')}")
        st.write(f"**【特徴：5層統合プロファイリング】**\n{res.get('特徴', '')}")
        st.write(f"**【適職】**\n{res.get('適職', '')}")
        st.write(f"**【恋愛のアドバイス】**\n{res.get('恋愛のアドバイス', '')}")
        
    st.divider()
    
    with st.expander("🔍 解析の根拠（5回分の詳細スコア）"):
        if st.session_state.raw_samples:
            sample_df = pd.DataFrame(st.session_state.raw_samples)
            sample_df.index = [f"試行 {i+1}" for i in range(len(sample_df))]
            st.table(sample_df)
            st.caption("※これら5つの推論結果を統計的に統合しています。")

    if st.button("🔄 新しい診断を行う"):
        st.session_state.diagnosis = None
        st.session_state.raw_samples = []
        st.rerun()