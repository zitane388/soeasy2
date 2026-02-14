# Parser Onboarding (Minimal Input)

새 사이트 파서를 추가할 때 아래 3가지만 전달하면 됩니다.

1. `sample_urls` 3개
- 정상 상품 2개
- 옵션 복잡/품절 케이스 1개

2. 아래 둘 중 하나
- `html_blocks` 1세트
  - selector를 모르더라도, 해당 태그 구간 HTML + 용도 설명 제공
- 또는 `dom_snapshots` 1세트
  - 클릭 전/후 DOM 노드 outerHTML 제공 (가격/옵션 버튼)

3. 동적 옵션 증거 1개 이상
- `HAR` 1개, 또는 `initial_data_scripts` + `dom_snapshots`
- 실제 옵션 선택 시 요청/응답이 포함된 HAR 파일
- 동적 가격/재고/SKU/조합 유효성/이미지 매핑 복원에 사용

---

## 파일 작성 순서

1. `parsers/product_pages/parser_onboarding_template.json` 복사
2. 파일명 예시: `parsers/product_pages/onboarding_specs/brand_country.json`
3. 템플릿 필드를 채운다.
4. HAR 파일 경로를 `har_file`에 넣는다.

---

## 필드 설명

- `brand`: 내부 브랜드 키 (예: `uniqlo`, `muji`)
- `country`: 국가 코드 (예: `jp`, `vn`, `us`)
- `sample_urls`: 대표 URL 3개
- `mode`: `html_blocks` 또는 `dom_snapshots` (참고용)
- `html_blocks`: selector 대신 제공하는 HTML 태그 구간
  - `block_name`: 블록 키
  - `purpose`: 블록 용도 (상품명/가격/옵션/이미지/상세설명)
  - `html`: 실제 HTML 조각
- `initial_data_scripts`: 페이지 초기 상태 스크립트 블록
  - `script_name`: 예 `__NEXT_DATA__`, `ld_json`
  - `purpose`: 용도
  - `html`: script 전체 태그
- `dom_snapshots`: 옵션 클릭 전/후 DOM 스냅샷
  - `snapshot_name`: 키 이름
  - `action`: 어떤 클릭 상태인지 설명
  - `html`: 노드 outerHTML
- `har_file`: HAR 파일 경로 (있으면 최우선 사용)

---

## HAR 파일이란?

- 브라우저 개발자도구 Network 기록 파일(`.har`)
- 옵션 클릭 시 발생한 요청/응답(JSON 포함)을 담고 있음
- 이 파일로 조합 유효성, 옵션별 가격/재고/SKU, 이미지 매핑을 복원함

Chrome 기준 추출:
1. `F12` -> `Network`
2. `Preserve log` 체크
3. 옵션(색상/사이즈 등) 2~3회 클릭
4. 목록 우클릭 -> `Save all as HAR with content`
5. 저장 경로를 `har_file`에 입력

---

## HAR 없이 추출하는 법 (대체 경로)

1. `initial_data_scripts` 추출
- `Elements` 탭 -> `Ctrl+F` -> `__NEXT_DATA__` 검색
- `<script id=\"__NEXT_DATA__\" ...>` 우클릭 -> `Copy element`

2. `dom_snapshots` 추출
- 옵션 선택 전 가격 노드 우클릭 -> `Inspect` -> `Copy outerHTML` (`price_before`)
- 옵션 변경 후 같은 가격 노드 `Copy outerHTML` (`price_after`)
- 옵션 버튼도 선택 전/후 같은 방식으로 각각 복사 (`option_before`, `option_after`)

---

## 빠른 체크리스트

- [ ] URL 3개가 실제로 열리는지
- [ ] `html_blocks` / `dom_snapshots` 중 하나가 채워졌는지
- [ ] `har_file` 또는 `initial_data_scripts/dom_snapshots`가 있는지
- [ ] 가격/재고/SKU 복원 가능한 증거가 있는지


## ??? ?? ??
- `html_blocks`? `block_name: "brand_area"`? ??
- `html`? ???? ??? ?? ??? ??? ???.

## model number tag input
- Put it in `html_blocks` with `block_name: "model_area"`.
- Example html: `<div class="model-number">HM6803-109</div>`.
