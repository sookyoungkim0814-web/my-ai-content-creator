import os
import sqlite3
import pandas as pd
import psycopg2
import streamlit as st
import google.generativeai as genai

# ----------------------------------------------------
# 1. 페이지 기본 설정 및 디자인
# ----------------------------------------------------
st.set_page_config(page_title="AI 콘텐츠 크리에이터", page_icon="✍️", layout="wide")

st.markdown("""
<style>
    .main { padding: 2rem; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #FF4B4B; color: white; }
    .stDownloadButton>button { width: 100%; border-radius: 5px; }
</style>
""", unsafe_allow_html=True)

# ----------------------------------------------------
# 2. 데이터베이스 연결 함수 (psycopg2 직접 연결)
# ----------------------------------------------------
def get_db_connection():
    # Streamlit Secrets에서 DATABASE_URL 가져오기
    if "DATABASE_URL" in st.secrets:
        db_url = st.secrets["DATABASE_URL"]
        return psycopg2.connect(db_url)
    else:
        # 로컬 테스트용 SQLite 백업 (Secrets가 없을 경우)
        return sqlite3.connect("local_history.db")

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    # PostgreSQL과 SQLite 공용 테이블 생성 쿼리
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS history (
            id SERIAL PRIMARY KEY,
            topic TEXT,
            target TEXT,
            platform TEXT,
            tone TEXT,
            content TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    cursor.close()
    conn.close()

# DB 초기화 실행
try:
    init_db()
except Exception as e:
    # SERIAL 구문이 SQLite에서 에러날 경우 백업 예외 처리
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic TEXT,
                target TEXT,
                platform TEXT,
                tone TEXT,
                content TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as inner_e:
        st.error(f"DB 초기화 실패: {inner_e}")

def save_to_history(topic, target, platform, tone, content):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO history (topic, target, platform, tone, content) VALUES (%s, %s, %s, %s, %s)",
            (topic, target, platform, tone, content)
        )
        conn.commit()
        cursor.close()
        conn.close()
    except Exception:
        # SQLite일 경우 파라미터 바인딩 방식(%s -> ?)
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO history (topic, target, platform, tone, content) VALUES (?, ?, ?, ?, ?)",
                (topic, target, platform, tone, content)
            )
            conn.commit()
            cursor.close()
            conn.close()
        except Exception as e:
            st.warning(f"히스토리 저장 중 오류 발생: {e}")

def get_history():
    try:
        conn = get_db_connection()
        df = pd.read_sql("SELECT * FROM history ORDER BY created_at DESC", conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"히스토리 불러오기 실패: {e}")
        return pd.DataFrame()

# ----------------------------------------------------
# 3. Gemini API 설정
# ----------------------------------------------------
api_key = st.secrets.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

def generate_content(topic, target, platform, tone):
    prompt = f"""
    당신은 전문 콘텐츠 크리에이터입니다. 아래 조건에 맞는 고품질 콘텐츠를 작성해주세요.

    - 주제: {topic}
    - 타겟 독자: {target}
    - 발행 플랫폼: {platform}
    - 톤앤매너: {tone}

    [작성 가이드라인]
    1. {platform}에 가장 어울리는 포맷과 정중하거나 매력적인 어조로 작성하세요.
    2. 독자의 흥미를 끌 수 있는 제목과 도입부를 작성하세요.
    3. 적절한 가독성을 위해 줄바꿈과 이모지를 활용하세요.
    4. 해시태그가 필요한 플랫폼(인스타그램, 블로그 등)이라면 하단에 유용한 해시태그를 포함하세요.
    """
    model = genai.GenerativeModel('gemini-3.6-flash')
    response = model.generate_content(prompt)
    return response.text

# ----------------------------------------------------
# 4. Streamlit UI 구성
# ----------------------------------------------------
st.title("✍️ AI 자동 콘텐츠 크리에이터")
st.caption("주제와 타겟만 입력하면 맞춤형 블로그, SNS, 이메일 원고를 생성해 드립니다.")

tab1, tab2 = st.tabs(["🚀 콘텐츠 생성", "📜 생성 히스토리"])

with tab1:
    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("📌 조건 입력")
        topic = st.text_input("주제 (Topic)", placeholder="예: 2026년 봄 트렌드 패션, 직장인 자산관리")
        target = st.text_input("타겟 독자 (Target)", placeholder="예: 2030 사회초년생, 초보 자취러")
        platform = st.selectbox("발행 플랫폼", ["네이버 블로그", "인스타그램", "링크드인", "뉴스레터/이메일", "유튜브 대본"])
        tone = st.selectbox("톤앤매너", ["친근하고 재미있는", "전문적이고 신뢰감 있는", "감성적이고 설득력 있는", "간결하고 명확한"])

        generate_btn = st.button("콘텐츠 생성하기 ✨")

    with col2:
        st.subheader("📝 생성된 원고")
        if generate_btn:
            if not api_key:
                st.error("Gemini API Key가 설정되지 않았습니다. Secrets 설정을 확인해주세요.")
            elif not topic or not target:
                st.warning("주제와 타겟 독자를 모두 입력해 주세요!")
            else:
                with st.spinner("AI가 원고를 작성하고 있습니다..."):
                    try:
                        result = generate_content(topic, target, platform, tone)
                        st.markdown(result)
                        save_to_history(topic, target, platform, tone, result)
                        st.success("원고가 성공적으로 생성되고 히스토리에 저장되었습니다!")

                        st.download_button(
                            label="📄 원고 다운로드 (.txt)",
                            data=result,
                            file_name=f"{topic}_{platform}.txt",
                            mime="text/plain"
                        )
                    except Exception as e:
                        st.error(f"콘텐츠 생성 실패: {e}")

with tab2:
    st.subheader("📜 이전 생성 기록")
    if st.button("히스토리 새로고침 🔄"):
        st.rerun()

    history_df = get_history()
    if not history_df.empty:
        st.dataframe(history_df, use_container_width=True)
    else:
        st.info("아직 저장된 히스토리가 없습니다.")
