DETAIL_DESCRIPTION_PROMPT = """
너는 한국 온라인 쇼핑몰 상품 상세페이지를 작성하는 전문가다.

입력된 원문 정보를 기반으로 한국 쇼핑몰에서 사용하는 상세페이지를 작성하라.

────────────────────────────────
[목표]
────────────────────────────────

국내 쇼핑몰 스타일의 상품 상세페이지 작성

반드시 아래 4개 섹션 구조를 사용한다:

상품설명
소재
사양
세탁 및 관리

────────────────────────────────
[상품설명 작성 규칙 — 매우 중요]
────────────────────────────────

상품설명은 아래 구조를 반복하여 작성한다:

1. 각 기능별로 먼저 "헤드라인형 어필 문장" 작성
2. 헤드라인는 반드시 굵게(**볼드체**) 작성
3. 바로 아래에 원문 기반의 근거 설명 작성
4. 기능별로 위 구조 반복

형식 예시:

**땀이 나도 쾌적한 에어리즘 기능성 소재**
에어리즘 소재를 사용해 땀을 빠르게 흡수하고 건조됩니다.
착용 중에도 쾌적한 상태를 유지할 수 있습니다.

**형태 변형을 줄인 립 골지 넥라인**
목둘레를 립 골지 짜임으로 제작했습니다.
세탁 후에도 형태가 쉽게 늘어지지 않는 구조입니다.

────────────────────────────────
[헤드라인 작성 규칙]
────────────────────────────────

헤드라인은 반드시:

- 기능 요약 형태로 작성
- 국내 쇼핑몰 어필형 문장 사용
- 과장 금지
- 반드시 볼드체 사용

허용 예시:

**겉은 코튼처럼 깔끔하고, 착용 시에는 에어리즘으로 시원하게**

**흔들림 없이 안정적으로 지지하는 브라 내장 구조**

**세탁 후에도 형태가 쉽게 변하지 않는 넥라인 구조**

금지:

- 설명형 헤드라인
- 볼드체 누락
- 기능과 무관한 헤드라인

────────────────────────────────
[근거 설명 작성 규칙]
────────────────────────────────

반드시 원문 기반으로만 작성

허용:

신축성이 향상된 소재로 제작되었습니다.
몸의 움직임에 따라 자연스럽게 늘어납니다.

금지:

추측
임의 기능 추가
원문에 없는 효과 추가

────────────────────────────────
[상품설명 문체 규칙]
────────────────────────────────

허용:

~구조입니다
~디자인입니다
~소재입니다
~제작되었습니다
~적용되었습니다

허용 (어필 표현 — 인과관계 있을 경우만):

쾌적한 착용 상태를 유지합니다
시원한 촉감을 제공합니다
안정적으로 유지합니다

금지:

~완성했습니다
~연출할 수 있습니다
~느낄 수 있습니다

────────────────────────────────
[소재 섹션 규칙]
────────────────────────────────

혼용률만 작성

예시:

면 60% 레이온 40%

설명 금지

────────────────────────────────
[사양 섹션 규칙]
────────────────────────────────

구조 및 기능만 작성

예시:

브라컵 내장 구조
에어리즘 기능성 소재
립 골지 넥라인
오버핏 구조

설명 금지

────────────────────────────────
[세탁 및 관리 섹션 규칙]
────────────────────────────────

지시형 문장 사용

예시:

세탁기 세탁 가능
세탁망 사용 권장
건조기 사용 금지

────────────────────────────────
[출력 형식 — 반드시 준수]
────────────────────────────────

아래 형식을 그대로 사용:

상품설명

(헤드라인 bold)
(근거 설명)

(헤드라인 bold)
(근거 설명)

소재

(혼용률)

사양

(구조 목록)

세탁 및 관리

(세탁 방법)

────────────────────────────────
[절대 금지]
────────────────────────────────

섹션 누락
볼드 헤드라인 누락
원문에 없는 기능 추가
불필요한 감정 표현

────────────────────────────────
아래 원문을 위 규칙에 따라 재작성하라:

===========
{INPUT_TEXT}
===========
"""






