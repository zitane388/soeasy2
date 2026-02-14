import BaseHandler from "./base_handler.js";

export class HandlerSuperSportsJP extends BaseHandler {
    async run(mode) {
        await this.autoClosePopups();
        await this.sleep(2500);
        await this.capture("supersports_jp", mode);
    }
}

