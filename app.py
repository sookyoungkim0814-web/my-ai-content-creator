import streamlit as st
import google.generativeai as genai
import re
from sqlalchemy import create_engine, text
from pypdf import PdfReader  # PDF 파일 읽기용 라이브러리 추가

# ==========================================================
# 0. DATABASE_URL 기반 Supabase PostgreSQL 연동
# ==========================================================
DATABASE_URL = st.secrets.get("DATABASE_URL", "")

# postgresql:// 주소를 psycopg2 드라이버 명시 형태로 자동 변환 (DB 연결 오류 해결)
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

# 텍스트 내 들여쓰기 공백 제거 함수 (코드 블록 방지용)
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
st.caption("하나의 정보로 네이버 블로그, 인스타그램 피드, 인스타그램 릴스 원고를 동시에 생성합니다.")

# ----------------------------------------------------------
# 🔑 API Key 불러오기 (Secrets 1순위)
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
SYSTEM_PROMPT = """
당신은 SNS 콘텐츠 전문 마케팅 카피라이터입니다. 
제공된 정보를 바탕으로 아래 3가지 플랫폼에 최적화된 원고를 일괄 작성해주세요.

[💥 최우선 절대 지침]
1. 각 플랫폼 원고 "내부"에는 어떠한 형태의 구분선(---, ***, ===, ___ 등)도 절대 사용하지 마세요. 
2. 문단 맨 앞에 들여쓰기(공백/탭)를 넣지 마세요. 바로 글자를 시작해 주세요.

1. **네이버 블로그**:
   - 모바일 화면 가독성을 극대화하기 위해 한 줄당 15~25자 내외로 짧게 끊어서 자주 줄바꿈(엔터)을 하고, 전체적인 문장이 모바일에서 가운데로 모이는 듯한 깔끔하고 감성적인 배열 느낌으로 작성
   - 글 최상단 시작 부분에 다정한 첫인사(예: 안녕하세요!)와 소개할 내용에 대한 간략한 요약 포함
   - 이목을 사로잡는 매력적인 제목 작성
   - 숫자 소제목(이모지 필수 포함 및 BOLD **소제목**)으로 내용 구조화
   - 친근하고 다정한 말투(~했어요 등)와 어울리는 이모지(😊, ✨, 💡, 💖 등) 풍부하게 사용
   - 본론 시작 직전에 구매 및 사용 꿀팁을 바로 배치하고, 요약/정리는 불렛(•)으로 작성
   - 모바일 가독성을 위해 핵심 위주로 공백 제외 1,250~1,500자 이내로 간결하게 작성
   - 경험 위주의 리얼한 정보성 내용 작성
   - 글 마지막에 요약 및 맺음말을 적고, 그 아래에 다정한 인삿말(예: 오늘도 행복한 하루 보내세요! 💖)을 반드시 포함

2. **인스타그램 피드**:
   - 가독성 높은 감성적/소통형 캡션, 불렛 등 이모지를 통한 줄바꿈 활용, 적절한 이모지
   - 하단에 관련 인기 태그(#) 15~20개 포함

3. **인스타그램 릴스**:
   - 15~30초 숏폼 영상 대본 형식으로 [시각 자료 / 자막 / 나레이션] 구조를 명확히 포함하여 상세하게 작성

응답은 반드시 아래 3개 구분 태그를 정확히 사용하여 출력하세요:

[네이버 블로그]
(원고 내용)

[인스타그램 피드]
(원고 내용)

[인스타그램 릴스]
(원고 내용)
"""

# ==========================================================
# 3. 메인 탭 구성
# ==========================================================
main_tab1, main_tab2 = st.tabs(["✍️ 원고 생성 및 결과", "📚 저장된 원고 관리"])