PRODUCT_NAME_PROMPT = """
너는 한국 온라인 쇼핑몰 상품명을 작성하는 전문가다.

원본 상품명을 한국 쇼핑몰 스타일로 자연스럽게 번역하고,
후보 키워드에서 상품 경쟁력에 도움이 되는 키워드 있다면
원본명과 자연스럽게 조합하여 새로운 상품명을 생성하라.

────────────────────────────────
[표현 변환 규칙 — 반드시 적용]
────────────────────────────────
1) 직역 느낌 단어는 한국 쇼핑몰에서 실제 사용하는 표현으로 변환한다.
2) 키워드 선택은 보수적으로 추측 금지, 사실에 기반한 정보만

────────────────────────────────
[핵심 출력 규칙 — 반드시 준수]
────────────────────────────────
1) 최종 상품명은 40자 이내.
2) 키워드순서는 브랜드명(한국어우선), 성별(해당 시), 특징키워드 순으로 배열한다.
3) 결과는 상품명 한 줄만 출력한다. 설명·부연 금지.

[원본상품명]
{ORIGINAL_NAME}

[후보키워드]
{P_KEYWORDS}
"""






PRODUCT_NAME_PROMPT_VISION = """
너는 한국 온라인 쇼핑몰 상품명을 작성하는 전문가다.

원본 상품명을 한국 쇼핑몰 스타일로 자연스럽게 번역하고,
검색 노출에 도움이 되는 키워드만 선별하여 조합해 상품명을 생성하라.

이미지가 제공되면 확인 가능한 요소만 반영하고 추측 금지.

────────────────────────────────
[키워드 사용 기준]
────────────────────────────────

사용 가능
상품 종류, 소재, 구조, 기능, 길이, 디자인, 패턴, 성별

사용 금지
배송, 할인, 특가, 이벤트, 세일, 신상, 인기, 추천, 무료배송 등
가격, 프로모션, 판매조건 등 상품 속성과 무관한 키워드 전면 금지

────────────────────────────────
[표현 규칙]
────────────────────────────────

1. 직역 금지, 한국 쇼핑몰에서 사용하는 자연스러운 표현 사용
2. 이미지 또는 원문에서 확인되지 않은 정보 추가 금지
3. 국내 검색 기준 용어 우선 사용

────────────────────────────────
[출력 규칙]
────────────────────────────────

1. 40자 이내
2. 키워드 순서: 브랜드명(한국어 우선) + 성별(해당 시) + 특징 + 상품 종류
3. 특수문자는 모델명에 필요한 경우만 허용
4. 설명 없이 상품명 한 줄만 출력.

[원본 상품명]
{ORIGINAL_NAME}

[후보 키워드]
{P_KEYWORDS}
"""








PRODUCT_OPTION_PROMPT = """
You are standardizing one ecommerce option value for Korean market listing.

Input:
- Group name: {GROUP_NAME}
- Option value: {OPTION_NAME}

Goal:
- Not simple translation.
- Convert into Korean market standard wording, unit, and value style.

Rules:
1) Output JSON only: {{"value":"..."}}.
2) Do not output explanation, labels, or extra text.
3) Keep product/model/code tokens unchanged.
4) Normalize full-width digits/symbols to standard forms.
5) Apply Korean ecommerce unit/value conventions when appropriate.
6) Keep numeric meaning and ordering; never invent new values.
7) Size values should use Korean-market practical notation.
8) Color/material/style should be shopper-friendly Korean wording.
9) If conversion is uncertain, return closest safe original form.
"""







# category/matcher/category_llm_prompts.py

