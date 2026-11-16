chrome.runtime.onMessage.addListener((msg, sender) => {
    
    console.log("📩 [BACKGROUND] message received:", msg);

    if (msg.cmd !== "SOEASY2_CAPTURE") return;

    // intent 삭제 → mode만 사용
    const mode = msg.mode;
    const site = msg.site;

    console.log(`🚀 MODE=${mode}  SITE=${site}`);

    // Flask로 전달 (intent 제거)
    fetch("http://127.0.0.1:5001/receive_scraped_html", {
        method:"POST",
        headers:{ "Content-Type":"application/json" },
        body:JSON.stringify(msg) // intent 필드 없음
    });

    if (sender?.tab?.id) chrome.tabs.remove(sender.tab.id);
});
