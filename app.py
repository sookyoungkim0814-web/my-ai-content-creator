import streamlit as st
import google.generativeai as genai

# ==========================================================
# 1. 페이지 기본 설정 및 세션 데이터 초기화
# ==========================================================
st.set_page_config(page_title="멀티 플랫폼 AI 원고 생성기", layout="wide")

st.title("📱 멀티 플랫폼 AI 원고 생성기")
st.caption("하나의 정보로 네이버 블로그, 인스타 피드/캐러셀/릴스·숏츠, 오늘의집 피드 원고를 동시에 생성합니다.")

# 사이드바 API 키 입력
api_key = st.sidebar.text_input("Gemini API Key를 입력하세요", type="password")
if api_key:
    genai.configure(api_key=api_key)

# 세션 상태 초기화
if "generated_contents" not in st.session_state:
    st.session_state.generated_contents = None
if "saved_history" not in st.session_state:
    st.session_state.saved_history = []

# 입력 및 결과 전체 초기화 함수
def reset_all():
    st.session_state.product_name = ""
    st.session_state.main_features = ""
    st.session_state.extra_info = ""
    st.session_state.feedback_text = ""
    st.session_state.generated_contents = None

# ==========================================================
# 2. 메인 입력 폼 영역
# ==========================================================
st.subheader("📝 제품 및 포스팅 정보 입력")

col_title, col_reset = st.columns([8, 2])
with col_reset:
    st.button("🔄 전체 초기화", on_click=reset_all, use_container_width=True)

# 미디어 파일 업로드
uploaded_files = st.file_uploader(
    "📷 참고 이미지 / 동영상 업로드 (선택사항)", 
    type=["jpg", "jpeg", "png", "mp4", "mov"], 
    accept_multiple_files=True
)

product_name = st.text_input("제품/장소/주제 이름", key="product_name", placeholder="예: 줄즈 에어2 휴대용 유모차")
main_features = st.text_area("주요 특징 및 장점 (줄바꿈 구분)", key="main_features", placeholder="예:\n- 한 손 한방 폴딩 및 기내 반입 가능\n- 매끄러운 핸들링과 서스펜션\n- 바구니 카시트 트래블 시스템 결합 가능")
extra_info = st.text_area("구매처, 가격, 아쉬운 점, 이벤트 등 추가 정보", key="extra_info", placeholder="예: 베이비하우스 내돈내산, 모바일 온누리상품권 10% 할인, 범퍼바 미포함 아쉬움")

