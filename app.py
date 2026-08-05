import streamlit as st
import google.generativeai as genai
import re

# ==========================================================
# 1. 페이지 기본 설정 및 초기 커스텀 CSS (나눔고딕 15px & 겹침 버그 수정)
# ==========================================================
st.set_page_config(page_title="멀티 플랫폼 AI 원고 생성기", layout="wide")

# 초기에 설정했던 나눔고딕 15px 스타일 복원 (버그 발생 요소 제외 지정)
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Nanum+Gothic:wght@400;700;800&display=swap');
    
    /* 전체 폰트 적용 */
    html, body, [class*="css"], [class*="st-"] {
        font-family: 'Nanum Gothic', sans-serif !important;
    }
    
    /* 본문, 입력창, 버튼 폰트 크기 15px 고정 */
    p, span, div, input, textarea, button, label {
        font-size: 15px !important;
    }

    /* 겹침 버그 방지: 파일 업로더 내 특정 버튼 크기 예외 처리 */
    [data-testid="stFileUploader"] button p {
        font-size: 13px !important;
    }
    
    /* 탭 및 코드 복사 창 가독성 강화 (글자 크기 15px, 줄간격 쾌적하게) */
    .stCodeBlock code, .stCodeBlock div {
        font-size: 15px !important;
        line-height: 1.7 !important;
        font-family: 'Nanum Gothic', monospace !important;
    }

    /* 소제목 및 강조 텍스트 BOLD 스타일 */
    .blog-subtitle {
        font-weight: 700 !important;
        font-size: 17px !important;
        margin-top: 15px;
        margin-bottom: 5px;
    }
    </style>
""", unsafe_allow_html=True)

st.title("📱 멀티 플랫폼 AI 원고 생성기")
st.caption("하나의 정보로 네이버 블로그, 인스타 피드/캐러셀/릴스·숏츠, 오늘의집 피드 원고를 동시에 생성합니다.")

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

# 세션 상태 초기화
if "generated_contents" not in st.session_state:
    st.session_state.generated_contents = None
if "saved_history" not in st.session_state:
    st.session_state.saved_history = []

def reset_all():
    st.session_state.product_name = ""
    st.session_state.main_features = ""
    st.session_state.extra_info = ""
    st.session_state.feedback_text = ""
    st.session_state.generated_contents = None

# ==========================================================
# 2. 프롬프트 시스템 설정
# ==========================================================
SYSTEM_PROMPT = """
당신은 SNS 콘텐츠 전문 마케팅 카피라이터입니다. 
제공된 정보를 바탕으로 아래 5가지 플랫폼에 최적화된 원고를 일괄 작성해주세요.

1. **네이버 블로그**:
   - 친근하고 정성스러운 실제 사용 후기 어조 ('~했어요', '~입니다', 이모지 적절히 활용)
   - 숫자 소제목(이모지 활용 및 BOLD **소제목**)으로 구조화
   - 각 내용 중 추천 사진 가이드 작성 (예: 📷 [추천 사진: 한 손으로 폴딩하는 컷])
   - 검색 노출 및 가독성을 높이기 위한 정돈된 문단 구성
   - 경험 위주로 내용 작성 (단순 제품 소개 시 경험 억지 작성 금지)
   - 공백 제외 글자수 1,000자~1,500자 분량