# ----------------------------------------------------------
# [MAIN TAB 1] 원고 생성 및 결과
# ----------------------------------------------------------
with main_tab1:
    left_col, right_col = st.columns([1, 1], gap="large")

    # ----- [LEFT COLUMN] 정보 입력 -----
    with left_col:
        st.subheader("📝 정보 입력 및 관리")
        
        col_reset, _ = st.columns([4, 6])
        with col_reset:
            st.button("🔄 전체 초기화", on_click=reset_inputs_only, use_container_width=True)

        uploaded_files = st.file_uploader(
            "📷 참고 이미지 / 동영상 / PDF 문서 업로드 (선택)", 
            type=["jpg", "jpeg", "png", "mp4", "mov", "pdf"], 
            accept_multiple_files=True,
            key=f"file_uploader_{st.session_state.file_uploader_key}"
        )

        product_name = st.text_input("제품/장소/주제 이름", key="product_name", placeholder="예: 줄즈 에어2 휴대용 유모차")
        main_features = st.text_area("주요 특징 및 장점 (줄바꿈 구분)", key="main_features", height=150, placeholder="예:\n- 한 손 한방 폴딩 및 기내 반입 가능\n- 매끄러운 핸들링과 서스펜션")
        extra_info = st.text_area("추가 정보 (가격, 구매처 등)", key="extra_info", height=100, placeholder="예: 베이비하우스 내돈내산, 모바일 온누리 10% 할인")

        if st.button("🚀 3개 플랫폼 원고 생성하기", type="primary", use_container_width=True):
            if not final_api_key:
                st.error("API Key를 확인해주세요.")
            elif not product_name or not main_features:
                st.warning("제품 이름과 주요 특징을 입력해주세요.")
            else:
                with st.spinner("AI가 3개 플랫폼 원고를 생성 중입니다..."):
                    try:
                        model = genai.GenerativeModel("gemini-3.8-flash")
                        user_prompt = f"- 제품/주제: {product_name}\n- 주요 특징: {main_features}\n- 추가 정보: {extra_info}"
                        
                        contents = [SYSTEM_PROMPT, user_prompt]
                        
                        if uploaded_files:
                            for file in uploaded_files:
                                if file.type == "application/pdf":
                                    try:
                                        pdf_reader = PdfReader(file)
                                        extracted_text = ""
                                        for page in pdf_reader.pages:
                                            extracted_text += page.extract_text() or ""
                                        contents.append(f"\n[첨부 PDF 문서 내용 ({file.name})]:\n{extracted_text}")
                                    except Exception as e:
                                        st.warning(f"⚠️ {file.name} PDF 읽기 실패: {e}")
                                else:
                                    contents.append({"mime_type": file.type, "data": file.read()})
                        
                        response = model.generate_content(contents)
                        st.session_state.generated_contents = response.text
                    except Exception as e:
                        err_msg = str(e)
                        if "API_KEY_INVALID" in err_msg or "API key not valid" in err_msg:
                            st.error("❌ 유효하지 않은 Gemini API Key입니다. 올바른 키를 입력해 주세요.")
                        elif "ResourceExhausted" in err_msg or "429" in err_msg:
                            st.error("⚠️ API 사용량 한도(Quota/Rate Limit)를 초과했습니다. 잠시 후 다시 시도해 주세요.")
                        else:
                            st.error(f"❌ 원고 생성 중 오류가 발생했습니다: {e}")

        if st.session_state.generated_contents:
            st.markdown("---")
            st.subheader("🔧 원고 보완 요청")
            feedback = st.text_area("수정하고 싶은 내용을 입력하세요", key="feedback_text", placeholder="예: 블로그 원고에 사진 가이드를 더 추가해줘.")
            
            if st.button("🔄 보완점 반영 재생성", use_container_width=True):
                if not feedback:
                    st.warning("보완할 내용을 입력해주세요.")
                else:
                    with st.spinner("피드백을 반영하여 다시 작성 중입니다..."):
                        try:
                            model = genai.GenerativeModel("gemini-3.8-flash")
                            refine_prompt = f"이전 원고:\n{st.session_state.generated_contents}\n\n피드백:\n{feedback}\n\n위 피드백 3개 플랫폼 모두에 반영해서 다시 작성해주세요."
                            response = model.generate_content([SYSTEM_PROMPT, refine_prompt])
                            st.session_state.generated_contents = response.text
                            st.rerun()
                        except Exception as e:
                            err_msg = str(e)
                            if "API_KEY_INVALID" in err_msg or "API key not valid" in err_msg:
                                st.error("❌ 유효하지 않은 Gemini API Key입니다. 올바른 키를 입력해 주세요.")
                            elif "ResourceExhausted" in err_msg or "429" in err_msg:
                                st.error("⚠️ API 사용량 한도(Quota/Rate Limit)를 초과했습니다. 잠시 후 다시 시도해 주세요.")
                            else:
                                st.error(f"❌ 원고 생성 중 오류가 발생했습니다: {e}")

    # ----- [RIGHT COLUMN] 결과 출력 -----
    with right_col:
        st.subheader("📄 생성된 원고 결과")
        
        if st.session_state.generated_contents:
            raw_text = st.session_state.generated_contents
            platforms = ["네이버 블로그", "인스타그램 피드", "인스타그램 릴스"]
            parsed_contents = {}
            
            for i, platform in enumerate(platforms):
                if i < len(platforms) - 1:
                    next_platforms = platforms[i+1:]
                    next_pattern = "|".join([rf"\[{re.escape(p)}\]" for p in next_platforms])
                    pattern = rf"\[{re.escape(platform)}\]\s*(.*?)(?={next_pattern}|\Z)"
                else:
                    pattern = rf"\[{re.escape(platform)}\]\s*(.*)"
                
                match = re.search(pattern, raw_text, re.DOTALL)
                
                if match:
                    content = match.group(1).strip()
                    content = re.sub(r'^[ \t]*[-*_]{3,}[ \t]*$', '', content, flags=re.MULTILINE)
                    content = clean_markdown_indent(content)
                    parsed_contents[platform] = content.strip()
                else:
                    parsed_contents[platform] = "생성된 내용이 없습니다."

            clean_full_content = ""
            for idx, platform in enumerate(platforms):
                clean_full_content += f"[{platform}]\n{parsed_contents[platform]}\n"
                if idx < len(platforms) - 1:
                    clean_full_content += "\n----------------------------------------\n\n"

            if st.button("💾 원고 저장하기", use_container_width=True):
                p_name = product_name if product_name else "무제"
                if save_history_to_db(p_name, clean_full_content):
                    st.session_state.saved_history = load_history_from_db()
                    st.success("Supabase PostgreSQL DB에 안전하게 저장되었습니다!")

            st.markdown("---")

            result_tabs = st.tabs(["📋 전체 원고"] + [f"📌 {p}" for p in platforms])
            
            with result_tabs[0]:
                for idx, platform in enumerate(platforms):
                    st.markdown(f"## 📌 {platform}")
                    st.markdown(parsed_contents[platform])
                    if idx < len(platforms) - 1:
                        st.markdown("---")
            
            for i, platform in enumerate(platforms):
                with result_tabs[i+1]:
                    st.caption(f"우측 상단의 복사 버튼(📋 아이콘)을 누르면 [{platform}] 원고가 변형 없이 복사됩니다.")
                    st.code(parsed_contents[platform], language="markdown")

        else:
            st.info("👈 왼쪽 입력창에 정보를 입력하고 원고 생성 버튼을 누르면 이 영역에 결과가 나타납니다.")

