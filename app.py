import streamlit as st
import google.genai as genai
from PIL import Image
from datetime import datetime
import tempfile
import os

st.set_page_config(page_title="멀티플랫폼 AI 콘텐츠 에이전트", layout="wide")

st.title("📸 멀티플랫폼 인플루언서 AI 콘텐츠 에이전트")
st.write("주제, 미디어(사진/동영상), 필수 고려사항을 입력하면 각 플랫폼 감성에 맞춘 콘텐츠를 자동 생성합니다.")

# -------------------------------------------------------------------
# 세션 상태 초기화
# -------------------------------------------------------------------
if "generated_result" not in st.session_state:
    st.session_state.generated_result = ""
if "last_topic" not in st.session_state:
    st.session_state.last_topic = ""
if "history" not in st.session_state:
    st.session_state.history = []

# API 키 입력
api_key = st.sidebar.text_input("Google Gemini API Key 입력", type="password")

# -------------------------------------------------------------------
# 사이드바: 저장된 원고 히스토리 리스트
# -------------------------------------------------------------------
st.sidebar.markdown("---")
st.sidebar.subheader("📚 저장된 원고 목록")

if st.session_state.history:
    history_options = {f"[{item['date']}] {item['topic']}": item for item in st.session_state.history}
    selected_label = st.sidebar.selectbox("불러올 원고를 선택하세요", list(history_options.keys()))
    
    col_nav1, col_nav2 = st.sidebar.columns(2)
    if col_nav1.button("📖 원고 불러오기"):
        target_item = history_options[selected_label]
        st.session_state.generated_result = target_item["content"]
        st.session_state.last_topic = target_item["topic"]
        st.rerun()

    if col_nav2.button("🗑️ 원고 삭제"):
        target_item = history_options[selected_label]
        st.session_state.history = [item for item in st.session_state.history if item["id"] != target_item["id"]]
        st.sidebar.success("원고가 삭제되었습니다.")
        st.rerun()
else:
    st.sidebar.info("아직 저장된 원고가 없습니다.")