2. **인스타그램 피드**:
   - 가독성 높은 감성적/소통형 캡션, 줄바꿈 활용, 적절한 이모지
   - 하단에 관련 인기 태그(#) 15~20개 포함

3. **인스타그램 캐러셀 (카드뉴스)**:
   - 슬라이드별(5장~10장) 구성안 제공 (슬라이드 1: 타이틀 / 2~9: 장점 요약 / 마지막: CTA)

4. **인스타그램 릴스 / 숏츠**:
   - 15~30초 숏폼 영상 대본 ([시각 자료 / 자막 / 나레이션])

5. **오늘의집 피드**:
   - 감성적인 리빙/육아 라이프스타일 톤앤매너, 공간/스타일/사용성 위주, 브랜드 및 해시태그 포함

응답은 반드시 아래 구분을 정확히 지켜서 출력하세요:
---
[네이버 블로그]
(원고 내용)

[인스타그램 피드]
(원고 내용)

[인스타그램 캐러셀]
(원고 내용)

[인스타그램 릴스/숏츠]
(원고 내용)

[오늘의집 피드]
(원고 내용)
---
"""

# ==========================================================
# 3. 화면 2분할 (왼쪽: 입력창 / 오른쪽: 결과물)
# ==========================================================
left_col, right_col = st.columns([1, 1], gap="large")

# ----------------------------------------------------------
# [LEFT COLUMN] 입력 영역
# ----------------------------------------------------------
with left_col:
    st.subheader("📝 정보 입력 및 관리")
    
    col_reset, _ = st.columns([4, 6])
    with col_reset:
        st.button("🔄 전체 초기화", on_click=reset_all, use_container_width=True)

    uploaded_files = st.file_uploader(
        "📷 참고 이미지 / 동영상 업로드 (선택)", 
        type=["jpg", "jpeg", "png", "mp4", "mov"], 
        accept_multiple_files=True
    )

    product_name = st.text_input("제품/장소/주제 이름", key="product_name", placeholder="예: 줄즈 에어2 휴대용 유모차")
    main_features = st.text_area("주요 특징 및 장점 (줄바꿈 구분)", key="main_features", height=150, placeholder="예:\n- 한 손 한방 폴딩 및 기내 반입 가능\n- 매끄러운 핸들링과 서스펜션")
    extra_info = st.text_area("추가 정보 (가격, 구매처 등)", key="extra_info", height=100, placeholder="예: 베이비하우스 내돈내산, 모바일 온누리 10% 할인")

    if st.button("🚀 5개 플랫폼 원고 생성하기", type="primary", use_container_width=True):
        if not final_api_key:
            st.error("API Key를 확인해주세요.")
        elif not product_name or not main_features:
            st.warning("제품 이름과 주요 특징을 입력해주세요.")
        else:
            with st.spinner("AI가 5개 플랫폼 원고를 생성 중입니다..."):
                model = genai.GenerativeModel("gemini-3.6-flash")
                user_prompt = f"- 제품/주제: {product_name}\n- 주요 특징: {main_features}\n- 추가 정보: {extra_info}"
                
                contents = [SYSTEM_PROMPT, user_prompt]
                if uploaded_files:
                    for file in uploaded_files:
                        contents.append({"mime_type": file.type, "data": file.read()})
                
                response = model.generate_content(contents)
                st.session_state.generated_contents = response.text

    # 보완 및 재생성 섹션
    if st.session_state.generated_contents:
        st.markdown("---")
        st.subheader("🔧 원고 보완 요청")
        feedback = st.text_area("수정하고 싶은 내용을 입력하세요", key="feedback_text", placeholder="예: 블로그 원고에 사진 가이드를 더 추가해줘.")
        
        if st.button("🔄 보완점 반영 재생성", use_container_width=True):
            if not feedback:
                st.warning("보완할 내용을 입력해주세요.")
            else:
                with st.spinner("피드백을 반영하여 다시 작성 중입니다..."):
                    model = genai.GenerativeModel("gemini-3.6-flash")
                    refine_prompt = f"이전 원고:\n{st.session_state.generated_contents}\n\n피드백:\n{feedback}\n\n위 피드백을 반영해서 다시 작성해주세요."
                    response = model.generate_content([SYSTEM_PROMPT, refine_prompt])
                    st.session_state.generated_contents = response.text
                    st.rerun()

    # 히스토리 목록
    st.markdown("---")
    st.subheader("📚 저장된 히스토리")
    if not st.session_state.saved_history:
        st.info("저장된 원고가 없습니다.")
    else:
        with st.form("history_delete_form"):
            delete_indices = []
            for idx, item in enumerate(st.session_state.saved_history):
                c_chk, c_exp = st.columns([1, 11])
                with c_chk:
                    if st.checkbox("", key=f"chk_{idx}"):
                        delete_indices.append(idx)
                with c_exp:
                    with st.expander(f"[{idx+1}] {item['product_name']}"):
                        st.code(item['content'], language="markdown")
            
            if st.form_submit_button("🗑️ 선택 삭제"):
                for i in sorted(delete_indices, reverse=True):
                    del st.session_state.saved_history[i]
                st.rerun()

# ----------------------------------------------------------
# [RIGHT COLUMN] 결과물 출력 영역
# ----------------------------------------------------------
with right_col:
    st.subheader("📄 생성된 원고 결과")
    
    if st.session_state.generated_contents:
        # 히스토리 저장 버튼
        if st.button("💾 원고 저장하기", use_container_width=True):
            st.session_state.saved_history.append({
                "product_name": product_name if product_name else "무제",
                "content": st.session_state.generated_contents
            })
            st.success("히스토리에 저장되었습니다!")

        st.markdown("---")
        
        # 플랫폼별 텍스트 파싱
        raw_text = st.session_state.generated_contents
        platforms = ["네이버 블로그", "인스타그램 피드", "인스타그램 캐러셀", "인스타그램 릴스/숏츠", "오늘의집 피드"]
        parsed_contents = {}
        
        for platform in platforms:
            pattern = rf"\[{platform}\](.*?)(?=\[\w+|\Z)"
            match = re.search(pattern, raw_text, re.DOTALL)
            parsed_contents[platform] = match.group(1).strip() if match else "생성된 내용이 없습니다."

        # 탭 형태로 플랫폼별 원고 출력 (복사 버튼 내장)
        tabs = st.tabs([f"📌 {p}" for p in platforms])
        
        for i, platform in enumerate(platforms):
            with tabs[i]:
                st.caption("우측 상단의 복사 버튼(📋 아이콘)을 누르면 원고 전체가 복사됩니다.")
                st.code(parsed_contents[platform], language="markdown")

    else:
        st.info("👈 왼쪽 입력창에 정보를 입력하고 원고 생성 버튼을 누르면 이 영역에 결과가 나타납니다.")
