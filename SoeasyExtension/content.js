// ==============================
//   SOEASY2 CONTENT SCRIPT MAIN
// ==============================
(async () => {

    console.log("[SOEASY2][BOOT]");
    console.log("[SOEASY2] location.href =", location.href);
    console.log("[SOEASY2] location.search =", location.search);
    console.log("[SOEASY2] location.hash =", location.hash);

    // 중복 실행 방지
    if (window.__SOEASY2__) {
        console.log("⚪ 중복 실행 차단됨");
        return;
    }
    window.__SOEASY2__ = true;

    console.log("🟢 [CONTENT] 실행됨");

    // ==============================
    //  1) Handler 모듈 로드
    // ==============================
    console.log("📥 Handler 모듈 로딩 시작");

    const { HandlerUniqloJP } = await import(
        chrome.runtime.getURL("handlers/uniqlo_jp.js")
    );
    const { HandlerGUJP } = await import(
        chrome.runtime.getURL("handlers/gu_jp.js")
    );
    const { HandlerUniqloVN } = await import(
        chrome.runtime.getURL("handlers/uniqlo_vn.js")
    );
    const { HandlerMujiJP } = await import(
        chrome.runtime.getURL("handlers/muji_jp.js")
    );


    console.log("🔥 Handler 모듈 정상 로드 완료");

    // ==============================
    //  2) Handler 선택
    // ==============================
    function getHandler(site) {
        return {
            uniqlo_jp: new HandlerUniqloJP(),
            gu_jp: new HandlerGUJP(),
            uniqlo_vn: new HandlerUniqloVN(),
            muji_jp: new HandlerMujiJP()
        }[site] ?? null;
    }


    // ==============================
    //  3) URL 파라미터 파싱
    // ==============================
    const params = new URLSearchParams(location.search);

    // hash 파라미터 병합 (RAW / COLOR 대응)
    if (location.hash && location.hash.includes("=")) {
        const hashParams = new URLSearchParams(location.hash.slice(1));
        hashParams.forEach((v, k) => {
            if (!params.has(k)) {
                params.set(k, v);
            }
        });
    }

    console.log("🔍 URL Params:", Object.fromEntries(params.entries()));

    const site = params.get("site");
    const mode = params.get("mode");

    console.log(`📌 SITE=${site}  MODE=${mode}`);

    // ==============================
    //  4) program 검증
    //     ⚠ SIZE 페이지는 예외
    // ==============================
    if (mode !== "SIZE" && params.get("program") !== "SOEASY2") {
        console.log("❌ program=SOEASY2 아님 → 종료");
        return;
    }

    // ==============================
    //  5) Handler 실행
    // ==============================
    const handler = getHandler(site);
    if (!handler) {
        console.log("❌ Handler 없음 → 종료");
        return;
    }

    console.log(`🚀 Handler.run 실행 → ${site} / ${mode}`);
    await handler.run(mode);

    console.log("🟦 Handler.run 정상 종료");

})();