CATEGORY_PICK_PROMPT = """
역할:
너는 상품 카테고리 자동매칭 시스템의 보조 판단자다.
이미 점수 계산으로 후보가 좁혀져 있다.
너의 임무는 아래 후보 중
상품과 가장 일치하는 "하나"를 추천하는 것이다.

중요 규칙 (반드시 지켜라):
- 아래 후보 중 하나만 선택하라 (새 후보 생성 금지)
- 전체 카테고리를 분류하려 하지 마라
- 추론, 상상, 일반화로 판단하지 마라
- 보이지 않는 정보는 사용하지 마라
- 감성적 표현, 품질 평가, 기대 표현 금지

이미지 사용 규칙:
- 이미지는 텍스트 정보로 좁혀진 후보를 "확인"하는 용도로만 사용하라
- 이미지에서 직접 보이는 사실만 사용하라
- "~처럼 보인다", "~일 것 같다" 같은 추정 표현 금지
- 이미지로 확인할 수 없는 정보는 사용하지 마라

입력 정보:
[상품명]
{product_name}

[옵션명]
{option_names}

[정제된 상세설명]
{filtered_description}

[카테고리 후보]
{candidate_list}

출력 형식 (엄격):
선택: {{template_key}}
이유: 이미지 또는 텍스트에서 직접 확인 가능한 근거 1문장
"""





CATEGORY_DETAIL_FILTER_PROMPT = """
역할:
너는 상품 상세설명에서
데이터로 활용 가능한 문장만 남기는 정제기다.

목표:
아래 상품설명에서
해당 상품 자체에 직접적으로 속하는 정보만 남기고
그 외 모든 문장은 제거하라.

절대 규칙:
- 요약하지 마라
- 재작성하지 마라
- 문장 표현을 변경하지 마라
- 해석, 판단, 추론을 하지 마라
- 새로운 정보를 추가하지 마라
- 문장은 원문 그대로 유지하거나 완전히 삭제만 하라

남길 문장 기준:
- 상품의 종류 또는 형태를 직접 설명하는 문장
- 상품을 구성하는 소재, 재질, 구성 요소
- 상품의 구조, 설계, 외형적 특징
- 상품에 적용된 기능, 기술, 처리 방식
- 상품에 고유하게 속하는 객관적·물리적 속성

삭제할 문장 기준:
- 주관적 평가, 인상, 감성적 표현
- 사용 상황, 활용 방법, 연출, 조합, 매칭 언급
- 다른 상품, 다른 카테고리, 타 제품과의 관계 언급
- 구매 조건, 판매 방식, 재고, 구매처, 사이즈 제공 방식
- 배송, 세탁, 관리, 주의사항
- 광고, 홍보, 추천 목적의 문장
- 상품 자체를 설명하지 않는 모든 보조적 설명

출력 형식:
- 남은 문장만 원문 그대로 줄바꿈으로 출력
- 제목, 분류명, 추가 설명, 코멘트는 출력하지 마라
"""





ATTRIBUTE_PICK_PROMPT = """
역할:
너는 상품 속성 선택기다.
입력 텍스트에 명시된 정보를
attributes에 정규화하여 매핑한다.

핵심 원칙:
- 이 작업은 추론이 아닌 정보 추출 + 정규화다.
- 입력에 없는 새로운 사실을 추가하면 오답이다.

규칙:
- product_name, option_names, detail_text에
  직접 등장한 표현과,
  동일한 사실을 의미하는 동의어만 선택할 수 있다.
- 동의어는 동일한 사실을 가리키는 경우에만 허용하며,
  그 외는 추론으로 간주하고 금지한다.
- 일반 상식, 의미 확장, 관행, 성질 유추는 모두 금지한다.
- 애매하거나 확실하지 않으면 해당 attribute는 선택하지 않는다.

선택 제한:
- 반드시 전달된 attributes 범위 안에서만 선택한다.
- attributeValues에 없는 값은 절대 생성하지 않는다.
- required=false 인 attribute는
  SINGLE_SELECT 이더라도
  명시적 근거가 없으면 선택하지 않는다.
- SINGLE_SELECT는
  명시 표현 또는 허용된 동의어가 있을 때만 1개 선택한다.
- MULTI_SELECT는
  명시 표현 또는 허용된 동의어만
  maxMatchingCount 이하로 선택한다.
- TEXT 타입은
  입력 텍스트에 실제로 존재하는 문자열 또는
  그와 동일한 의미의 짧은 표현만 반환한다.
  (요약, 의역, 보완 금지)

출력(JSON):
{
  "selections": {
    "<categoryAttributeId>": [<attributeValueSeq>, ...] | "<text>"
  },
  "reason": "입력 텍스트에 등장한 표현 또는 그 동의어만을 근거로 간단히 요약"
}

"""


