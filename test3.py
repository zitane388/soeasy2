import os
import re
from bs4 import BeautifulSoup
from collections import Counter

import asyncio
from playwright.sync_api import sync_playwright

def get_universal_score(container, items, hint_keywords):
    score = 0
    match_details = []
    container_html = str(container).lower()
    container_text = container.get_text(separator=' ', strip=True).lower()
    
    review_signals = ['review', 'stars', 'votes', 'days ago', 'helpful']
    if sum(w in container_text for w in review_signals) >= 2:
        return -2000, []

    ui_noise = ['carousel', 'search', 'nav', 'menu', 'arrow', 'slide', 'pause', 'play']
    if any(word in container_html for word in ui_noise):
        return -1000, []

    unit_pattern = r'\b\d+(\.\d+)?\s*(lbs|lb|kg|g|oz|oz\.)\b'
    unit_matches = re.findall(unit_pattern, container_text)
    
    if len(unit_matches) >= 2:
        score += 500
        match_details.append(f"Units Found ({len(unit_matches)})")

    for hint in hint_keywords:
        if hint.lower() in container_text:
            score += 100
            match_details.append(f"Hint({hint})")

    interactive = container.find_all(['button', 'input', 'label', 'a'])
    if len(interactive) >= len(items):
        score += 200

    return score, match_details


def find_best_options(file_path, label_hints, value_hints):
    print(f"\n🚀 분석 시작: {os.path.basename(file_path)}")
    print(f"🎯 레이블 힌트: {label_hints} | 값 힌트: {value_hints}")
    print("="*80)

    if not os.path.exists(file_path):
        print(f"❌ [에러] 파일을 찾을 수 없습니다: {file_path}")
        return []

    with open(file_path, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), 'html.parser')

    # [Step 1] 상품명 앵커 찾기
    title_node = soup.find('h1') or soup.find('h2')
    if not title_node:
        print("❌ [중단] 상품명(h1/h2)을 찾을 수 없습니다.")
        return []
    
    product_title = title_node.get_text(strip=True)
    print(f"📍 앵커 포인트 발견: <{title_node.name}> - '{product_title[:30]}...'")

    # [Step 2] 상품 정보 블록 확정 (상향 탐색)
    anchor_block = title_node
    for i in range(1, 4):
        p = anchor_block.parent
        if not p or p.name in ['body', 'html', 'main', 'nav', 'header']: break
        anchor_block = p
        p_identity = (str(p.get('class', '')) + str(p.get('id', ''))).lower()
        if any(word in p_identity for word in ['product-info', 'title-container', 'header-section']): break

    # [Step 3] 전략적 단계별 확장 탐색
    final_candidates = []
    current_scope = anchor_block
    
    for attempt in range(4):
        if attempt > 0:
            if not current_scope.parent or current_scope.parent.name in ['body', 'html', 'nav']: break
            current_scope = current_scope.parent
        
        print(f"\n🔍 [확장 시도 {attempt}] 범위: <{current_scope.name}>")
        
        step_candidates = []
        containers = current_scope.find_all(['div', 'ul', 'fieldset'])
        
        for idx, container in enumerate(containers):
            all_text = container.get_text(" ", strip=True)
            
            # 레이블 매칭
            matched_labels = [h for h in label_hints if re.search(rf"\b{re.escape(h)}\b", all_text, re.I)]
            
            # 가격($) 기호가 있어도 레이블 힌트가 있으면 통과 (월마트 대응)
            if "$" in all_text and not matched_labels:
                continue

            if matched_labels:
                # 하부 반복 구조 탐색
                for sub in container.find_all(['div', 'ul'], recursive=True):
                    subs = [c for c in sub.find_all(recursive=False) if c.name not in ['script', 'style', 'br']]
                    if len(subs) < 2: continue
                    
                    patterns = [f"{c.name}.{'.'.join(sorted(c.get('class', [])))}" for c in subs]
                    most_common, count = Counter(patterns).most_common(1)[0]
                    rep_score = count / len(subs)
                    
                    if rep_score >= 0.7:
                        sub_text = sub.get_text(" ", strip=True)
                        matched_values = [v for v in value_hints if re.search(re.escape(v), sub_text, re.I)]
                        has_swatch = sub.find(attrs={"data-testid": "vt-swatch"}) is not None

                        if matched_values or has_swatch:
                            step_candidates.append({
                                'container': sub,
                                'matched_labels': matched_labels,
                                'matched_count': len(matched_labels) + (len(matched_values) if matched_values else 1),
                                'html': str(sub)
                            })
                            break 

        # [Step 4] 중복 제거 및 최종 검증 텍스트 로그 출력
        if step_candidates:
            # 품질 점수 계산 및 정렬
            for cand in step_candidates:
                item_count = len(cand['container'].find_all(recursive=False))
                cand['quality_score'] = (cand.get('matched_count', 0) * 15) + (item_count * 2)
            
            step_candidates.sort(key=lambda x: x['quality_score'], reverse=True)
            
            # 중복 제거 (포함 관계 확인)
            unique_results = []
            for cand in step_candidates:
                if not any(cand['html'] in f['html'] or f['html'] in cand['html'] for f in unique_results):
                    unique_results.append(cand)

            # --- [핵심: 검증용 전체 텍스트 로그] ---
            print(f"\n" + "="*80)
            print(f"🔍 [최종 검증] 탐지된 {len(unique_results[:3])}개 구역의 전체 화면 텍스트")
            print(f"📍 대상 상품: {product_title}")
            print("="*80)

            for i, cand in enumerate(unique_results[:3], 1):
                # 자식 요소들 사이를 ' | '로 구분하여 시각화
                raw_visible_text = cand['container'].get_text(" | ", strip=True)
                
                print(f"\n[구역 #{i}] --------------------------------------------------")
                print(f"📌 위치 점수: {cand['quality_score']}")
                print(f"🏷️ 감지된 키워드: {cand['matched_labels']}")
                print(f"📝 화면 표시 텍스트 전체:")
                print(f">>> {raw_visible_text}")
                print("-" * 80)
            
            final_candidates = unique_results[:3]
            break

    return final_candidates


