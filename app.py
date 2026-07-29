import os
from google import genai
from google.genai import types

# 1. Gemini API 클라이언트 초기화
# 환경변수 GOOGLE_API_KEY가 설정되어 있어야 합니다.
# export GOOGLE_API_KEY="your-api-key"
client = genai.Client()

# 2. 멀티플랫폼 콘텐츠 생성 함수 Definition
def generate_multi_platform_content(topic: str, media_paths: list[str] = None):
    """
    주제(topic)와 사진/동영상 파일 목록(media_paths)을 전달받아
    인스타그램, 네이버 블로그, 숏폼(릴스/클립/쇼츠), 오늘의 집 가이드에 맞는 
    콘텐츠 결과를 생성합니다.
    """
    
    # AI 에이전트 페르소나 및 플랫폼별 가이드라인 프롬프트 설정
    system_instruction = """
    당신은 육아, 라이프스타일, 인테리어 분야에 특화된 전문 만능 인플루언서 AI 에이전트입니다.
    사용자가 제공한 주제와 사진/동영상의 분위기, 감성을 완벽하게 파악하여 
    각 플랫폼별 특성에 들어맞는 최적의 콘텐츠 프레임을 생성해 주세요.

    [플랫폼별 작성 가이드라인]
    1. 인스타그램 (Feed & Reels Caption)
       - 특유의 감성적이고 정돈된 톤앤매너, 적절한 이모지 사용
       - 공감대를 형성하는 문장과 줄바꿈
       - 검색 및 노출에 최적화된 해시태그 목록 (#육아템 #휴대용유모차 등)

    2. 네이버 블로그
       - 진정성 있는 내돈내산/실제 경험 위주의 가독성 높은 어조 (~했는데요!, ~입니다)
       - 헤더/소제목 구분 및 항목별 꿀팁/장단점 정리
       - [추가 추천 요소]: 글 작성 시 추가로 첨부하면 좋을 사진 각도, 매장 지도, 관련 팁 아이디어 제시

    3. 숏폼 콘텐츠 (인스타그램 릴스 / 네이버 클립 / 유튜브 쇼츠)
       - 시청자를 사로잡는 강력한 후킹 멘트 (상단 자막용)
       - 15~30초 분량의 씬(Scene)별 구성안 및 오디오/나레이션 스크립트

    4. 오늘의 집 (Story / O-House Feed)
       - 공간과 어우러지는 감성적인 인테리어/라이프스타일 톤
       - 유용한 육아/집꾸미기 정보 공유 스타일
    """

    # 이미지/동영상 및 텍스트 프롬프트 구성
    contents = []
    
    # 미디어 파일 업로드 및 프롬프트 첨부
    if media_paths:
        for path in media_paths:
            if os.path.exists(path):
                print(f"미디어 파일 업로드 중: {path}")
                uploaded_file = client.files.upload(file=path)
                contents.append(uploaded_file)
            else:
                print(f"경고: 파일을 찾을 수 없습니다 -> {path}")

    # 사용자 요구사항 텍스트 프롬프트
    prompt_text = f"""
    [요청 주제 및 내용]
    {topic}

    위 전달된 이미지/동영상 파일들의 감성과 분위기, 그리고 주제를 바탕으로 
    인스타그램, 네이버 블로그, 숏폼(릴스/클립/쇼츠), 오늘의 집 플랫폼 맞춤형 원고 및 대본을 생성해 주세요.
    """
    contents.append(prompt_text)

    print("\nGemini AI 에이전트가 콘텐츠를 생성 중입니다...\n")

    # 최신 SDK 기준 Gemini 모델 호출 (gemini-2.5-flash)
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.7,
        )
    )

    return response.text

# 3. 실행 예시
if __name__ == "__main__":
    # 작성하고자 하는 콘텐츠 주제
    user_topic = """
    베이비하우스 마곡점에서 직접 비교해보고 내돈내산으로 구매한 '줄즈 에어2' 휴대용 유모차와 
    '다이치' 바구니 카시트 트래블 시스템 조합 실사용 후기.
    - 온누리상품권 10% 할인 팁
    - 한 손 이지폴딩 및 기내반입 가벼움
    - 바구니 카시트 결합의 편리함과 스무스한 핸들링 장점
    - 범퍼바 별도구매 및 등받이 각도 아쉬운 점 정리
    """
    
    # 참고할 미디어 파일 경로 목록 (예시)
    sample_media = [
        # "stroller_image1.jpg",
        # "stroller_video1.mp4"
    ]

    result = generate_multi_platform_content(topic=user_topic, media_paths=sample_media)
    
    print("=" * 50)
    print("✨ AI 에이전트 플랫폼별 최종 결과물 ✨")
    print("=" * 50)
    print(result)
