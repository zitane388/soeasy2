import time
import os
import re
import threading
import logging
from typing import List

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait # 최상단으로 이동
from selenium.webdriver.support import expected_conditions as EC # 최상단으로 이동
from webdriver_manager.chrome import ChromeDriverManager
from urllib.parse import urljoin

# 프로젝트 내부 모듈 연동
from llm.llm_client import request_llm_with_image, get_prompt
from naver_best.models import NaverProductItem, NaverVariant
from naver_best.parser import parse_store_html, parse_detail_html

logger = logging.getLogger("naver_best.orchestrator")

class NaverBestOrchestrator:
    def __init__(self, urls_from_store: List[str], stop_event: threading.Event, items_container: List[NaverProductItem]):
        self.urls_from_store = urls_from_store
        self.stop_event = stop_event
        self.items = items_container
        self.is_collecting = False
        self.exit_status = "SUCCESS"
        self.driver = None
        self.max_captcha_retries = 10 # 캡차 최대 10번 시도

    def _status(self, msg: str):
        """UI 상태바 메시지 업데이트"""
        logger.info(f"📢 [STATUS] {msg}")
        # if hasattr(self, "ui"): self.ui.status_var.set(msg)

    def _render_cards(self):
        """UI 카드 렌더링 요청 신호"""
        # if hasattr(self, "ui"): self.ui.queue.put("RENDER")
        pass

    def _refresh_buttons(self):
        """작업 종료 후 UI 버튼 상태 복구 콜백"""
        if hasattr(self, "on_finished_callback") and self.on_finished_callback:
            self.on_finished_callback()

    def _init_driver(self):
        """Selenium 드라이버 초기화 및 봇 탐지 우회 설정 (상세 통신 로그 억제 포함)"""
        import logging
        
        # --- [추가] Selenium 내부의 지저분한 Remote response 로그 억제 ---
        # Remote response: status=200 | data={...} 로그를 차단합니다.
        logging.getLogger("selenium.webdriver.remote.remote_connection").setLevel(logging.WARNING)
        logging.getLogger("urllib3.connectionpool").setLevel(logging.WARNING)
        # -----------------------------------------------------------

        options = webdriver.ChromeOptions()
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        # options.add_argument("--headless") # 필요 시 활성화
        
        # ChromeDriver 설치 및 실행
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        
        # navigator.webdriver 속성 제거로 탐지 우회
        self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"""
        })
        self.driver.implicitly_wait(5)

    def _handle_captcha(self, sidx: int, total_stores: int) -> bool:
        """캡차 해결 시도 및 자동 리다이렉트 대기"""
        for attempt in range(1, self.max_captcha_retries + 1):
            if self.stop_event.is_set(): return False

            captcha_imgs = self.driver.find_elements(By.ID, "rcpt_img")
            if not captcha_imgs:
                return True 

            self._status(f"[{sidx}/{total_stores}] 🚨 캡차 감지! 해결 시도 ({attempt}/{self.max_captcha_retries})")
            
            try:
                question_text = self.driver.find_element(By.ID, "rcpt_info").text
                base64_img_url = captcha_imgs[0].get_attribute("src")

                template = get_prompt("CAPTCHA")
                full_prompt = template.format(QUESTION=question_text)
                
                answer_raw = request_llm_with_image(full_prompt, base64_img_url)
                answer = re.sub(r'[^0-9]', '', answer_raw)
                
                if answer:
                    input_box = self.driver.find_element(By.ID, "rcpt_answer")
                    input_box.clear()
                    input_box.send_keys(answer)
                    self.driver.find_element(By.ID, "cpt_confirm").click()
                    
                    # 🚀 [핵심] 리다이렉트 및 페이지 전환 대기
                    # 정답이 맞으면 캡차 요소가 사라지고 상품 페이지가 로드됩니다.
                    time.sleep(5) 
                    
                    if not len(self.driver.find_elements(By.ID, "rcpt_img")):
                        # 캡차 이미지가 사라졌다면 성공!
                        # 여기서 잠시 더 대기하여 상품 상세 내용이 렌더링될 시간을 줍니다.
                        time.sleep(2) 
                        logger.info("✅ 캡차 통과 및 상품 페이지 진입 성공!")
                        return True
                
                # 실패 시 새로고침하여 새로운 캡차 유도
                logger.warning(f"❌ {attempt}회차 정답 오류. 재시도 중...")
                self.driver.refresh()
                time.sleep(3)
                
            except Exception as e:
                logger.error(f"⚠️ 캡차 로직 에러: {e}")
                self.driver.refresh()
                time.sleep(2)
        
        return True

    # scrapers/naver_best_orchestrator.py

    def collect_list_only(self):
        """[단계 1] 상점 페이지에서 BEST 상품 목록(이름, URL, 대표이미지)만 추출"""
        try:
            self.is_collecting = True
            self.exit_status = "SUCCESS"
            self._init_driver()
            
            total_stores = len(self.urls_from_store)

            for sidx, store_url in enumerate(self.urls_from_store, 1):
                if self.stop_event and self.stop_event.is_set():
                    self.exit_status = "STOPPED"
                    break

                self._status(f"[{sidx}/{total_stores}] 상점 목록 수집 중: {store_url}")
                self.driver.get(store_url)
                time.sleep(3)

                if not self._handle_captcha(sidx, total_stores): continue

                # 스크롤하여 데이터 로드 유도
                self.driver.execute_script("window.scrollTo(0, 1000);")
                time.sleep(1)

                html_source = self.driver.page_source
                best_items_raw = parse_store_html(html_source)
                
                new_items = []
                for it in best_items_raw:
                    raw_href = it.get("href", "")
                    if not raw_href: continue
                    
                    detail_url = urljoin(store_url, raw_href)

                    # 중복 체크
                    if not any(getattr(ex, "best_detail_url", "") == detail_url for ex in self.items):
                        new_items.append(NaverProductItem(
                            name=it.get("name", "상품명 로딩 중..."),
                            best_detail_url=detail_url,
                            images=[it.get("img", "")] if it.get("img") else [],
                            store_url=store_url,
                            is_collected=False
                        ))
                
                self.items.extend(new_items)
                self._render_cards() # UI에 목록 즉시 노출

            self._status("목록 수집 완료. 불필요한 상품 삭제 후 '상세 수집'을 눌러주세요.")

        except Exception as e:
            self._status(f"목록 수집 중 오류: {e}")
        finally:
            self.is_collecting = False
            if self.driver: self.driver.quit()
            self._refresh_buttons()

    def collect_details_only(self):
        """[단계 2] 목록에 있는 상품들의 상세 이미지, 설명, 옵션 수집"""
        try:
            self.is_collecting = True
            self.exit_status = "SUCCESS"
            
            pending = [it for it in self.items if not it.is_collected]
            if not pending:
                self._status("상세 수집할 대상이 없습니다.")
                return

            self._init_driver()
            total_pending = len(pending)

            for didx, item in enumerate(pending, 1):
                if self.stop_event and self.stop_event.is_set():
                    self.exit_status = "STOPPED"
                    break

                self._status(f"상세 수집 중 ({didx}/{total_pending}): {item.name[:15]}")
                self.driver.get(item.best_detail_url)
                
                # 1. 캡차 먼저 해결 (페이지가 완전히 로드된 상태여야 함)
                if not self._handle_captcha(didx, total_pending): continue

                # 2. 옵션 버튼 클릭 (캡차 통과 후 실행)
                try:
                    # 버튼이 나타날 때까지 아주 잠시 대기 (묵시적 대기 활용)
                    option_btn = self.driver.find_element(By.CSS_SELECTOR, "div.KobocOawE2 a._yGBCMWCWu")
                    if option_btn:
                        self.driver.execute_script("arguments[0].click();", option_btn)
                        time.sleep(10.2) # 리스트 렌더링 시간 확보
                except Exception as e:
                    # 옵션이 없는 상품(단일상품)일 경우 에러가 나므로 통과
                    print(f"[DEBUG] 옵션 버튼 없음 또는 클릭 실패(단일상품 가능성): {item.name[:10]}")

                # 3. 상세 데이터 파싱 (한 번만 수행)
                detail_html = self.driver.page_source
                imgs, desc, options, p_name = parse_detail_html(detail_html)
                
                # --- [로그 출력] ---
                print(f"\n--- [DEBUG] {didx}/{total_pending} 상품 수집 데이터 ---")
                print(f"상품명: {p_name}")
                print(f"이미지 개수: {len(imgs) if imgs else 0}")
                print(f"상세설명 길이: {len(desc) if desc else 0}")
                print(f"파싱된 options 원본: {options}")

                # 4. 아이템 모델 업데이트
                if p_name and p_name != "상품명 없음": item.name = p_name
                item.images = imgs if imgs else item.images
                item.description = desc
                
                if options:
                    # 여기서 이미 {그룹명: 옵션명} 구조로 데이터를 생성합니다.
                    variant_list = [NaverVariant(option_map={opt.get('group', '옵션'): v}) 
                                    for opt in options for v in opt.get('items', [])]
                    
                    # 리스트가 비어있을 경우를 대비한 그룹명 추출
                    g_name = options[0].get('group', '옵션') if options else "옵션"
                    item.variants = variant_list if variant_list else [NaverVariant(option_map={g_name: "단일상품"})]
                    
                    # [중요] 리스트 출력 시 "그룹명: 옵션명"이 모두 보이도록 반복문 추가
                    print(f"변환된 variants 개수: {len(item.variants)}")
                    for v in item.variants:
                        for g, val in v.option_map.items():
                            print(f"💡 {g}: {val}") # 여기서 '색상: 블랙' 형태로 출력됨
                else:
                    # 옵션이 아예 없는 경우
                    item.variants = [NaverVariant(option_map={"기본": "단일상품"})]
                    print("💡 기본: 단일상품")
                
                item.is_collected = True
                self._render_cards() # UI 갱신

            self._status("모든 상세 정보 수집 완료!")

        except Exception as e:
            print(f"[ERROR] 상세 수집 중 예외 발생: {e}")
            self._status(f"상세 수집 중 오류: {e}")
        finally:
            self.is_collecting = False
            if self.driver: self.driver.quit()
            self._refresh_buttons()