import BaseHandler from "./base_handler.js";

export class HandlerUniqloVN extends BaseHandler {
    async run(mode) {
        await this.autoClosePopups();

        // SPA 렌더링 대기
        await this.sleep(3000);

        await this.capture("uniqlo_vn", mode);
    }

}
