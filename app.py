import streamlit as st
import google.genai as genai
from PIL import Image
from datetime import datetime

st.set_page_config(page_title="멀티플랫폼 AI 콘텐츠 에이전트", layout="wide")

st.title("📸 멀티플랫폼 인플루언서 AI 콘텐츠 에이전트")
st.write("주제와 미디어(사진/동영상)를 업로드하면 각 플랫폼 감성에 맞춘 콘텐츠를 자동 생성합니다.")

# 세션 상태 초기화 (결과 저장, 히스토리 저장 목록 관리)
if "generated_result" not in st.session_state:
    st.session_state.generated_result = ""
if "last_topic" not in st.session_state:
    st.session_state.last_topic = ""
if "history" not in st.session_state:
    st.session_state.history = []  # [{ "id": ..., "date": ..., "topic": ..., "content": ... }]

# Gemini API 키 입력
api_key = st.sidebar.text_input("Google Gemini API Key 입력", type="password")

# -------------------------------------------------------------------
# 사이드바: 저장된 원고 히스토리 리스트
# -------------------------------------------------------------------
st.sidebar.markdown("---")
st.sidebar.subheader("📚 저장된 원고 목록")

if st.session_state.history:
    selected_doc_id = st.sidebar.selectbox(
        "불러올 원고를 선택하세요",
        options=[item["id"] for item in st.session_state.history],
        format_func=lambda x: next((f"[{item['date']}] {item['topic']}" for item in st.session_state.history if item["id"] == x), x)
    )
    
    col_nav1, col_nav2 = st.sidebar.columns(2)
    if col_nav1.button("📖 원고 불러오기"):
        selected_item = next((item for item in st.session_state.history if item["id"] == selected_doc_id), None)
        if selected_item:
            st.session_state.generated_result = selected_item["content"]
            st.session_state.last_topic = selected_item["topic"]
            st.rerun()

    if col_nav2.button("🗑️ 원고 삭제"):
        st.session_state.history = [item for item in st.session_state.history if item["id"] != selected_doc_id]
        st.success("원고가 삭제되었습니다.")
        st.rerun()
else:
    st.sidebar.info("아직 저장된 원고가 없습니다.")


