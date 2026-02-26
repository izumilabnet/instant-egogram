import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from google import genai
from google.genai import types
import json
import os
import re

# --- 1. ページ設定 ---
st.set_page_config(page_title="インスタント・エゴグラム", layout="wide")

if 'auth' not in st.session_state: st.session_state.auth = False
if 'diagnosis' not in st.session_state: st.session_state.diagnosis = None
if 'scores' not in st.session_state: st.session_state.scores = {"CP":0.0, "NP":0.0, "A":0.0, "FC":0.0, "AC":0.0}

# --- 2. 認証 ---
if not st.session_state.auth:
    st.title("インスタント・エゴグラム")
    pw = st.text_input("パスワードを入力してください", type="password")
    if st.button("ログイン"):
        if pw == "okok":
            st.session_state.auth = True
            st.rerun()
    st.stop()

# --- 3. 分析エンジン (一括診断用) ---
def get_batch_analysis(text, gender, age):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key: return None
    try:
        client = genai.Client(api_key=api_key)
        model_id = "gemini-2.5-flash"
        
        prompt_content = f"""
        属性: {age}、{gender}。
        以下の文章から、書き手のエゴグラム（CP, NP, A, FC, AC）を各-10〜10の範囲で推論し、性格診断を行ってください。
        
        【解析対象の文章】
        '{text}'
        
        【出力形式：JSON】
        1. "scores": {{"CP": 数値, "NP": 数値, "A": 数値, "FC": 数値, "AC": 数値}}
        2. "性格類型": "短いキャッチコピー"
        3. "特徴": "200字程度の詳細解説"
        4. "適職": "100字以内の箇書き"
        5. "恋愛のアドバイス": "100字以内の具体的なポイント"
        """
        
        response = client.models.generate_content(
            model=model_id,
            contents=prompt_content,
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        
        raw_text = response.text.strip()
        json_match = re.search(r'(\{.*\})', raw_text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(1))
        return None
    except Exception:
        return None

# --- 4. 画面レイアウト ---
st.title("⚡ インスタント・エゴグラム")
st.caption("文章を貼り付けるだけで、AIが深層心理を即座にプロファイリングします。")

st.sidebar.title("👤 プロフィール設定")
gender = st.sidebar.selectbox("対象の性別", ["男性", "女性", "その他", "回答しない"], index=None, placeholder="選択してください")
age = st.sidebar.selectbox("対象の年齢", ["10代", "20代", "30代", "40代", "50代", "60代", "70代以上"], index=2)

input_text = st.text_area("解析したい文章を入力してください（自己紹介文、SNSの投稿、小説のセリフなど）", height=300, placeholder="ここに文章をペーストしてください...")

if st.button("🚀 精密診断を開始する"):
    if input_text:
        with st.spinner("AIが深層心理を解析中..."):
            result = get_batch_analysis(input_text, gender if gender else "未指定", age)
            if result and "scores" in result:
                st.session_state.diagnosis = result
                st.session_state.scores = result["scores"]
                st.rerun()
            else:
                st.error("解析に失敗しました。もう一度お試しください。")
    else:
        st.warning("文章を入力してください。")

# --- 5. 結果表示 ---
if st.session_state.diagnosis:
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("📊 エゴグラム・プロファイル")
        df = pd.DataFrame(list(st.session_state.scores.items()), columns=['項目', '値'])
        
        fig = go.Figure()
        
        # 1. 棒グラフ（淡く薄い色に変更）
        fig.add_trace(go.Bar(
            x=df['項目'], 
            y=df['値'],
            name='スコア',
            marker_color='rgba(135, 206, 250, 0.4)',  # 淡い水色（透明度0.4）
            marker_line_color='rgba(135, 206, 250, 1)', # 枠線だけ少し濃く
            marker_line_width=1.5
        ))
        
        # 2. 折れ線グラフ（目立たせるために濃い色で重ね書き）
        fig.add_trace(go.Scatter(
            x=df['項目'], 
            y=df['値'],
            name='波形',
            mode='lines+markers',
            line=dict(color='#ff4b4b', width=4), # 濃い赤で強調
            marker=dict(size=10, color='#ff4b4b', symbol='circle')
        ))
        
        fig.update_layout(
            yaxis=dict(range=[-10.1, 10.1], zeroline=True, gridcolor='rgba(200, 200, 200, 0.2)'),
            xaxis=dict(gridcolor='rgba(200, 200, 200, 0.2)'),
            height=450,
            margin=dict(l=10, r=10, t=10, b=10),
            showlegend=False,
            plot_bgcolor='rgba(0,0,0,0)' # 背景を透過させてスッキリと
        )
        st.plotly_chart(fig, width="stretch")

    with col2:
        res = st.session_state.diagnosis
        st.success(f"### 🏆 {res.get('性格類型', '診断結果')}")
        st.write(f"**【特徴】**\n{res.get('特徴', '')}")
        st.write(f"**【適職】**\n{res.get('適職', '')}")
        st.write(f"**【恋愛のアドバイス】**\n{res.get('恋愛のアドバイス', '')}")
        
        if st.button("🔄 新しい診断を行う"):
            st.session_state.diagnosis = None
            st.rerun()