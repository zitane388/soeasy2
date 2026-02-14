import BaseHandler from "./base_handler.js";

export class HandlerMujiJP extends BaseHandler {

    async run(mode) {
        // 1. 공통 초기화 (팝업 닫기 및 안정화)
        await this.autoClosePopups();
        await this.sleep(3000);

        // 2. 모드별 분기 처리
        if (mode === "SIZE_CHART") {
            // 사이즈표 수집 모드: 탭을 클릭하여 상세설명을 포기하고 사이즈표를 노출시킴
            console.log("📏 [MODE: SIZE_CHART] 사이즈표 탭으로 전환합니다.");
            const success = await this.openSpecsTab();
            if (!success) {
                console.warn("⚠ 사이즈표 탭 전환 실패");
            }
        } else if (mode === "RAW") {
            // 기본 데이터 수집 모드: 탭 이동 없이 첫 화면(상세설명 포함)을 유지함
            console.log("📝 [MODE: RAW] 기본 상세 페이지 정보를 유지합니다.");
        }

        // 3. 캡처 진행 (파일명에 모드를 붙여 구분하면 관리가 쉽습니다)
        const fileName = mode === "SIZE_CHART" ? "muji_jp_size" : "muji_jp";
        await this.capture(fileName, mode);
    }

    /**
     * '仕様・サイズ' (사양/사이즈) 탭 클릭 로직
     */
    async openSpecsTab() {
        // 텍스트 기반 탐색
        const buttons = document.querySelectorAll("button.Tab_button__MlAG2");
        for (const btn of buttons) {
            if (btn.textContent.trim().includes("仕様・サイズ")) {
                btn.click();
                await this.sleep(2000); // 탭 전환 후 테이블 렌더링 시간 확보
                return true;
            }
        }

        // data-testid 기반 탐색 (Fallback)
        const tabNode = document.querySelector("li[data-testid='tab-2'] button");
        if (tabNode) {
            tabNode.click();
            await this.sleep(2000);
            return true;
        }

        return false;
    }
}