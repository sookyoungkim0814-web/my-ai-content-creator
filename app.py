import streamlit as st
import google.generativeai as genai
import re
import json
import os

# ==========================================================
# 0. 로컬 파일(JSON) 저장/불러오기 함수
# ==========================================================
HISTORY_FILE = "saved_history.json"

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_history(history_list):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history_list, f, ensure_ascii=False, indent=4)

# ==========================================================
# 1. 페이지 기본 설정
# ==========================================================
st.set_page_config(page_title="멀티 플랫폼 AI 원고 생성기", layout="wide")

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

# ----------------------------------------------------------
# 세션 상태 초기화 (JSON 파일 기반 영구 저장)
# ----------------------------------------------------------
if "generated_contents" not in st.session_state:
    st.session_state.generated_contents = None
if "saved_history" not in st.session_state:
    st.session_state.saved_history = load_history()
if "file_uploader_key" not in st.session_state:
    st.session_state.file_uploader_key = 0

# 입력창, 업로드 파일, 현재 결과를 안전하게 초기화하는 콜백 함수
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

3. **인스타그램 캐러셀**:
   - 슬라이드별(5장~10장) 구성안 제공 (슬라이드 1: 타이틀 / 2~9: 장점 요약 / 마지막: CTA)

4. **인스타그램 릴스/숏츠**:
   - 15~30초 숏폼 영상 대본 ([시각 자료 / 자막 / 나레이션])

5. **오늘의집 피드**:
   - 감성적인 리빙/육아 라이프스타일 톤앤매너, 공간/스타일/사용성 위주, 브랜드 및 해시태그 포함

응답은 반드시 아래 5개 구분 태그를 정확히 사용하여 출력하세요:

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
            "📷 참고 이미지 / 동영상 업로드 (선택)", 
            type=["jpg", "jpeg", "png", "mp4", "mov"], 
            accept_multiple_files=True,
            key=f"file_uploader_{st.session_state.file_uploader_key}"
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
                        refine_prompt = f"이전 원고:\n{st.session_state.generated_contents}\n\n피드백:\n{feedback}\n\n위 피드백 5개 플랫폼 모두에 반영해서 다시 작성해주세요."
                        response = model.generate_content([SYSTEM_PROMPT, refine_prompt])
                        st.session_state.generated_contents = response.text
                        st.rerun()

    # ----- [RIGHT COLUMN] 결과 출력 -----
    with right_col:
        st.subheader("📄 생성된 원고 결과")
        
        if st.session_state.generated_contents:
            if st.button("💾 원고 저장하기", use_container_width=True):
                new_item = {
                    "product_name": product_name if product_name else "무제",
                    "content": st.session_state.generated_contents
                }
                st.session_state.saved_history.append(new_item)
                # JSON 파일에도 영구 저장
                save_history(st.session_state.saved_history)
                st.success("히스토리에 영구 저장되었습니다! (코드 수정 후에도 유지됩니다)")

            st.markdown("---")
            
            # 플랫폼별 텍스트 파싱
            raw_text = st.session_state.generated_contents
            platforms = ["네이버 블로그", "인스타그램 피드", "인스타그램 캐러셀", "인스타그램 릴스/숏츠", "오늘의집 피드"]
            parsed_contents = {}
            
            for i, platform in enumerate(platforms):
                if i < len(platforms) - 1:
                    next_platforms = platforms[i+1:]
                    next_pattern = "|".join([rf"\[{re.escape(p)}\]" for p in next_platforms])
                    pattern = rf"\[{re.escape(platform)}\]\s*(.*?)(?={next_pattern}|\Z)"
                else:
                    pattern = rf"\[{re.escape(platform)}\]\s*(.*)"
                
                match = re.search(pattern, raw_text, re.DOTALL)
                parsed_contents[platform] = match.group(1).strip() if match else "생성된 내용이 없습니다."

            # 결과 탭 구성
            result_tabs = st.tabs(["📋 전체 원고"] + [f"📌 {p}" for p in platforms])
            
            # 1) 전체 원고 탭
            with result_tabs[0]:
                for platform in platforms:
                    st.markdown(f"## 📌 {platform}")
                    st.markdown(parsed_contents[platform])
                    st.markdown("---")
                
            # 2) 각 플랫폼별 탭
            for i, platform in enumerate(platforms):
                with result_tabs[i+1]:
                    st.caption(f"우측 상단의 복사 버튼(📋 아이콘)을 누르면 [{platform}] 원고가 복사됩니다.")
                    st.code(parsed_contents[platform], language="markdown")

        else:
            st.info("👈 왼쪽 입력창에 정보를 입력하고 원고 생성 버튼을 누르면 이 영역에 결과가 나타납니다.")

# ----------------------------------------------------------
# [MAIN TAB 2] 저장된 원고 관리
# ----------------------------------------------------------
with main_tab2:
    st.subheader("📚 저장된 히스토리 관리")
    
    if not st.session_state.saved_history:
        st.info("저장된 원고가 없습니다. '원고 생성 및 결과' 탭에서 원고를 만든 뒤 [💾 원고 저장하기] 버튼을 눌러보세요.")
    else:
        with st.form("history_delete_form"):
            delete_indices = []
            for idx, item in enumerate(st.session_state.saved_history):
                c_chk, c_exp = st.columns([1, 15])
                with c_chk:
                    if st.checkbox("", key=f"history_chk_{idx}"):
                        delete_indices.append(idx)
                with c_exp:
                    with st.expander(f"[{idx+1}] {item['product_name']}"):
                        st.markdown(item['content'])
            
            if st.form_submit_button("🗑️ 선택 항목 삭제", use_container_width=True):
                if not delete_indices:
                    st.warning("삭제할 항목을 선택해주세요.")
                else:
                    for i in sorted(delete_indices, reverse=True):
                        del st.session_state.saved_history[i]
                    # JSON 파일 업데이트
                    save_history(st.session_state.saved_history)
                    st.success("선택한 원고가 삭제되었습니다.")
                    st.rerun()