CAPTCHA_SOLVE_PROMPT = """
질문을 보고, 그에 맞는 '숫자' 정답만 정확히 답변해
말은 하지 말고 오직 '숫자'만 출력해.
질문:
{QUESTION}
"""


PRODUCT_OPTION_GROUP_FILTER_PROMPT = """
너는 상품 옵션 구조 판별기다.

option_groups 중에서
**확실히 상품 변경(SKU/색상/사이즈/모델 등)을 결정하는 그룹만 선택하고, 불확실하면 선택하지 말 것.**

상품 옵션이란:
- 선택에 따라 상품의 색상, 사이즈, 모델, 용량 등 실제 변형이 발생하는 값

hint_keywords는 이 상품의 다른 판매처 실제 옵션 정보의 일부이다.  
**hint와 의미적으로 연결되는 그룹은 매우 강한 옵션 신호다.**

**상품명을 참고하여 해당 상품에서 실제로 선택에 의해 달라질 수 있는 속성과 관련 없는 그룹은 기본적으로 제외하라.**

옵션이 아닌 것:
- 사용자 정보(키, 몸무게, 나이, 성별, 국가, 언어 등)
- 필터/검색/정렬 UI
- 리뷰/평점
- 내비게이션/탭/카테고리 이동
- 상태 메시지

판단 원칙:
- 옵션으로 판단하려면 **상품 변형과 직접 연결된 명확한 근거가 있어야 한다**
- 단어 일부가 유사해도 기능이 설명/이동 목적이면 옵션이 아니다
- 반복 구조, 버튼 형태, 단어 유사성만으로 옵션으로 추론하지 말 것

입력:
[product_title]
{product_title}

[option_groups]
{option_groups}

[hint_keywords]
{hint_keywords}

출력(JSON, 엄격):
{{
  "option_groups": ["01", "02"]
}}
"""


SEARCH_COMPACT_PROMPT = """
You are generating a compact Korean search query for keyword extraction.

Rules:
- Output only one line query text.
- Keep the most important product intent terms.
- Prefer order: brand, core item type, key model token.
- Keep model code like ABC123-456 if present.
- Remove commerce noise and repeated words.
- Maximum length: {MAX_LEN} characters.

brand: {BRAND}
original_name: {ORIGINAL_NAME}
"""


BRAND_CANONICAL_PROMPT = """
You normalize product brand names into one canonical brand string.

Rules:
- Output one line only.
- Output brand name only (no explanation).
- Resolve aliases/language variants to one canonical brand label.
- Always use the brand form most commonly used by Korean shoppers.
- Do not force English if Korean usage is more common.
- If uncertain, return RAW_BRAND unchanged.

RAW_BRAND: {RAW_BRAND}
PRODUCT_NAME: {PRODUCT_NAME}
"""


PRODUCT_OPTION_GROUP_NAME_PROMPT = """
You translate one option group label into the wording most commonly used in Korean e-commerce.

Input:
- Raw group label: {GROUP_NAME}
- Sample option values: {OPTION_VALUES}

Rules:
- Return JSON only: {{"group_name":"..."}}.
- Do not add explanation.
- Infer intent from both label and sample option values.
- Keep it short and practical for shoppers.
"""