import copy

def structure_options(container):
    structured_data = []
    
    # 1. 직계 자식(recursive=False)만 검사하여 '라벨'과 '옵션그룹'을 구조적으로 분리
    direct_children = [c for c in container.find_all(recursive=False) if c.name not in ['script', 'style']]
    if not direct_children: return []

    # 2. 각 자식의 '구조 시그니처' 생성 (SVG 등 내부 노이즈 포함 여부 판단)
    child_structures = []
    for child in direct_children:
        inner_tags = "_".join([t.name for t in child.find_all(True)])
        signature = f"{child.name}|{inner_tags}"
        child_structures.append(signature)

    stats = Counter(child_structures)
    if not stats: return []
    most_common_sig, count = stats.most_common(1)[0]

    seen_values = set()
    for i, child in enumerate(direct_children):
        current_sig = child_structures[i]
        
        text_content = child.get_text(strip=True)
        if count > 1 and current_sig != most_common_sig and not text_content:
            continue

        # --- [보정 1] SVG 텍스트 오염 방지 ---
        # SVG 내부의 <title>Check Icon</title> 등이 get_text()에 잡히지 않도록 
        # 복사본에서 SVG를 제거한 후 텍스트를 추출합니다.
        temp_child = copy.copy(child)
        for svg in temp_child.find_all('svg'):
            svg.decompose()
        
        raw_text = temp_child.get_text(separator=" ", strip=True)
        
        # 텍스트가 부족하면 원본(child)의 이미지/속성에서 보충
        if not raw_text or len(raw_text) < 2:
            img = child.find('img')
            if img:
                raw_text = img.get('alt') or img.get('title') or ""
            elif child.get('title'):
                raw_text = child.get('title')
            elif child.get('aria-label'):
                raw_text = child.get('aria-label')

        clean_val = " ".join(raw_text.split()).strip()
        
        # 만약 여전히 'Check Icon' 같은 단어가 포함되어 있다면 제거 (2차 방어)
        clean_val = re.sub(r'(Check Icon|Close Icon|Arrow Icon|SVG Icon)', '', clean_val, flags=re.I).strip()
        
        if not clean_val or clean_val in seen_values or len(clean_val) > 50:
            continue

        # --- [보정 2] 정밀한 품절 판별 ---
        # SVG 내부의 클래스(path class="disabled")에 낚이지 않도록 항목(child) 자체의 속성을 우선합니다.
        # 1. 태그 속성 (disabled, aria-disabled)
        is_disabled_attr = child.has_attr('disabled') or child.get('aria-disabled') == 'true'
        
        # 2. 항목 자체의 클래스명 (li class="out-of-stock" 등)
        item_class = " ".join(child.get('class', [])).lower()
        is_disabled_class = any(x in item_class for x in ['disabled', 'out-of-stock', 'soldout'])
        
        # 3. 텍스트에 명시적인 품절 문구가 있는 경우
        # SVG가 제거된 raw_text를 기준으로 검사하여 오판 방지
        is_soldout_text = any(x in raw_text.lower() for x in ['out of stock', '품절', 'unavailable'])
        
        is_available = not (is_disabled_attr or is_disabled_class or is_soldout_text)
        
        structured_data.append({
            'option_text': clean_val, 
            'element': child, 
            'is_available': is_available
        })
        seen_values.add(clean_val)

    return structured_data

def print_structured_options(results, hint_keywords):
    if not results:
        print("\n❌ 추출된 옵션 데이터가 없습니다.")
        return
    print("\n" + "="*70)
    print(f"🎯 최종 옵션 분석 결과 (탐지 키워드: {', '.join(hint_keywords)})")
    print("="*70)
    for i, res in enumerate(results[:2], 1):
        options = structure_options(res['container'])
        if not options: continue
        print(f"\n[후보 {i}] 구조 패턴: {res.get('pattern', 'Unknown')}")
        print(f"{'No.':<5} | {'Option Text':<20} | {'Status':<12} | {'Tag'}")
        print(f"{'-' * 60}")
        for idx, opt in enumerate(options, 1):
            status = "Available" if opt['is_available'] else "SOLD OUT"
            display_text = (opt['option_text'][:18] + '..') if len(opt['option_text']) > 20 else opt['option_text']
            print(f"{idx:<5} | {display_text:<20} | {status:<12} | <{opt['element'].name}>")
        print(f"{'-' * 60}")

if __name__ == "__main__":
    TARGET_FILE = "test_html/walmart.html"
    # OPTION_HINTS = ["color", "GREEN", "XXS", "XS"]
    # OPTION_HINTS = ["color", "Olive", "XXS", "XS"]
    # OPTION_HINTS = ["color", "charcoal"]
    # OPTION_HINTS = ["Weight"]
    # OPTION_VALUE_HINTS = ["15", "lbs"]
    OPTION_HINTS = ["color", "size", "classic red", "Black Soot", "xxs"]
    OPTION_VALUE_HINTS = ["classic red", "Black Soot", "xxs", "s"]
    
    print(f"🔍 '{TARGET_FILE}' 정밀 분석 로그")
    final_results = find_best_options(TARGET_FILE, OPTION_HINTS, OPTION_VALUE_HINTS)
    
    print_structured_options(final_results, OPTION_HINTS)