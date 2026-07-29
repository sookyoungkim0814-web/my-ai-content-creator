import streamlit as st
from google import genai
from google.genai import types
from PIL import Image

# ---------------------------------------------------------
# Page Configuration
# ---------------------------------------------------------
st.set_page_config(
    page_title="올인원 인플루언서 AI 콘텐츠 제작소 🎥",
    page_icon="🎥",
    layout="wide",
)

st.title("🎥 멀티플랫폼 인플루언서 콘텐츠 자동 생성 에이전트")
st.caption("사진/동영상과 간단한 내용만 업로드하면 Gemini 3.6 Flash가 플랫폼별 맞춤 원고를 생성합니다.")

# ---------------------------------------------------------
# Sidebar: API Key Configuration
# ---------------------------------------------------------
with st.sidebar:
    st.header("⚙️ API 설정")
    api_key = st.text_input("Gemini API Key를 입력하세요", type="password")
    
    MODEL_NAME = "gemini-3.6-flash"
    st.info(f"🤖 사용 모델: **{MODEL_NAME}**")
    st.markdown("---")
    st.markdown("💡 이미지/동영상을 업로드하면 AI가 시각적 감성을 분석하여 글을 작성합니다.")

# ---------------------------------------------------------
# System Prompt
# ---------------------------------------------------------
SYSTEM_PROMPT = """
당신은 만능 멀티플랫폼 인플루언서 콘텐츠 제작 AI 에이전트입니다. 
사용자가 제공하는 [주제/경험 내용]과 [업로드된 사진/동영상의 시각적 감성/분위기]를 분석하여, 각 플랫폼의 성격과 포맷에 맞춘 최상급 품질의 원고를 작성해 주세요.

[플랫폼별 작성 가이드라인]
1. 네이버 블로그 (Naver Blog)
- 친근하고 솔직한 경험 위주의 내돈내산 육아/라이프스타일 블로거 말투 (~했어요!, ~ 추천해 드려요 🤍)
- 구매/방문 팁, 실사용 장점, 아쉬운 점, 사진 첨부 구도 안내(`[사진: ~하는 모습]`) 포함

2. 인스타그램 피드 (Instagram Feed)
- 감성적이고 세련된 인스타 톤앤매너, 이모티콘 적극 활용, 해시태그 15~20개 포함

3. 숏폼 스크립트 (릴스 / 클립 / Shorts)
- 0~3초 시선을 사로잡는 강력한 후킹 멘트, 주요 포인트 3가지, 엔딩 CTA
- `[화면 연출 설명]` + `(나레이션/자막)` 포맷

4. 오늘의집 (Ohouse)
- 감각적이고 따뜻한 인테리어 및 공간 스타일링 중심 원고
"""

# ---------------------------------------------------------
# Main UI Inputs (파일 업로드 화면 추가)
# ---------------------------------------------------------
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📝 콘텐츠 및 파일 업로드")
    
    # 1. 주제 입력
    topic = st.text_area(
        "1. 주제 / 경험 내용",
        placeholder="예: 줄즈 에어2 휴대용 유모차 + 다이치 바구니 카시트 마곡 베이비하우스 구매 및 한강 나들이 후기",
        height=100
    )
    
    # 2. 파일 업로드 버튼 (사진/동영상)
    uploaded_files = st.file_uploader(
        "2. 사진 및 동영상 업로드 (선택)",
        type=["jpg", "jpeg", "png", "mp4"],
        accept_multiple_files=True
    )
    
    # 업로드한 이미지 미리보기
    if uploaded_files:
        st.write("🖼️ 업로드된 파일 미리보기:")
        preview_cols = st.columns(3)
        for idx, file in enumerate(uploaded_files):
            if file.type.startswith("image"):
                img = Image.open(file)
                preview_cols[idx % 3].image(img, use_container_width=True)

    # 3. 추가 장단점 / 꿀팁
    highlights = st.text_area(
        "3. 강조할 장단점 및 꿀팁 (선택)",
        placeholder="예: 모바일 온누리상품권 10% 할인, 한 손 핸들링 / 범퍼바 별도 구매 아쉬움",
        height=100
    )

    generate_btn = st.button("🚀 4개 플랫폼 원고 전체 생성하기", type="primary", use_container_width=True)

# ---------------------------------------------------------
# Generation & Result Display
# ---------------------------------------------------------
with col2:
    st.subheader("✨ 플랫폼별 생성 결과물")
    
    if generate_btn:
        if not api_key:
            st.error("🔑 좌측 사이드바에 Gemini API Key를 입력해 주세요.")
        elif not topic:
            st.warning("📌 주제 및 경험 내용을 입력해 주세요.")
        else:
            with st.spinner("업로드한 이미지 분석 및 플랫폼별 원고 작성 중..."):
                try:
                    client = genai.Client(api_key=api_key)
                    
                    # Gemini API에 전달할 contents 리스트 구성
                    contents = []
                    
                    # 업로드된 이미지가 있으면 PIL Image 객체로 변환하여 API에 전달
                    if uploaded_files:
                        for file in uploaded_files:
                            if file.type.startswith("image"):
                                img = Image.open(file)
                                contents.append(img)
                    
                    # 텍스트 프롬프트 추가
                    user_prompt = f"""
                    [사용자 입력 정보]
                    - 주제 / 경험 내용: {topic}
                    - 강조할 장단점 및 꿀팁: {highlights}

                    함께 첨부된 사진/동영상의 분위기, 색감, 장소, 감성을 분석하여 
                    네이버 블로그, 인스타그램 피드, 숏폼 스크립트, 오늘의집 원고를 생성해 주세요.
                    """
                    contents.append(user_prompt)

                    # gemini-3.6-flash 호출
                    response = client.models.generate_content(
                        model=MODEL_NAME,
                        contents=contents,
                        config=types.GenerateContentConfig(
                            system_instruction=SYSTEM_PROMPT,
                            temperature=0.7,
                        )
                    )

                    st.success("✅ 원고 생성이 완료되었습니다!")
                    st.markdown(response.text)

                except Exception as e:
                    st.error(f"오류가 발생했습니다: {str(e)}")