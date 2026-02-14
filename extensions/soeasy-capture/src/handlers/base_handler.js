export default class BaseHandler{

    sleep(ms){ return new Promise(r=>setTimeout(r,ms)); }

    async autoClosePopups(){
        console.log("🧹 팝업 제거 시작");

        const selectors=[
            "#onetrust-accept-btn-handler",
            "[data-testid='uc-accept-all-button']",
            "button[aria-label*='accept' i]",
            "button[aria-label*='close' i]",
            ".modal-close",".overlay .close",
            ".cookie-consent",".cookie-modal"
        ];

        let count=0;
        selectors.forEach(sel=>{
            document.querySelectorAll(sel).forEach(btn=>{
                try{ btn.click(); count++; }catch{}
            });
        });
        console.log(`🧹 팝업 제거 완료 → ${count}개`);
    }

    capture(site,mode){
        console.log(`📤 CAPTURE 실행 site=${site} mode=${mode}`);
        chrome.runtime.sendMessage({
            cmd:"SOEASY2_CAPTURE",
            site,mode,
            url:location.href,
            html:document.documentElement.outerHTML
        },()=>console.log("📨 Background 전달 완료"));
    }
}