# -------------------------------------------------------------------
# 메인화면: API 키 인증 후 동작
# -------------------------------------------------------------------
if api_key:
    client = genai.Client(api_key=api_key)

    # 1. 주제 및 미디어 업로드
    topic = st.text_input("1. 콘텐츠 주제를 입력하세요", placeholder="예: 줄즈 에어2 유모차 & 다이치 카시트 내돈내산 사용후기")
    uploaded_files = st.file_uploader("2. 사진 또는 동영상을 업로드하세요 (복수 선택 가능)", type=["jpg", "jpeg", "png", "mp4"], accept_multiple_files=True)

    # 콘텐츠 전체 생성 버튼
    if st.button("🚀 전체 플랫폼 콘텐츠 생성하기"):
        if not topic:
            st.warning("주제를 입력해주세요!")
        else:
            images = []
            if uploaded_files:
                for file in uploaded_files:
                    if file.type.startswith("image"):
                        images.append(Image.open(file))

            with st.spinner("AI가 미디어의 감성과 느낌을 분석하여 플랫폼별 맞춤 글을 작성 중입니다..."):
                prompt = f"""
                너는 인스타그램, 네이버 블로그, 숏폼(릴스/클립/숏츠), 오늘의집 등 다양한 채널을 운영하는 전문 인플루언서 에이전트야.
                제공된 사진/동영상들의 전체적인 감성, 색감, 장소, 분위기, 스타일을 세밀하게 분석하고 이를 반영해서 각 플랫폼 스타일에 맞게 글을 작성해줘.

                [주제]: {topic}

                ---
                ### 1. 인스타그램 피드
                - 인스타그램 특유의 감성적이고 친근한 톤앤매너, 적절한 이모티콘 사용
                - 본문 피드 작성 후 인스타 특성을 고려한 관련 인기 해시태그 목록 작성 (#내돈내산 #육아템 등)

                ### 2. 네이버 블로그 (경험 위주 솔직후기)
                - 첨부해 준 후기 스타일을 반영하여 '초보맘/육아맘' 관점의 솔직하고 다정한 경험담 말투로 작성
                - 1,500자~2,000자 이내로 작성
                - 구성 요소:
                  1) 매장/구매처 할인 꿀팁 (온누리상품권 10~15% 할인, 백화점 상품권 활용 등)
                  2) 제품 언박싱 & 첫인상/컬러 느낌 (포장 상태, 실물 색감 등)
                  3) 장점 분석 (휴대성, 기내 반입, 트래블 파우치, 핸들링, 트래블 시스템 결합, 브랜드 리콜/사후 대응 감동 비하인드 등)
                  4) 구매 시 고려해야 할 아쉬운 점/단점 (범퍼바 별도 구매, 등받이 각도 등)
                  5) 이런 분들께 추천하는 요약 파트
                - 글 중간중간 추가로 첨부하면 좋을 사진이나 정보(지도, 위치, 이벤트 캡처, 카시트 결합 사진 등)를 팁 형태로 제안해줘.
                - 본문 작성 후 네이버 블로그 특성을 고려한 관련 인기 해시태그 목록 작성 (#내돈내산 #육아템 등)

                ### 3. 숏폼 스크립트 (인스타 릴스 / 네이버 클립 / 유튜브 숏츠)
                - 시선을 사로잡는 강력한 3초 후킹 멘트
                - 화면 자막 및 대사 스크립트
                - 조회수와 댓글 반응을 유도할 수 있는 공감 포인트 구성

                ### 4. 오늘의 집
                - 감성적인 공간 스타일링 노트, 인테리어/동선과의 조화, 가벼운 추천글 톤앤매너
                """

                input_data = [prompt] + images
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=input_data
                )

                st.session_state.generated_result = response.text
                st.session_state.last_topic = topic

    # -------------------------------------------------------------------
    # 2. 결과물 표시 및 보완/저장/리스트 관리
    # -------------------------------------------------------------------
    if st.session_state.generated_result:
        st.markdown("---")
        st.subheader("✨ 생성된 원고 결과물")
        st.markdown(st.session_state.generated_result)

        st.markdown("---")
        col1, col2 = st.columns(2)

        # [기능 1] 히스토리 저장 및 텍스트 다운로드
        with col1:
            st.subheader("💾 원고 저장 관리")
            
            # 리스트에 저장하기 버튼
            if st.button("📌 원고 목록(히스토리)에 저장하기"):
                doc_id = len(st.session_state.history) + 1
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
                st.session_state.history.append({
                    "id": doc_id,
                    "date": now_str,
                    "topic": st.session_state.last_topic,
                    "content": st.session_state.generated_result
                })
                st.success("왼쪽 사이드바 '저장된 원고 목록'에 추가되었습니다!")

            st.write("")
            st.download_button(
                label="📄 텍스트(.txt) 파일로 다운로드",
                data=st.session_state.generated_result,
                file_name=f"{st.session_state.last_topic}_원고.txt",
                mime="text/plain"
            )

        # [기능 2] 피드백 반영 재생성
        with col2:
            st.subheader("🔄 피드백 반영 / 보완하여 재생성")
            refine_feedback = st.text_area("보완하고 싶은 점을 적어주세요", placeholder="예: 블로그 글에 온누리상품권 팁을 강조해줘, 릴스 후킹 멘트를 더 강력하게 수정해줘 등")

            if st.button("✨ 보완점 반영하여 다시 생성하기"):
                if refine_feedback:
                    with st.spinner("요청하신 보완사항을 반영하여 원고를 수정 중입니다..."):
                        refine_prompt = f"""
                        이전 작성한 원고에서 아래 요청사항을 반영하여 전체 내용을 수정해줘:

                        [기존 주제]: {st.session_state.last_topic}
                        [수정/보완 요청사항]: {refine_feedback}

                        [이전 원고 내용]:
                        {st.session_state.generated_result}
                        """
                        response = client.models.generate_content(
                            model='gemini-2.5-flash',
                            contents=refine_prompt
                        )
                        st.session_state.generated_result = response.text
                        st.rerun()
                else:
                    st.warning("보완할 내용을 입력해주세요!")
else:
    st.info("왼쪽 사이드바에 Gemini API 키를 입력해 주세요.")