# ----------------------------------------------------------
# [MAIN TAB 2] 저장된 원고 관리 (Supabase 기반)
# ----------------------------------------------------------
with main_tab2:
    st.subheader("📚 저장된 히스토리 관리")
    
    if st.button("🔄 DB 목록 새로고침"):
        st.session_state.saved_history = load_history_from_db()
        st.rerun()

    if not st.session_state.saved_history:
        st.info("저장된 원고가 없습니다. '원고 생성 및 결과' 탭에서 원고를 만든 뒤 [💾 원고 저장하기] 버튼을 눌러보세요.")
    else:
        with st.form("history_delete_form"):
            for item in st.session_state.saved_history:
                item_id = item.get("id")
                c_chk, c_exp = st.columns([1, 15])
                with c_chk:
                    st.checkbox("", key=f"history_chk_{item_id}")
                with c_exp:
                    with st.expander(f"[{item_id}] {item.get('product_name', '무제')}"):
                        raw_history_content = item.get("content", "")
                        cleaned_history_content = clean_markdown_indent(raw_history_content)
                        st.markdown(cleaned_history_content)
            
            if st.form_submit_button("🗑️ 선택 항목 삭제", use_container_width=True):
                delete_ids = [item.get("id") for item in st.session_state.saved_history if st.session_state.get(f"history_chk_{item.get('id')}", False)]
                if not delete_ids:
                    st.warning("삭제할 항목을 선택해주세요.")
                else:
                    if delete_history_from_db(delete_ids):
                        st.session_state.saved_history = load_history_from_db()
                        st.success("선택한 원고가 DB에서 삭제되었습니다.")
                        st.rerun()