# ==========================================================
# 3. 프롬프트 시스템 설정 (5개 플랫폼 세부 지침 반영)
# ==========================================================
SYSTEM_PROMPT = """
당신은 SNS 콘텐츠 전문 마케팅 카피라이터입니다. 
제공된 정보를 바탕으로 아래 5가지 플랫폼에 최적화된 원고를 일괄 작성해주세요.
각 플랫폼 고유의 작성 스타일과 톤앤매너를 완벽히 준수해야 합니다.

1. **네이버 블로그**:
   - 친근하고 정성스러운 실제 사용 후기 어조 ('~했어요', '~입니다', 이모지 적절히 활용)
   - 숫자 소제목(이모지 활용), 언박싱/구매 팁/장점/아쉬운 점/총평 등으로 구조화
   - 각 내용 중간마다 배치하면 좋을 추천 사진 가이드 작성 (예: 📷 [추천 사진: 한 손으로 유모차를 접는 연출 컷])
   - 검색 노출 및 가독성을 높이기 위한 정돈된 문단 구성
   - 사용후기의 경우 경험 위주로 작성하되, 단순 제품 소개일 경우 경험을 억지로 지어내지 말 것
   - 공백 제외 글자수 1,000자~1,500자 분량으로 풍성하게 작성

2. **인스타그램 피드**:
   - 가독성 높은 감성적/소통형 캡션
   - 줄바꿈을 적극 활용하고, 핵심 포인트를 요약하여 작성
   - 내용과 맥락에 맞는 적절한 이모지 사용
   - 하단에 관련 인기 태그(#) 15~20개 포함

3. **인스타그램 캐러셀 (카드뉴스)**:
   - 슬라이드별(5장~10장) 구성안 제공
   - 슬라이드 1: 시선을 사로잡는 타이틀/헤드카피
   - 슬라이드 2~9: 핵심 장점 및 특징 요약 (이미지 가이드 + 짧은 텍스트)
   - 슬라이드 10(마지막): 마무리 및 저장/공유 유도 행동 강령(CTA)

4. **인스타그램 릴스 / 숏츠**:
   - 15~30초 분량의 숏폼 영상 대본
   - [시각 자료 / 자막 / 나레이션(대사)] 형태로 구체적인 씬(Scene)별 구성
   - 장면과 대사가 직관적으로 보이도록 가독성 좋게 작성

5. **오늘의집 피드**:
   - 감성적이고 정돈된 리빙/육아 라이프스타일 톤앤매너
   - 공간, 스타일, 사용성 위주의 편안하고 간결한 글 구성
   - 관련 브랜드 태그 및 해시태그 포함

응답은 반드시 각 플랫폼 구분이 명확하도록 아래 출력 형식을 준수하세요:
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
# 4. 원고 생성 버튼 동작
# ==========================================================
if st.button("🚀 5개 플랫폼 원고 한 번에 생성하기", type="primary", use_container_width=True):
    if not api_key:
        st.error("API Key를 입력해주세요.")
    elif not product_name or not main_features:
        st.warning("제품 이름과 주요 특징을 입력해주세요.")
    else:
        with st.spinner("AI가 상세 가이드라인에 맞추어 5개 플랫폼 원고를 생성 중입니다..."):
            model = genai.GenerativeModel("gemini-1.5-flash")
            
            user_prompt = f"""
            - 제품/주제: {product_name}
            - 주요 특징: {main_features}
            - 추가 정보: {extra_info}
            """
            
            contents = [SYSTEM_PROMPT, user_prompt]
            if uploaded_files:
                for file in uploaded_files:
                    bytes_data = file.read()
                    contents.append({"mime_type": file.type, "data": bytes_data})
            
            response = model.generate_content(contents)
            st.session_state.generated_contents = response.text

# ==========================================================
# 5. 생성 결과 출력, 저장, 보완 및 재생성 영역
# ==========================================================
if st.session_state.generated_contents:
    st.markdown("---")
    st.subheader("📄 생성된 원고 결과")

    # 전체 원고 복사용 Textarea
    st.text_area("전체 원고 복사용 (선택 후 Ctrl+C)", value=st.session_state.generated_contents, height=350)
    
    # 수동 저장 버튼 (클릭 시에만 저장)
    col_save, _ = st.columns([3, 7])
    with col_save:
        if st.button("💾 이 원고를 히스토리에 저장하기", use_container_width=True):
            st.session_state.saved_history.append({
                "product_name": product_name if product_name else "무제",
                "content": st.session_state.generated_contents
            })
            st.success("원고가 히스토리에 성공적으로 저장되었습니다!")

    st.markdown("---")
    
    # 피드백 반영 및 재생성
    st.subheader("🔧 원고 보완 및 재생성")
    feedback = st.text_area("보완하고 싶은 내용을 입력하세요", key="feedback_text", placeholder="예: 네이버 블로그에 사진 추천 위치를 더 추가해주고, 인스타 릴스 대본 씬을 더 직관적으로 바꿔줘.")
    
    if st.button("🔄 보완점 반영하여 재생성하기"):
        if not feedback:
            st.warning("보완할 내용을 입력해주세요.")
        else:
            with st.spinner("피드백을 반영하여 원고를 다시 작성 중입니다..."):
                model = genai.GenerativeModel("gemini-1.5-flash")
                refine_prompt = f"""
                이전 생성 원고:
                {st.session_state.generated_contents}

                사용자 요청 보완 사항:
                {feedback}

                위 피드백을 반영하여 5개 플랫폼 원고를 다시 작성해 주세요.
                """
                response = model.generate_content([SYSTEM_PROMPT, refine_prompt])
                st.session_state.generated_contents = response.text
                st.rerun()

# ==========================================================
# 6. 저장된 원고 히스토리 및 선택 삭제 영역
# ==========================================================
st.markdown("---")
st.subheader("📚 저장된 원고 히스토리")

if not st.session_state.saved_history:
    st.info("저장된 원고가 없습니다.")
else:
    with st.form("history_delete_form"):
        delete_indices = []
        for idx, item in enumerate(st.session_state.saved_history):
            col_chk, col_exp = st.columns([1, 11])
            with col_chk:
                chk = st.checkbox("", key=f"chk_{idx}")
                if chk:
                    delete_indices.append(idx)
            with col_exp:
                with st.expander(f"[{idx+1}] {item['product_name']}"):
                    st.code(item['content'], language="markdown")
        
        btn_delete = st.form_submit_button("🗑️ 선택한 원고 삭제하기")
        if btn_delete:
            if delete_indices:
                for i in sorted(delete_indices, reverse=True):
                    del st.session_state.saved_history[i]
                st.success("선택한 원고가 삭제되었습니다.")
                st.rerun()
            else:
                st.warning("삭제할 원고를 선택해주세요.")
