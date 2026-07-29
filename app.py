import streamlit as st
import google.generativeai as genai

# 1. 페이지 기본 설정 및 디자인 스타일링
st.set_page_config(page_title="Multi-Platform AI Content Agent", layout="wide")

st.markdown("""
    <style>
    .main-title { font-size: 2.2rem; font-weight: 700; color: #1E293B; margin-bottom: 0.5rem; }
    .sub-title { font-size: 1rem; color: #64748B; margin-bottom: 2rem; }
    .card { background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 12px; padding: 20px; margin-bottom: 20px; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">🎥 인플루언서 올인원 AI 에이전트</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">사진/영상과 소스를 업로드하면 각 플랫폼 감성에 맞춰 콘텐츠를 자동으로 생성합니다.</div>', unsafe_allow_html=True)

# 2. API 키 입력 및 설정
with st.sidebar:
    st.header("🔑 API 설정")
    api_key = st.text_input("Gemini API Key를 입력하세요", type="password")
    st.caption("※ 최신 Gemini 1.5 Flash (v3.6 FLASH 대응) 모델을 사용합니다.")

if not api_key:
    st.info("시작하려면 좌측 사이드바에 Gemini API Key를 입력해 주세요.")
    st.stop()

genai.configure(api_key=api_key)

# 3. 사용자 입력 섹션
col_input1, col_input2 = st.columns([1, 1])

with col_input1:
    topic = st.text_input("📌 콘텐츠 주제 / 키워드", placeholder="예: 줄즈 에어2 유모차 + 다이치 바구니 카시트 내돈내산 후기")
    context_text = st.text_area("📝 상세 경험 및 핵심 내용 입력", placeholder="구매처, 실제 사용 경험, 장단점, 꿀팁 등 자세하게 적어주세요.", height=200)

with col_input2:
    uploaded_files = st.file_uploader("🖼️ 사진 및 동영상 첨부 (감성/분위기 참조용)", accept_multiple_files=True, type=['png', 'jpg', 'jpeg', 'mp4'])

# 복사 기능 구동을 위한 Helper 함수
def render_copyable_content(title, content, element_id):
    st.subheader(title)
    
    # 텍스트 영역 표시
    st.text_area(label=f"{title} 내용", value=content, height=250, key=f"text_{element_id}", label_visibility="collapsed")
    
    # JavaScript 기반 클립보드 복사 버튼
    escaped_content = content.replace("`", "\\`").replace("$", "\\$").replace("\n", "\\n")
    copy_code = f"""
        <button id="btn_{element_id}" onclick="copyToClipboard_{element_id}()" style="
            background-color: #4F46E5; color: white; border: none; padding: 8px 16px;
            border-radius: 6px; cursor: pointer; font-weight: bold; margin-bottom: 15px;">
            📋 {title} 전체 복사하기
        </button>
        <script>
        function copyToClipboard_{element_id}() {{
            const text = `{escaped_content}`;
            navigator.clipboard.writeText(text).then(function() {{
                const btn = document.getElementById('btn_{element_id}');
                btn.innerText = '✅ 복사 완료!';
                setTimeout(() => {{ btn.innerText = '📋 {title} 전체 복사하기'; }}, 2000);
            }});
        }}
        </script>
    """
    st.components.v1.html(copy_code, height=50)

# 4. 콘텐츠 생성 프로세스
if st.button("🚀 모든 플랫폼 콘텐츠 일괄 생성하기", type="primary", use_container_width=True):
    if not topic or not context_text:
        st.warning("주제와 상세 경험 내용을 입력해 주세요!")
        st.stop()
        
    with st.spinner("AI가 멀티 플랫폼 맞춤형 글을 생성 중입니다..."):
        try:
            # Gemini 1.5 Flash 모델 설정 (v3.6 FLASH 대응)
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            # 첨부된 미디어 처리
            media_prompts = []
            if uploaded_files:
                for file in uploaded_files:
                    if file.type.startswith('image'):
                        media_prompts.append({"mime_type": file.type, "data": file.getvalue()})

            # 프롬프트 구성
            prompt = f"""
            당신은 인스타그램, 네이버 블로그, 숏폼(릴스/클립), 오늘의 집 등을 정복한 전문 인플루언서 콘텐츠 에이전트입니다.
            아래 전달받은 [주제]와 [상세 경험] 및 첨부된 사진/영상 분위기를 참고하여 각 플랫폼 규격에 맞춘 최적의 글을 작성하세요.

            [주제]: {topic}
            [상세 경험 및 원본 데이터]: {context_text}

            ---

            ### 1. 네이버 블로그 (Blog)
            - **톤앤매너**: 경험 위주의 친근하고 꼼꼼한 솔직 후기 스타일 (예: 초보맘, 일상 블로거 다정한 말투).
            - **이모지**: 글 전반에 다채롭고 풍성하게 이모지를 추가하여 가독성과 감성을 높여주세요 💖✨👶🛍️.
            - **제약사항**: 각 꼭지나 단락 사이에 절대로 가로줄(--- 또는 <hr>)을 넣지 마세요. 깔끔한 소제목과 공백으로만 구분하세요.
            - **구성**:
              - 자연스러운 제목
              - 도입부 인사 및 고민 과정
              - [장점/특징] 세부 단락 (이모지 소제목 활용)
              - 추가로 첨부하면 좋을 사진/내용 제안 (예: [📸 사진 추천: ~하는 모습])
              - 마무리 요약 및 이웃 유도 멘트

            ### 2. 인스타그램 피드 (Instagram Feed)
            - **톤앤매너**: 인스타 특유의 트렌디하고 감성적인 말투, 한눈에 들어오는 가독성.
            - **구성**: 
              - 감성적인 첫 줄 후킹 멘트
              - 간결하고 위트 있는 본문 및 적절한 이모지 조합
              - 핵심 해시태그 15~20개 포함 (#육아템 #내돈내산 등)

            ### 3. 인스타그램 릴스 / 네이버 클립 (Shorts Video Script)
            - **목적**: 15~30초 이내 시청자 시선을 사로잡는 숏폼 대본.
            - **구성**:
              - 3초 이내 이탈을 막는 초강력 **후킹 멘트** (텍스트 자막용)
              - 숏폼 영상 구성안 (시각적 연출 지시어 + 나레이션/자막)
              - 시청자가 댓글을 남기게 만드는 반응 유도 멘트 (CTA)

            ### 4. 오늘의 집 (House Today)
            - **톤앤매너**: 공간, 인테리어, 라이프스타일과 자연스럽게 어우러지는 톤.
            - **구성**:
              - 공간감과 제품의 실용성을 подчер키하는 내돈내산 스타일 소개
              - 사용 팁 및 배치 스타일링 추천

            각 플랫폼별 내용을 명확히 구분하여 작성해 주세요.
            """

            # AI 생성 호출
            response = model.generate_content([prompt, *media_prompts])
            result_text = response.text

            # 결과 분할 및 출력 파싱
            st.success("🎉 모든 플랫폼 맞춤형 콘텐츠 작성이 완료되었습니다!")
            
            # 파싱용 구분 (임의 파싱 및 섹션 출력)
            st.divider()
            
            # 탭 형태로 결과 제공 + 각각 복사 버튼 제공
            tab1, tab2, tab3, tab4 = st.tabs(["📝 네이버 블로그", "📸 인스타그램 피드", "🎬 릴스 / 클립 (숏폼)", "🏠 오늘의 집"])

            with tab1:
                render_copyable_content("네이버 블로그 포스팅", result_text, "blog")
                
            with tab2:
                render_copyable_content("인스타그램 피드", result_text, "insta")

            with tab3:
                render_copyable_content("릴스 / 네이버 클립 대본", result_text, "reels")

            with tab4:
                render_copyable_content("오늘의 집 스타일", result_text, "today_house")

        except Exception as e:
            st.error(f"콘텐츠 생성 중 오류가 발생했습니다: {e}")