# -------------------------------------------------------------------
# 메인화면: 입력폼
# -------------------------------------------------------------------
if api_key:
    client = genai.Client(api_key=api_key)

    topic = st.text_input("1. 콘텐츠 제목 / 주제를 입력하세요", placeholder="예: [사용후기] 줄즈 에어2 유모차 & 다이치 카시트 내돈내산 추천")
    uploaded_files = st.file_uploader("2. 사진 또는 동영상을 업로드하세요 (복수 선택 가능)", type=["jpg", "jpeg", "png", "mp4"], accept_multiple_files=True)
    must_include = st.text_area(
        "3. 내용 작성 시 꼭 고려하거나 포함해야 할 사항을 입력하세요", 
        placeholder="예: 온누리상품권 10~15% 할인 구매 꿀팁, 어댑터 리콜 대응에 감동받은 비하인드, 등받이 각도나 범퍼바 별도구매 등 아쉬운 점"
    )

    if st.button("🚀 전체 플랫폼 콘텐츠 생성하기"):
        if not topic:
            st.warning("제목/주제를 입력해주세요!")
        else:
            media_inputs = []
            temp_files = []

            with st.spinner("미디어 파일 분석 및 준비 중..."):
                if uploaded_files:
                    for file in uploaded_files:
                        if file.type.startswith("image"):
                            media_inputs.append(Image.open(file))
                        elif file.type.startswith("video"):
                            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_file:
                                tmp_file.write(file.read())
                                tmp_file_path = tmp_file.name
                                temp_files.append(tmp_file_path)
                            
                            uploaded_gemini_file = client.files.upload(file=tmp_file_path)
                            media_inputs.append(uploaded_gemini_file)

            with st.spinner("AI가 채널별 맞춤 원고를 작성하고 있습니다..."):
                prompt = f"""
                너는 인스타그램, 네이버 블로그, 숏폼(릴스/클립/숏츠), 오늘의집 등 다양한 채널을 운영하는 전문 인플루언서 에이전트야.
                제공된 사진/동영상들의 전체적인 감성, 색감, 장소, 분위기, 스타일을 세밀하게 분석하고 이를 반영해서 각 플랫폼 스타일에 맞게 글을 작성해줘.

                [주제/제목]: {topic}
                [필수 반영/고려 사항]: {must_include if must_include else "특별한 추가 요구사항 없음"}

                ---
                ### 1. 인스타그램 피드
                - 인스타그램 특유의 감성적이고 친근한 톤앤매너
                - 적절하고 다채로운 이모티콘 적극 활용
                - 본문 작성 후 관련 인기 해시태그 목록 작성 (#내돈내산 #육아템 #육아소통 등)

                ### 2. 네이버 블로그 (경험 위주 솔직후기)
                - **글자수 조건**: 공백 포함 **최소 1,500자 ~ 최대 2,000자 분량**으로 서론, 본론, 결론을 매우 풍부하고 디테일하게 작성할 것.
                - **스타일 조건**: 
                  1) 섹션 구분 시 가로줄(---)을 절대로 사용하지 말 것.
                  2) 글의 가독성과 몰입감을 위해 문단 사이 및 제목, 본문 곳곳에 귀엽고 직관적인 이모지(✨, 👶, 🛒, 💡, 맘, ❤️ 등)를 다채롭게 추가할 것.
                - 초보맘/인플루언서 관점의 다정하고 솔직한 경험담 말투 (~했답니다, ~했지 뭐예요 등)
                - 필수 구성 요소:
                  1) 구매처 및 할인 꿀팁 (온누리상품권 할인, 백화점 상품권 활용 등)
                  2) 제품 언박싱 & 실물 느낌/컬러 소감
                  3) 솔직 장점 분석 (폴딩, 휴대성, 핸들링, 트래블 시스템 결합, 리콜/AS 대응 감동 비하인드 등)
                  4) 구매 시 고려해야 할 단점/아쉬운 점 (범퍼바 별도 구매, 등받이 각도 등)
                  5) 추천 대상 요약 정리
                - 글 중간중간 [📸 사진 추천: 매장 지도 위치 / 결합 사진 / 리콜 안내 문자 캡처 등] 가이드를 넣어줄 것.

                ### 3. 숏폼 스크립트 (인스타 릴스 / 네이버 클립 / 유튜브 숏츠)
                - 시선을 사로잡는 강력한 3초 후킹 멘트
                - 화면 자막 및 대사 스크립트
                - 댓글과 조회수 반응을 이끌어낼 수 있는 공감 포인트 구성

                ### 4. 오늘의 집
                - 감성적인 공간 스타일링 노트, 인테리어/동선과의 조화, 가벼운 추천글 톤앤매너
                """

                try:
                    input_data = [prompt] + media_inputs
                    response = client.models.generate_content(
                        model='gemini-3.6-flash',
                        contents=input_data
                    )

                    st.session_state.generated_result = response.text
                    st.session_state.last_topic = topic
                except Exception as e:
                    st.error(f"콘텐츠 생성 중 오류가 발생했습니다: {e}")
                finally:
                    for tmp_path in temp_files:
                        if os.path.exists(tmp_path):
                            os.remove(tmp_path)

    # -------------------------------------------------------------------
    # 결과물 표시 및 히스토리 저장 관리
    # -------------------------------------------------------------------
    if st.session_state.generated_result:
        st.markdown("---")
        st.subheader("📄 전체 원고 결과물")
        
        # 전체 원고 화면 표출
        st.markdown(st.session_state.generated_result)

        st.markdown("---")
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("💾 원고 저장 관리")
            
            if st.button("📌 원고 목록(히스토리)에 저장하기"):
                new_id = len(st.session_state.history) + 1
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
                
                st.session_state.history.append({
                    "id": new_id,
                    "date": now_str,
                    "topic": st.session_state.last_topic,
                    "content": st.session_state.generated_result
                })
                st.success("왼쪽 사이드바 '저장된 원고 목록'에 성공적으로 저장되었습니다!")
                st.rerun()

            st.write("")
            st.download_button(
                label="📄 전체 원고 텍스트(.txt) 다운로드",
                data=st.session_state.generated_result,
                file_name=f"{st.session_state.last_topic}_원고.txt",
                mime="text/plain"
            )

        with col2:
            st.subheader("🔄 피드백 반영 / 보완하여 재생성")
            refine_feedback = st.text_area("보완하고 싶은 점을 적어주세요", placeholder="예: 블로그 글에 사진 들어갈 위치를 2개 더 늘려줘, 인스타 해시태그를 더 많이 뽑아줘 등")

            if st.button("✨ 보완점 반영하여 다시 생성하기"):
                if refine_feedback:
                    with st.spinner("요청하신 보완사항을 반영하여 원고를 수정 중입니다..."):
                        refine_prompt = f"""
                        이전 작성한 원고에서 아래 요청사항을 반영하여 전체 내용을 수정해줘:

                        [기존 주제]: {st.session_state.last_topic}
                        [수정/보완 요청사항]: {refine_feedback}

                        * 블로그 글 규칙 재확인:
                          - 공백 포함 최소 1,500자 ~ 최대 2,000자 분량
                          - 가로줄(---) 절대 금지
                          - 다양하고 풍부한 이모지 적극 활용

                        [이전 원고 내용]:
                        {st.session_state.generated_result}
                        """
                        response = client.models.generate_content(
                            model='gemini-3.6-flash',
                            contents=refine_prompt
                        )
                        st.session_state.generated_result = response.text
                        st.rerun()
                else:
                    st.warning("보완할 내용을 입력해주세요!")
else:
    st.info("왼쪽 사이드바에 Gemini API 키를 입력해 주세요.")
