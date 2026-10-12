import streamlit as st
import google.generativeai as genai
import re
from sqlalchemy import create_engine, text
from pypdf import PdfReader

# ==========================================================
# 0. DATABASE_URL 기반 Supabase PostgreSQL 연동
# ==========================================================
DATABASE_URL = st.secrets.get("DATABASE_URL", "")

if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)

@st.cache_resource
def get_db_engine():
    if not DATABASE_URL:
        st.error("⚠️ Secrets에 DATABASE_URL이 설정되어 있지 않습니다.")
        return None
    try:
        engine = create_engine(
            DATABASE_URL, 
            pool_pre_ping=True,
            connect_args={
                "sslmode": "require", 
                "connect_timeout": 10
            }
        )
        with engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS history (
                    id SERIAL PRIMARY KEY,
                    content TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """))
            conn.execute(text("""
                ALTER TABLE history 
                ADD COLUMN IF NOT EXISTS product_name TEXT;
            """))
            conn.commit()
        return engine
    except Exception as e:
        st.error(f"❌ DB 연결 실패: {e}")
        return None

engine = get_db_engine()

def load_history_from_db():
    if not engine:
        return []
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT id, product_name, content FROM history ORDER BY id DESC;"))
            return [{"id": row[0], "product_name": row[1], "content": row[2]} for row in result.fetchall()]
    except Exception as e:
        st.error(f"DB 데이터 불러오기 오류: {e}")
        return []

def save_history_to_db(product_name, content):
    if not engine:
        return False
    try:
        with engine.connect() as conn:
            conn.execute(
                text("INSERT INTO history (product_name, content) VALUES (:p_name, :cnt);"),
                {"p_name": product_name, "cnt": content}
            )
            conn.commit()
        return True
    except Exception as e:
        st.error(f"DB 저장 오류: {e}")
        return False

def delete_history_from_db(item_ids):
    if not engine or not item_ids:
        return False
    try:
        with engine.connect() as conn:
            conn.execute(
                text("DELETE FROM history WHERE id = ANY(:ids);"),
                {"ids": item_ids}
            )
            conn.commit()
        return True
    except Exception as e:
        st.error(f"DB 삭제 오류: {e}")
        return False

def clean_markdown_indent(text_data):
    if not text_data:
        return ""
    lines = text_data.split("\n")
    cleaned = [line.lstrip() for line in lines]
    return "\n".join(cleaned)

# ==========================================================
# 1. 페이지 기본 설정
# ==========================================================
st.set_page_config(page_title="멀티 플랫폼 AI 원고 생성기", layout="wide")

st.title("📱 멀티 플랫폼 AI 원고 생성기")
st.caption("하나의 정보로 네이버 블로그, 인스타 피드/캐러셀/릴스·숏츠, 오늘의집 피드 원고를 동시에 생성합니다.")

# ----------------------------------------------------------
# 🔑 API Key 불러오기
# ----------------------------------------------------------
secret_api_key = st.secrets.get("GEMINI_API_KEY", "")
user_api_key = st.sidebar.text_input("Gemini API Key (Secrets 설정 시 빈칸)", type="password")
final_api_key = user_api_key if user_api_key else secret_api_key

if final_api_key:
    genai.configure(api_key=final_api_key)
    st.sidebar.success("✅ API Key가 연결되었습니다.")
else:
    st.sidebar.warning("⚠️ API Key를 확인해주세요.")

# ----------------------------------------------------------
# 세션 상태 초기화
# ----------------------------------------------------------
if "generated_contents" not in st.session_state:
    st.session_state.generated_contents = None
if "saved_history" not in st.session_state:
    st.session_state.saved_history = load_history_from_db()
if "file_uploader_key" not in st.session_state:
    st.session_state.file_uploader_key = 0

def reset_inputs_only():
    st.session_state["product_name"] = ""
    st.session_state["main_features"] = ""
    st.session_state["extra_info"] = ""
    st.session_state["feedback_text"] = ""
    st.session_state.generated_contents = None
    st.session_state.file_uploader_key += 1

# ==========================================================
# 2. 프롬프트 시스템 설정
# ==========================================================
SYSTEM_PROMPT = """당신은 SNS 콘텐츠 전문 마케팅 카피라이터입니다. 
제공된 정보를 바탕으로 아래 5가지 플랫폼에 최적화된 원고를 일괄 작성해주세요.

[💥 최우선 절대 지침]
1. 각 플랫폼 원고 "내부"에는 어떠한 형태의 구분선(---, ***, ===, ___ 등)도 절대 사용하지 마세요. 
2. 문단 맨 앞에 들여쓰기(공백/탭)를 넣지 마세요. 바로 글자를 시작해 주세요.

1. **네이버 블로그**:
   - 모바일로 보았을 때 자연스럽고 읽기 편한 띄어쓰기 및 줄바꿈 적용
   - 사람들의 관심을 불러일으키는 매력적인 제목 작성
   - 숫자 소제목(이모지 활용 및 BOLD **소제목**)으로 내용 구조화
   - 친근하고 정성스러운 말투 ('~했어요
