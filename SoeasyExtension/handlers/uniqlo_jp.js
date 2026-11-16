import BaseHandler from "./base_handler.js";

export class HandlerUniqloJP extends BaseHandler {

    async run(mode){
        await this.autoClosePopups();

        if (mode === "RAW") {
            await this.openSizeChart();
        }

        await this.capture("uniqlo_jp", mode);
    }

    async openSizeChart(){
        // SPA 안정화 대기
        await this.sleep(3000);

        const nodes = document.querySelectorAll(
            "div[data-testid='ITOTypography']"
        );

        for (const el of nodes) {
            if (el.textContent.trim() === "サイズを確認する") {
                console.log("📐 사이즈표 버튼 클릭:", el);
                el.click();
                return;
            }
        }

        console.warn("⚠ 사이즈표 버튼을 찾지 못함");
    }
}
