# utils/html_cleaner.py

from bs4 import BeautifulSoup

def html_to_text(html_str: str) -> str:
    """
    HTML → 순수 텍스트 변환
    상세보기(TextBox)에 표시할 때 사용됨.
    """
    if not html_str:
        return ""

    soup = BeautifulSoup(html_str, "html.parser")

    # <br> → 줄바꿈
    for br in soup.find_all("br"):
        br.replace_with("\n")

    # 문단 요소들은 줄바꿈 1개 삽입
    for tag in soup.find_all(["p", "div", "li", "tr"]):
        if tag.text.strip():
            tag.append("\n")

    # 텍스트만 추출
    raw = soup.get_text()

    # 불필요한 공백/중복 줄바꿈 제거
    lines = [line.strip() for line in raw.splitlines() if line.strip()]
    return "\n".join(lines)


def text_to_html(text: str) -> str:
    """
    TEXT → HTML 변환
    네이버 detailContent 업로드 용도.
    """
    if not text:
        return ""

    # \n → <br>
    escaped = (
        text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
    )

    return escaped.replace("\n", "<br>")

def format_description_blocks(text: str) -> str:
    """
    LLM이 생성한 텍스트를
    '제목 + 본문 + (빈 줄) + 제목...' 형태로 재정렬한다.

    - 제목 라인(strong 제거 후): 상품설명 / 소재 / 사양 / 세탁 및 관리
    - 제목은 항상 단독 라인
    - 본문은 제목 아래 연속 출력
    - 블록과 블록 사이는 빈 줄 1개
    """

    if not text:
        return ""

    # 줄 단위로 분리
    lines = [line.strip() for line in text.split("\n")]

    # 관련 제목 키워드
    section_names = ["상품설명", "소재", "사양", "세탁 및 관리"]

    formatted = []
    current_block = []

    def flush_block():
        if current_block:
            if formatted:
                formatted.append("")  # 블록 사이 빈 줄
            formatted.extend(current_block)
            current_block.clear()

    i = 0
    while i < len(lines):
        line = lines[i]

        # ✔ 제목인지 확인
        if line in section_names:
            flush_block()          # 기존 블록 종료
            current_block.append(line)   # 새로운 제목 시작
        else:
            # ✔ 본문 줄이면 그냥 추가
            if line:
                current_block.append(line)

        i += 1

    flush_block()  # 마지막 블록 처리

    return "\n".join(formatted)

