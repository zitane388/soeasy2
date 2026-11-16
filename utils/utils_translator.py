from deep_translator import GoogleTranslator

# 전역 인스턴스 (메모리 캐싱)
_translator = GoogleTranslator(source='auto', target='ko')

def translate_to_korean(text: str) -> str:
    """
    텍스트를 한국어로 번역.
    실패하면 원문 반환.
    """
    if not text:
        return text
    try:
        return _translator.translate(text)
    except Exception as e:
        print(f"[번역 오류] {e}")
        return text
