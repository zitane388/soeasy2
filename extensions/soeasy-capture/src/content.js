// ==============================
//   SOEASY2 CONTENT SCRIPT MAIN
// ==============================
(async () => {

    console.log("[SOEASY2][BOOT]");
    console.log("[SOEASY2] location.href =", location.href);
    console.log("[SOEASY2] location.search =", location.search);
    console.log("[SOEASY2] location.hash =", location.hash);

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
    const { HandlerSuperSportsJP } = await import(
        chrome.runtime.getURL("handlers/supersports_jp.js")
    );
    const { HandlerLens } = await import(
        chrome.runtime.getURL("handlers/lens.js")
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
            muji_jp: new HandlerMujiJP(),
            supersports_jp: new HandlerSuperSportsJP(),
            lens: new HandlerLens(),
        }[site] ?? null;
    }


    // ==============================
    //  3) URL 파라미터 파싱
    // ==============================
    const params = new URLSearchParams(location.search);

    // hash 파라미터 병합
    if (location.hash && location.hash.includes("=")) {
        const hashParams = new URLSearchParams(location.hash.slice(1));
        hashParams.forEach((v, k) => {
            if (!params.has(k)) params.set(k, v);
        });
    }

    console.log("🔍 URL Params:", Object.fromEntries(params.entries()));

    let site = params.get("site");
    let mode = params.get("mode");

    if (site) site = site.toLowerCase();
    if (mode) mode = mode.toLowerCase();

    // 🔥 URL에 없으면 세션에서 복구
    if (!site || !mode) {
        const s = sessionStorage.getItem("SOEASY2_SESSION");
        if (s) {
            const data = JSON.parse(s);
            site = data.site;
            mode = data.mode;
            console.log("♻ 세션에서 복구:", site, mode);
        }
    }


    console.log(`📌 SITE=${site}  MODE=${mode}`);


    // ==============================
    //  4) program 검증 (세션 있으면 통과)
    // ==============================
    const hasProgram = params.get("program") === "SOEASY2";

    if (mode !== "size" && !hasProgram && !sessionStorage.getItem("SOEASY2_SESSION")) {
        console.log("❌ program=SOEASY2 아님 → 종료");
        return;
    }

    // 🔥 세션 저장 (최초 진입 또는 복구 후 유지)
    sessionStorage.setItem(
        "SOEASY2_SESSION",
        JSON.stringify({ site, mode })
    );



    // ==============================
    //  5) Handler 실행
    // ==============================

    // 🔥 mode 기준 중복 실행 방지
    if (window.__SOEASY2_RUNNING_MODE__ === mode) {
        console.log("⚪ 동일 mode 중복 실행 차단");
        return;
    }
    window.__SOEASY2_RUNNING_MODE__ = mode;

    const handler = getHandler(site);
    if (!handler) {
        console.log("❌ Handler 없음 → 종료");
        return;
    }

    console.log(`🚀 Handler.run 실행 → ${site} / ${mode}`);
    await handler.run(mode);

    console.log("🟦 Handler.run 정상 종료");



})();
