// 전설로 떠나는 투자자 추천종목: 인터넷이 없어도 마지막으로 본 화면이 열리게 하는 서비스워커.
// 인터넷이 되면 항상 최신 화면(추천 갱신 반영)을 받고, 안 되거나 6초 안에 응답이 없으면 저장본을 쓴다.
const C = "legend-v3", PAGE = "./";
self.addEventListener("install", e => {
  e.waitUntil(caches.open(C).then(c => c.addAll([PAGE, "manifest.json", "icon-192.png", "icon-512.png"])).catch(() => {}));
  self.skipWaiting();
});
self.addEventListener("activate", e => {
  e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== C).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener("fetch", e => {
  const r = e.request, u = new URL(r.url);
  // 웹폰트(Pretendard): 한 번 받으면 저장해 두고 오프라인에서도 같은 글꼴로 보이게 한다
  if (r.method === "GET" && u.hostname === "cdn.jsdelivr.net") {
    e.respondWith(caches.match(r).then(m => m || fetch(r).then(res => { if (res.ok || res.type === "opaque") { const cp = res.clone(); caches.open(C).then(c => c.put(r, cp)); } return res; })));
    return;
  }
  if (r.method !== "GET" || u.origin !== location.origin) return;
  const nav = r.mode === "navigate" || /\/(index\.html)?$/.test(u.pathname);
  const key = nav ? PAGE : r;
  const net = (nav ? fetch(u.origin + u.pathname + u.search, { cache: "no-cache" }) : fetch(r)).then(res => {
    if (res.ok) { const cp = res.clone(); caches.open(C).then(c => c.put(key, cp)); }
    return res;
  });
  const saved = caches.match(key);
  e.respondWith(new Promise(done => {
    let over = false;
    const use = m => { if (!over) { over = true; done(m); } };
    const t = setTimeout(() => saved.then(m => m && use(m)), 6000);
    net.then(res => { clearTimeout(t); use(res); })
       .catch(() => { clearTimeout(t); saved.then(m => use(m || Response.error())); });
  }));
});
