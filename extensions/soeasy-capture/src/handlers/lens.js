import BaseHandler from "./base_handler.js";

export class HandlerLens extends BaseHandler {

    async run(mode) {
        mode = mode?.toLowerCase();
        console.log("🟡 [LENS] mode =", mode);

        if (mode === "lens_init") {
            await this.waitForResults();
            await this.clickProductsTab();
            return;
        }

        if (mode === "lens_products") {
            await this.waitForResults();
            await this.scrollToBottom();
            await this.capture("lens", "lens_products");
        }
    }

    async waitForResults() {
        for (let i = 0; i < 20; i++) {
            if (document.querySelectorAll('div[role="listitem"]').length > 5) return;
            await this.sleep(500);
        }
    }

    async clickProductsTab() {
        console.log("🔎 Products 탭 찾는 중");

        const spans = document.querySelectorAll('span.R1QWuf');

        for (const span of spans) {
            if (span.textContent.trim().toLowerCase() === "products") {
                const link = span.closest("a");
                if (!link) continue;

                console.log("🟢 Products 탭 클릭");
                link.click();

                await this.sleep(4000);

                window.__SOEASY2_RUNNING_MODE__ = null;
                sessionStorage.setItem(
                    "SOEASY2_SESSION",
                    JSON.stringify({ site: "lens", mode: "lens_products" })
                );
                location.reload();
                return;
            }
        }

        console.warn("⚠ Products 탭 못찾음");
    }


    async scrollToBottom() {
        let lastHeight = 0;
        for (let i = 0; i < 20; i++) {
            window.scrollTo(0, document.body.scrollHeight);
            await this.sleep(1200);
            const h = document.body.scrollHeight;
            if (h === lastHeight) return;
            lastHeight = h;
        }
    }
}
