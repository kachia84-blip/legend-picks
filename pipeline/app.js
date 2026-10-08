/* 전설로 떠나는 투자자 추천종목 — 화면 로직 (build.py 가 template.html 의 APP 자리표시자 위치에 이 파일을 넣는다) */
const TONES = {strong:"강력 매수 후보", buy:"매수 후보", wait:"훌륭한 기업 · 가격 부담", hold:"보통 · 관찰", pass:"부적합"};
const TONE_COLOR = {strong:"var(--strong)", buy:"var(--buy)", wait:"var(--wait)", hold:"var(--hold)", pass:"var(--pass)"};
const ICONS = {
  home:'<path d="M3 11l9-8 9 8v9a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z"/>',
  list:'<path d="M4 6h16M4 12h16M4 18h10"/>',
  star:'<polygon points="12 3 14.8 9 21.5 9.8 16.5 14.3 17.9 21 12 17.6 6.1 21 7.5 14.3 2.5 9.8 9.2 9"/>',
  book:'<path d="M5 4h11a3 3 0 0 1 3 3v13H8a3 3 0 0 1-3-3z"/><path d="M5 17a3 3 0 0 1 3-3h11"/>',
  info:'<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7.5v.01"/>',
  tag:'<path d="M20.6 13.4l-7.2 7.2a2 2 0 0 1-2.8 0L3 13V3h10l7.6 7.6a2 2 0 0 1 0 2.8z"/><circle cx="7.5" cy="7.5" r="1.4"/>'
};
const TABS = [["home","홈","home"],["list","종목","list"],["tags","태그","tag"],["watch","관심","star"],["about","더보기","info"]];   // 투자자 소개는 '더보기' 안에 둔다
const TONES_COIN = {strong:"강력 매수 신호", buy:"매수 신호", wait:"진입 대기", hold:"관망", pass:"신호 없음"};
const GROUPS_STOCK = ["growth","value","mixed","chart"], GROUPS_COIN = ["ctrend","cbreak","crev"];
const st = {view:"home", inv:0, market:"us", tone:"all", only:"all", tags:[], sort:"score", q:"", sheet:null, sheetInv:0, seq:[], detailErr:false, fold:{}};
const $ = id => document.getElementById(id);
const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));

/* 데이터 복원: 종목 기본 정보는 한 번만 저장돼 있어 투자자별 목록과 합친다 (용량 절약) */
const BY_ID = Object.fromEntries(DATA.investors.map((v,i) => [v.id, i]));
const TONE_CODES = ["strong","buy","wait","hold","pass"];
DATA.investors.forEach(v => {
  v.stocks = v.stocks.map(it => {
    const s = {...DATA.stocks[it.t], ...it, ticker: it.t, summary: "", checks: []};
    const TL = v.domain === "coin" ? TONES_COIN : TONES;
    s.verdict = it.verdict ?? TL[it.tone];
    if(it.votes){
      s.votes = it.votes.map(([i, score, quality, tc]) => {
        const x = DATA.investors[BY_ID[(v.vote_ids || DATA.invIds)[i]]], tone = TONE_CODES[tc];
        return {id: x.id, name: x.name, mono: x.mono, group: x.group, score, quality, tone, verdict: TL[tone]};
      });
      s.backers = s.votes.filter(x => x.tone === "strong" || x.tone === "buy").map(x => x.mono);
    }
    return s;
  });
});
/* 인덱스 */
const IDX = DATA.investors.map(v => new Map(v.stocks.map(s => [s.ticker, s])));

/* 종목 상세(체크리스트·요약)는 무거워서 투자자별 파일로 나눠 두고, 필요할 때 한 번만 불러온다 */
const DETAIL = {};
function loadDetail(i){
  const v = DATA.investors[i];
  if(v.detailLoaded) return Promise.resolve(true);
  if(!DETAIL[v.id]){
    DETAIL[v.id] = fetch(`data/${v.id}.json`).then(r => { if(!r.ok) throw new Error(r.status); return r.json(); })
      .then(d => {
        IDX[i].forEach((s, t) => { const x = d[t]; if(!x) return; s.summary = x.s;
          s.checks = x.c.map(([name, g, points, max, ok, detail]) => ({name, group: g === "q" ? "quality" : "price", points, max, ok: ok === null ? null : !!ok, detail})); });
        v.detailLoaded = true; return true;
      })
      .catch(() => { delete DETAIL[v.id]; return false; });
  }
  return DETAIL[v.id];
}
const inv = () => DATA.investors[st.inv];
const sinv = () => DATA.investors[st.sheetInv];
const isCons = v => !!v.consensus;
const isAllCons = v => isCons(v) && v.group === "all";
const rankKey = s => s.rank ?? s.score;
/* 주식 / 코인 영역: 시장 탭(미국·한국·코인)에 따라 쓰는 평가자(투자 거장 ↔ 매매이론)가 달라진다 */
const dom = () => st.market === "coin" ? "coin" : "stock";
const isCoin = s => s.market === "coin";
const groupsNow = () => dom() === "coin" ? GROUPS_COIN : GROUPS_STOCK;
const tones = () => dom() === "coin" ? TONES_COIN : TONES;
const defaultInv = d => BY_ID[d === "coin" ? "call" : "all"];
const members = g => DATA.investors.filter(x => !isCons(x) && x.domain === dom() && (!g || x.group === g));
/* 종목 찾기: 주식·코인 종합 목록에서 (관심종목·상세 화면용) */
const baseOf = t => IDX[BY_ID.all].get(t) || (BY_ID.call !== undefined && IDX[BY_ID.call].get(t)) || null;
function setMarket(m){
  st.market = m; st.tone = "all"; st.tags = [];
  if(DATA.investors[st.inv].domain !== dom()) st.inv = defaultInv(dom());
}

/* 공유: 사이트 링크 복사 / 기기 공유 시트 */
const SITE_URL = "https://kachia84-blip.github.io/legend-picks/";
async function copyLink(){
  try{ await navigator.clipboard.writeText(SITE_URL); toast("링크를 복사했어요 🔗"); }
  catch(e){
    const ta = document.createElement("textarea"); ta.value = SITE_URL; ta.style.position = "fixed"; ta.style.opacity = "0"; document.body.appendChild(ta); ta.select();
    try{ document.execCommand("copy"); toast("링크를 복사했어요 🔗"); }catch(_){ toast("링크를 길게 눌러 복사해 주세요"); }
    ta.remove();
  }
}
async function shareLink(){
  if(navigator.share){ try{ await navigator.share({title: "전설로 떠나는 투자자 추천종목", text: "전설의 투자자 15인이 고른 종목을 한눈에 볼 수 있어요", url: SITE_URL}); }catch(e){} }
  else copyLink();
}

/* 데이터 기준 시각: 시세·재무를 실제로 받은 때(한국시간)와 얼마나 지났는지 */
function fresh(){
  // 코인 화면에서는 코인 시세를 받은 시각, 그 외에는 주식 데이터를 받은 시각
  const useCoin = st.market === "coin" && DATA.coin_fetched_ms;
  const at = useCoin ? DATA.coin_fetched : DATA.fetched, atMs = useCoin ? DATA.coin_fetched_ms : DATA.fetched_ms;
  const ms = Math.max(0, Date.now() - atMs), h = ms / 3.6e6;
  const rel = ms < 120000 ? "방금" : h < 1 ? `${Math.round(ms / 60000)}분 전` : h < 24 ? `${Math.floor(h)}시간 ${Math.round((h % 1) * 60)}분 전` : `${Math.floor(h / 24)}일 전`;
  return {rel, h, lvl: h < 3 ? "ok" : h < 8 ? "mid" : "old",
          abs: at.slice(5, 10).replace("-", "/") + " " + at.slice(11), full: at};
}
function updateStamp(){
  const f = fresh();
  $("stamp").innerHTML = `<i class="dot ${f.lvl}"></i><span class="hide-m">${f.abs} 기준 · </span>${f.rel}`;
  const a = document.querySelector(".asof .rel"); if(a) a.textContent = f.rel;
}
setInterval(updateStamp, 60000);

/* 화면 모드: 라이트(기본) / 다크 / 자동(기기 설정 따라감) */
const THEMES = [["light","☀️ 라이트"],["dark","🌙 다크"],["auto","🔄 자동"]];
let themeMode = "light";
try{ themeMode = localStorage.getItem("legend-theme") || "light"; }catch(e){}
function applyTheme(){
  const t = themeMode === "auto" ? (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light") : themeMode;
  document.documentElement.dataset.theme = t;
}
function setTheme(m){ themeMode = m; try{ localStorage.setItem("legend-theme", m); }catch(e){} applyTheme(); }
try{ matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => { if(themeMode === "auto") applyTheme(); }); }catch(e){}

/* 관심종목 (저장소를 못 쓰는 환경에서도 동작하도록 방어) */
let watch = new Set();
try{ watch = new Set(JSON.parse(localStorage.getItem("legend-watch") || "[]")); }catch(e){}
const saveWatch = () => { try{ localStorage.setItem("legend-watch", JSON.stringify([...watch])); }catch(e){} };

/* 포맷터 */
function money(v, cur){
  if(v == null) return "-";
  if(cur === "KRW") return v >= 1e12 ? (v/1e12).toFixed(1) + "조원" : Math.round(v/1e8).toLocaleString() + "억원";
  return v >= 1e12 ? "$" + (v/1e12).toFixed(2) + "T" : "$" + (v/1e9).toFixed(0) + "B";
}
/* 원화는 보통 정수로, 코인처럼 1000원 미만의 작은 가격은 소수점까지 보여준다 */
const krw = v => (Math.abs(v) >= 1000 ? Math.round(v).toLocaleString() : Math.abs(v) >= 100 ? v.toFixed(1).replace(/\.0$/, "") : Math.abs(v) >= 10 ? v.toFixed(2) : v.toFixed(4).replace(/0+$/, "").replace(/\.$/, "")) + "원";
const price = (v, cur) => v == null ? "-" : cur === "KRW" ? krw(v) : "$" + v.toLocaleString(undefined,{minimumFractionDigits:2,maximumFractionDigits:2});
/* 좁은 칸용 짧은 가격: 1천만 원 이상은 만원 단위(11,297만원), 100만~1천만 원은 소수 한 자리 만원(345.2만원). 나머지는 그대로 */
const priceS = (v, cur) => {
  if(v == null) return "-";
  if(cur === "KRW"){
    const a = Math.abs(v);
    if(a >= 1e7) return Math.round(v / 1e4).toLocaleString() + "만원";
    if(a >= 1e6) return (v / 1e4).toFixed(1).replace(/\.0$/, "") + "만원";
  }
  return price(v, cur);
};
const pct = v => v == null ? "-" : (v*100).toFixed(1) + "%";
const sgn = v => v == null ? "-" : (v >= 0 ? "+" : "") + (v*100).toFixed(0) + "%";
const tk = s => s.ticker.replace(".KS","").replace("KRW-","");
const months = wk => Math.round(wk * 7 / 30.4);
const ring = (s, size) => `<div class="ring" style="--p:${s.score};--c:${TONE_COLOR[s.tone]}${size ? ";--s:"+size+"px" : ""}"><i>${s.score}</i></div>`;
const bk = s => s.backers && s.backers.length ? `<span class="bk" title="추천한 투자자">${s.backers.map(m => `<i>${esc(m)}</i>`).join("")}</span>` : "";
/* 투자자 아바타: 사진이 있으면 사진, 없으면 이니셜 */
const pf = (v, sz = 30) => `<span class="pf ${isCons(v) ? "cons" : ""}" style="--sz:${sz}px">${v.photo ? `<img src="${esc(v.photo)}" alt="" loading="lazy">` : esc(v.mono)}</span>`;

/* 추세·체질 표시 */
const TREND = {up:["📈","상승 추세"], rebound:["↗","반등 시도"], flat:["➖","횡보"], down:["📉","하락 추세"]};
function trendPill(s){
  if(!s.trend) return "";
  const [ic, t] = s.severe ? ["🔪","급락 중"] : s.knife ? ["🔪","떨어지는 칼날"] : TREND[s.trend];
  return `<span class="pill tr-${s.knife ? "knife" : s.trend}">${ic} ${t}</span>`;
}
/* 이평선 정배열: 4·12·24·40주선(약 20·60·120·200일선)이 위에서부터 차례로 쌓이고 주가가 4주선 위 */
const alignPill = s => s.align ? `<span class="pill al" title="4·12·24·40주 이동평균이 위에서부터 차례로 배열 (약 20·60·120·200일선)">📶 이평선 정배열</span>` : "";
function structPill(s){
  if(s.struct === "growth") return `<span class="pill gr">🌱 성장 체질</span>`;
  if(s.struct === "slow") return `<span class="pill sl">⚠ 성장 둔화</span>`;
  return "";
}
/* ── 한눈에 보는 태그: 긍정은 초록, 주의는 빨강, 중립은 회색 ── */
/* 코인 태그: 재무가 없으니 차트·거래 지표로만 만든다 */
function computeTagsCoin(s){
  const T = [], add = (k, i, t, p, id) => T.push({k, i, t, p, id});
  const L = s.levels;
  if(L){
    if(L.status === "buy") add("pos", "✅", "지금 진입 구간", 95, "cbuy");
    else if(L.status === "near") add("pos", "👀", `진입가 근접 ${sgn(L.to_buy)}`, 85, "cnear");
    else if(L.status === "late") add("neg", "🏃", "이미 올라 추격 주의", 88, "clate");
    else if(L.status === "sell") add("neu", "🎯", "목표가 도달", 60, "csell");
    else add("neu", "⏳", `진입가까지 ${sgn(L.to_buy)}`, 35, "cwait");
  } else add("neu", "❔", "가격 전략 없음", 20, "nolv");
  if(s.severe) add("neg", "🔪", "급락 중", 95, "severe");
  else if(s.knife) add("neg", "🔪", "떨어지는 칼날", 90, "knife");
  else if(s.trend === "down") add("neg", "📉", "하락 추세", 80, "down");
  else if(s.trend === "up") add("pos", "📈", "상승 추세", 80, "up");
  else if(s.trend === "rebound") add("pos", "↗", "반등 시도", 50, "rebound");
  else if(s.trend === "flat") add("neu", "➖", "횡보", 30, "flat");
  if(s.align) add("pos", "📶", "이평선 정배열", 90, "align");
  if((s.pain ?? 0) >= 75) add("neg", "😰", "버티기 어려움", 70, "pain");
  if(s.above200) add("pos", "🏔", "200일선 위", 55, "a200");
  else add("neg", "🕳", "200일선 아래", 65, "b200");
  if(s.hi55) add("pos", "🚀", "55일 고점 돌파", 82, "brk55");
  if((s.vol_ratio3 ?? 0) >= 1.5) add("pos", "📊", `거래량 급증 ×${s.vol_ratio3.toFixed(1)}`, 78, "volhi");
  if((s.rs90 ?? 0) >= 0.10) add("pos", "💪", `BTC보다 강세 ${sgn(s.rs90)}p`, 72, "rshi");
  if((s.rsi2 ?? 100) <= 10 && s.above200) add("pos", "🎯", `단기 과매도 RSI(2) ${s.rsi2.toFixed(0)}`, 84, "oversold");
  if((s.adx ?? 0) >= 25) add("pos", "🧭", `추세 뚜렷 ADX ${s.adx.toFixed(0)}`, 60, "adxhi");
  if((s.bw_pct ?? 1) <= 0.2) add("pos", "🗜", "변동성 수축(스퀴즈)", 66, "squeeze");
  if(s.macd_since != null && s.macd_since <= 3) add("pos", "✨", "MACD 골든크로스", 70, "macdx");
  if((s.ret30 ?? 0) >= 0.25) add("pos", "🔥", `30일 ${sgn(s.ret30)}`, 62, "mom");
  if((s.value24 ?? 0) >= 5e10) add("pos", "💧", `거래대금 ${Math.round(s.value24 / 1e8).toLocaleString()}억`, 50, "liq");
  else if((s.value24 ?? 1e12) < 1e10) add("neg", "🪫", "거래대금 적음", 68, "lowliq");
  if((s.rsi14 ?? 0) >= 75) add("neg", "🥵", `과열 RSI ${s.rsi14.toFixed(0)}`, 76, "hot");
  if((s.atr_pct ?? 0) >= 0.07) add("neg", "🎢", `변동성 매우 큼 ${(s.atr_pct * 100).toFixed(0)}%`, 66, "volx");
  if((s.dd365 ?? 0) <= -0.5) add("neg", "🔻", `1년 고점 대비 ${sgn(s.dd365)}`, 72, "deepdd");
  const w = (s.warnings || []).length;
  if(w) add("neg", "🚨", `추세 훼손 신호 ${w}`, 88, "cwarn");
  else add("pos", "👍", "추세 훼손 신호 없음", 40, "cclean");
  return T.sort((a, b) => b.p - a.p);
}
function computeTags(s){
  if(isCoin(s)) return computeTagsCoin(s);
  const T = [], add = (k, i, t, p, id) => T.push({k, i, t, p, id});
  const L = s.levels;
  // 가격 위치 (추천 인원은 판정 태그에 이미 나오므로 중복해서 붙이지 않는다)
  if(L){
    if(L.status === "buy") add("pos", "✅", "지금 매수 구간", 95, "buyzone");
    else if(L.status === "near") add("pos", "👀", `매수가 근접 ${sgn(L.to_buy)}`, 85, "near");
    else if(L.status === "late") add("neg", "🏃", "이미 올라 추격 주의", 88, "clate");
    else if(L.status === "sell") add("neg", "💸", L.kind === "coin" ? "목표가 도달" : "적정가 초과", 90, "over");
    else add("neu", "⏳", `매수가까지 ${sgn(L.to_buy)}`, 35, "wait");
  } else add("neu", "❔", "가격 산출 불가", 20, "nolv");
  // 차트 지표 (차트 현인들이 보는 신호): 주식에도 같은 태그를 붙인다
  if((s.rsi2 ?? 100) <= 10 && s.above200) add("pos", "🎯", `단기 과매도 RSI(2) ${s.rsi2.toFixed(0)}`, 84, "oversold");
  if(s.hi55) add("pos", "🚀", "55일 고점 돌파", 82, "brk55");
  if((s.vol_ratio3 ?? 0) >= 1.5) add("pos", "📊", `거래량 급증 ×${s.vol_ratio3.toFixed(1)}`, 78, "volhi");
  if((s.adx ?? 0) >= 25) add("pos", "🧭", `추세 뚜렷 ADX ${s.adx.toFixed(0)}`, 60, "adxhi");
  if((s.bw_pct ?? 1) <= 0.2) add("pos", "🗜", "변동성 수축(스퀴즈)", 66, "squeeze");
  if(s.macd_since != null && s.macd_since <= 3) add("pos", "✨", "MACD 골든크로스", 70, "macdx");
  if((s.rsi14 ?? 0) >= 75) add("neg", "🥵", `과열 RSI ${s.rsi14.toFixed(0)}`, 76, "hot");
  // 주가 흐름
  if(s.severe) add("neg", "🔪", "급락 중", 95, "severe");
  else if(s.knife) add("neg", "🔪", "떨어지는 칼날", 90, "knife");
  else if(s.trend === "down") add("neg", "📉", "하락 추세", 80, "down");
  else if(s.trend === "up") add("pos", "📈", "상승 추세", 80, "up");
  else if(s.trend === "rebound") add("pos", "↗", "반등 시도", 50, "rebound");
  else if(s.trend === "flat") add("neu", "➖", "횡보", 30, "flat");
  if(s.align) add("pos", "📶", "이평선 정배열", 90, "align");
  if((s.pain ?? 0) >= 75) add("neg", "😰", "버티기 어려움", 70, "pain");
  // 성장
  if(s.struct === "growth") add("pos", "🌱", "성장 체질", 85, "growth");
  else if(s.struct === "slow") add("neg", "⚠", "성장 둔화", 85, "slow");
  else if(s.struct === "mature") add("neu", "⚖", "성숙·안정", 30, "mature");
  if(s.rev_cagr != null){
    if(s.rev_cagr >= 0.2) add("pos", "🚀", `매출 고성장 ${sgn(s.rev_cagr)}`, 75, "revhi");
    else if(s.rev_cagr < 0) add("neg", "🔻", "매출 역성장", 80, "revneg");
  }
  if(s.loss) add("neg", "🕳", "최근 적자", 85, "loss");
  else if(s.ni_yoy != null){
    if(s.ni_yoy >= 0.25) add("pos", "🔥", `이익 급증 ${sgn(s.ni_yoy)}`, 70, "nihi");
    else if(s.ni_yoy <= -0.15) add("neg", "📉", `이익 감소 ${sgn(s.ni_yoy)}`, 80, "nilo");
  }
  // 수익성·재무
  if(s.roe != null){
    if(s.roe >= 0.20) add("pos", "💪", `ROE ${(s.roe*100).toFixed(0)}%`, 70, "roehi");
    else if(s.roe < 0.08 && !s.loss) add("neg", "⬇", "ROE 낮음", 60, "roelo");
  }
  if(!s.fin && s.op_margin != null){
    if(s.op_margin >= 0.20) add("pos", "🏰", `고마진 ${(s.op_margin*100).toFixed(0)}%`, 65, "mgnhi");
    else if(s.op_margin < 0.05) add("neg", "🧊", "낮은 마진", 55, "mgnlo");
  }
  if(!s.fin){
    if(s.debt0 || (s.debt_to_ni != null && s.debt_to_ni <= 1.5)) add("pos", "🛡", "부채 낮음", 60, "debtlo");
    else if(s.debt_to_ni != null && s.debt_to_ni > 5) add("neg", "🏚", "부채 과다", 75, "debthi");
    if(s.net_cash != null && s.net_cash >= 0) add("pos", "💎", "순현금", 55, "netcash");
    if(s.fcf_neg) add("neg", "💧", "현금흐름 적자", 75, "fcfneg");
    else if(s.fcf_yield != null && s.fcf_yield >= 0.06) add("pos", "💵", `FCF 수익률 ${(s.fcf_yield*100).toFixed(0)}%`, 65, "fcfhi");
  }
  // 가격 매력
  if(s.per != null){
    if(s.per <= 12) add("pos", "🏷", `PER ${s.per.toFixed(0)}배`, 60, "perlo");
    else if(s.per >= 40) add("neg", "🧮", `PER ${s.per.toFixed(0)}배`, 65, "perhi");
  }
  if(s.pb != null && s.pb <= 1) add("pos", "🏷", "PBR 1배 이하", 55, "pblo");
  if(s.peg != null && s.peg <= 1) add("pos", "⚖", `PEG ${s.peg.toFixed(1)}`, 60, "peglo");
  if(s.div_yield != null && s.div_yield >= 0.03) add("pos", "🎁", `배당 ${(s.div_yield*100).toFixed(1)}%`, 55, "div");
  // 재무 손절 신호
  const w = (s.warnings || []).length;
  if(w) add("neg", "🚨", `재무 손절 신호 ${w}`, 88, "warn");
  else add("pos", "👍", "재무 신호 정상", 40, "clean");
  return T.sort((a, b) => b.p - a.p);
}
const TAGNAME = {cons:"🏆 추천 다수", split:"🤷 의견 갈림", buyzone:"✅ 지금 매수 구간", near:"👀 매수가 근접", over:"💸 적정가 초과", wait:"⏳ 매수가 대기", nolv:"❔ 가격 산출 불가",
  severe:"🔪 급락 중", knife:"🔪 떨어지는 칼날", down:"📉 하락 추세", up:"📈 상승 추세", rebound:"↗ 반등 시도", flat:"➖ 횡보", align:"📶 이평선 정배열", pain:"😰 버티기 어려움",
  growth:"🌱 성장 체질", slow:"⚠ 성장 둔화", mature:"⚖ 성숙·안정", revhi:"🚀 매출 고성장", revneg:"🔻 매출 역성장", loss:"🕳 최근 적자", nihi:"🔥 이익 급증", nilo:"📉 이익 감소",
  roehi:"💪 ROE 높음", roelo:"⬇ ROE 낮음", mgnhi:"🏰 고마진", mgnlo:"🧊 낮은 마진", debtlo:"🛡 부채 낮음", debthi:"🏚 부채 과다", netcash:"💎 순현금", fcfneg:"💧 현금흐름 적자",
  fcfhi:"💵 FCF 수익률 높음", perlo:"🏷 PER 낮음", perhi:"🧮 PER 높음", pblo:"🏷 PBR 1배 이하", peglo:"⚖ PEG 낮음", div:"🎁 배당", warn:"🚨 재무 손절 신호", clean:"👍 재무 신호 정상",
  /* 코인 */
  cbuy:"✅ 지금 진입 구간", cnear:"👀 진입가 근접", clate:"🏃 이미 올라 추격 주의", csell:"🎯 목표가 도달", cwait:"⏳ 진입가 대기", a200:"🏔 200일선 위", b200:"🕳 200일선 아래",
  brk55:"🚀 55일 고점 돌파", volhi:"📊 거래량 급증", rshi:"💪 BTC보다 강세", oversold:"🎯 단기 과매도(눌림)", adxhi:"🧭 추세 뚜렷(ADX)", squeeze:"🗜 변동성 수축", macdx:"✨ MACD 골든크로스",
  mom:"🔥 30일 강한 상승", liq:"💧 거래대금 풍부", lowliq:"🪫 거래대금 적음", hot:"🥵 과열(RSI)", volx:"🎢 변동성 매우 큼", deepdd:"🔻 1년 고점 대비 -50%↓", cwarn:"🚨 추세 훼손 신호", cclean:"👍 추세 훼손 신호 없음"};
const tagsOf = s => s._tags || (s._tags = computeTags(s));
const tagScore = s => { const t = tagsOf(s); return t.filter(x => x.k === "pos").length - t.filter(x => x.k === "neg").length; };
/* 최대 max개: 중요도 순으로 고르되, 주의(빨강) 태그가 있으면 최소 2개는 보이게 한다 */
function pickTags(s, max){
  const all = tagsOf(s);
  if(!max || all.length <= max) return all;
  let sel = all.slice(0, max);
  const negs = all.filter(t => t.k === "neg");
  const have = sel.filter(t => t.k === "neg").length, need = Math.min(2, negs.length) - have;
  if(need > 0){
    const extra = negs.filter(t => !sel.includes(t)).slice(0, need);
    sel = [...sel.slice(0, max - extra.length), ...extra];
  }
  return sel.sort((a, b) => b.p - a.p);
}
function tagsHtml(s, max = 6, click = false){
  const all = tagsOf(s), sel = pickTags(s, max);
  return sel.map(t => `<span class="tg ${t.k}${click ? " clk" : ""}" ${click ? `data-tag="${t.id}"` : ""}>${t.i} ${esc(t.t)}</span>`).join("")
    + (all.length > sel.length ? `<span class="tg more">+${all.length - sel.length}</span>` : "");
}
/* 상세 화면용: 긍정 / 주의 / 참고로 나눠 전부 보여준다 */
function glanceHtml(s){
  const all = tagsOf(s), g = k => all.filter(t => t.k === k);
  const row = (k, label, cls) => g(k).length ? `<div class="gl-row"><span class="gl-l ${cls}">${label} ${g(k).length}</span><div class="gl-t">${g(k).map(t => `<span class="tg ${t.k}">${t.i} ${esc(t.t)}</span>`).join("")}</div></div>` : "";
  return `<div class="glance"><div class="gl-h">한눈에 보기</div>${row("pos","긍정","pos")}${row("neg","주의","neg")}${row("neu","참고","neu")}</div>`;
}

function statusInfo(s){
  const L = s.levels;
  if(L && L.kind === "coin"){
    const m = {buy:{k:"buy", short:"지금 진입 구간", long:"현재가가 진입 구간 안에 있어요. 신호 조건이 맞는 자리입니다."},
      near:{k:"near", short:"진입가 근접", long:`진입가까지 ${sgn(L.to_buy)} 남았어요. 조건이 채워지는지 지켜보세요.`},
      wait:{k:"wait", short:`진입가까지 ${sgn(L.to_buy)}`, long:`아직 진입 자리가 아닙니다. 진입가(${price(L.buy, s.currency)})에 가까워질 때까지 기다리는 쪽입니다.`},
      late:{k:"near", short:"추격 주의", long:"이미 진입가보다 많이 올랐어요(1ATR 이상). 지금 따라 사면 손절폭이 커지니 눌림을 기다리는 쪽이 낫습니다."},
      sell:{k:"sell", short:"목표가 도달", long:"목표가에 도달했어요. 보유 중이라면 이익 실현을 검토할 구간이고, 신규 진입은 피하세요."}};
    return m[L.status];
  }
  if(!L) return {k:"none", short:"가격 산출 불가", long:"내재가치를 추정할 수 없어 가격 전략을 제공하지 못합니다. (현금흐름이 적자이거나 데이터 부족)"};
  if(L.status === "buy")  return {k:"buy",  short:"지금 매수 구간", long:"현재가가 매수가보다 낮아 안전마진이 확보된 구간입니다."};
  if(L.status === "near") return {k:"near", short:"매수가 근접", long:`매수가까지 ${sgn(L.to_buy)} 남았습니다. 조금만 더 내려오면 매수 구간입니다.`};
  if(L.status === "wait") return {k:"wait", short:`매수가까지 ${sgn(L.to_buy)}`, long:`아직 매수가보다 높습니다. ${sgn(L.to_buy)} 정도 내려올 때까지 기다리는 쪽입니다.`};
  return {k:"sell", short:"적정가 초과", long:"현재가가 추정 적정가(매도가)를 넘었습니다. 신규 매수는 피하고, 보유 중이라면 차익 실현을 검토할 구간입니다."};
}

/* ── 공통 조각 ── */
function segHtml(){
  const n = m => (m === "coin" ? DATA.investors[BY_ID.call] : DATA.investors[BY_ID.all]).stocks.filter(s => s.market === m).length;
  const hasCoin = BY_ID.call !== undefined;
  return `<div class="seg" role="tablist" style="--n:${hasCoin ? 3 : 2}">
    <button role="tab" data-m="us" aria-selected="${st.market==="us"}">미국 주식<span>${n("us")}</span></button>
    <button role="tab" data-m="kr" aria-selected="${st.market==="kr"}">한국 주식<span>${n("kr")}</span></button>
    ${hasCoin ? `<button role="tab" data-m="coin" aria-selected="${st.market==="coin"}">코인<span>${n("coin")}</span></button>` : ""}</div>`;
}
/* 1단: 종합 / 진영(성장주·저평가·복합 또는 추세추종·돌파·눌림) → 2단: 해당 진영의 투자자·매매이론 */
function chipsHtml(){
  const cur = inv();
  const cats = DATA.investors.map((v,i) => [v,i]).filter(([v]) => isCons(v) && v.domain === dom());
  const row1 = cats.map(([v,i]) => `<button class="ic cat ${v.group==="all"?"all":""} ${!isCons(cur) && cur.group===v.id ? "in" : ""}" data-inv="${i}" aria-pressed="${i===st.inv}">${esc(v.short)}</button>`).join("");
  const mem = isAllCons(cur) ? members() : members(cur.group);
  const row2 = mem.map(v => `<button class="ic" data-inv="${BY_ID[v.id]}" aria-pressed="${v.id===cur.id}">${pf(v, 26)}${esc(v.short)}</button>`).join("");
  return `<div class="ichips cat">${row1}</div><div class="ichips mem">${row2}</div>`;
}

/* 관점(종합·진영·투자자) 선택은 평소엔 한 줄로 접어 두고, 누르면 펼친다 */
function perspHtml(){
  return `<details class="persp"><summary><span>관점 <b>${esc(inv().short)}</b></span><span class="chev">바꾸기</span></summary>${chipsHtml()}</details>`;
}
/* 접는 블록: 열고 닫은 상태는 st.fold 에 기억해 다시 그려도 유지한다 */
function fold(key, title, inner, hint = ""){
  return inner ? `<details class="fold" data-fold="${key}" ${st.fold[key] ? "open" : ""}><summary><span>${title}</span>${hint ? `<small>${hint}</small>` : ""}</summary><div class="fold-b">${inner}</div></details>` : "";
}

/* 투자자 소개 카드 */
function creditHtml(v){
  const c = v.photo_credit;
  return c ? `<div class="credit">사진: ${esc(c.artist || "작성자 미상")} · ${esc(c.license)} · <a href="${esc(c.source)}" target="_blank" rel="noopener">Wikimedia Commons</a></div>` : "";
}
function profileCard(v){
  if(isAllCons(v)){
    return `<div class="prof"><div class="prof-t">${v.domain === "coin" ? `코인 종합 · 매매이론 ${members().length}개의 합의` : `종합 · ${members().length}인의 합의`}</div><p class="prof-b">${esc(v.intro)}</p>
      <div class="gtiles">${groupsNow().map(g => { const gi = BY_ID[g], gv = DATA.investors[gi];
        return `<button class="gt" data-inv="${gi}"><b>${esc(gv.short)}</b><small>${esc(gv.tagline)}</small><span class="gm">${members(g).map(x => pf(x, 26)).join("")}</span></button>`; }).join("")}</div></div>`;
  }
  if(isCons(v)){
    return `<div class="prof"><div class="prof-t">${esc(v.name)}</div><p class="prof-b">${esc(v.intro)}</p>
      ${members(v.id).map(x => `<button class="mrow" data-inv="${BY_ID[x.id]}">${pf(x, 46)}<span><b>${esc(x.name)}</b><small>${esc(x.profile.role)}</small></span></button>`).join("")}</div>`;
  }
  const p = v.profile, gname = DATA.groups[v.group].name;
  return `<div class="prof">
    <div class="prof-h">${pf(v, 84)}<div><div class="prof-n">${esc(v.name)}</div><div class="prof-r">${esc(p.role)}</div>
      <div class="prof-m">${esc(p.meta)} · <span class="gtag g-${v.group}">${esc(gname)}</span></div></div></div>
    <p class="prof-b">${esc(p.bio)}</p>
    <div class="prof-p"><b>${v.domain === "coin" ? "이론의 핵심" : "투자 철학"}</b><p>${esc(p.philosophy)}</p><div class="kws">${p.keywords.map(k => `<span>${esc(k)}</span>`).join("")}</div></div>
    <div class="prof-w">대표 저서·활동 <b>${esc(p.works)}</b></div>
    <details class="prof-d"><summary>이 앱은 이렇게 평가해요</summary><ol class="steps">${v.principles.map(x => `<li>${esc(x)}</li>`).join("")}</ol></details>
    ${creditHtml(v)}</div>`;
}

/* TOP 5: 같은 업종은 최대 2개까지만 올려 특정 업종 쏠림을 막는다 */
function topPicks(all, n = 5){
  const cnt = {}, out = [], cap = dom() === "coin" ? 99 : 2;   // 코인은 업종 구분이 없어 제한하지 않는다
  for(const s of all.filter(s => (s.tone === "strong" || s.tone === "buy") && !s.severe).sort((a,b) => rankKey(b) - rankKey(a))){
    const k = s.sector || "-";
    if((cnt[k] || 0) >= cap) continue;
    cnt[k] = (cnt[k] || 0) + 1; out.push(s);
    if(out.length >= n) break;
  }
  return out;
}

/* 가격 3종: 주식은 매수가·매도가·손절가, 코인은 진입가·목표가·손절가 */
const lvLabels = s => (isCoin(s) || (s.levels && s.levels.kind === "coin")) ? ["진입가", "목표가", "손절가"] : ["매수가", "매도가", "손절가"];
function lvHtml(s){
  const L = s.levels, c = s.currency, [a, b, x] = lvLabels(s);
  return L ? `<div class="lv"><div class="b"><span>${a}</span><b>${priceS(L.buy,c)}</b></div><div class="s"><span>${b}</span><b>${priceS(L.sell,c)}</b></div><div class="x"><span>${x}</span><b>${priceS(L.stop,c)}</b></div></div>` : "";
}
/* 카드 부제: 주식은 업종·현재가, 코인은 현재가·24시간 등락 */
const subLine = s => isCoin(s) ? `현재 ${price(s.price, s.currency)} · 24시간 <b style="color:var(--${(s.change24 ?? 0) >= 0 ? "ok" : "no"})">${(s.change24 ?? 0) >= 0 ? "+" : ""}${((s.change24 ?? 0) * 100).toFixed(1)}%</b>`
                                      : `${esc(s.sector||"")} · 현재 ${price(s.price, s.currency)}`;
function pickCard(s, i){
  const lv = lvHtml(s) || `<div class="note">가격 전략을 산출할 수 없는 종목입니다.</div>`;
  return `<div class="pick tn-${s.tone} ${i===0?"first":""}" data-open="${esc(s.ticker)}" style="animation-delay:${i*70}ms">
    <span class="medal ${i<3?"m"+(i+1):""}">${i+1}위</span>
    <div class="top"><div><div class="nm">${esc(s.name)}<span class="tk">${esc(tk(s))}</span></div>
      <div class="sub">${subLine(s)}</div></div>${ring(s)}</div>
    <div class="tags"><span class="tag t-${s.tone}">${esc(s.verdict)}</span></div>
    <div class="tgs">${tagsHtml(s, 3)}</div>${lv}</div>`;
}

/* ── 홈 ── */
function viewHome(){
  const v = inv(), all = v.stocks.filter(s => s.market === st.market);
  const picks = topPicks(all);
  const near = all.filter(s => s.quality >= 65 && s.levels && s.levels.status === "near" && !s.knife).sort((a,b) => Math.abs(a.levels.to_buy) - Math.abs(b.levels.to_buy)).slice(0,6);
  const knives = all.filter(s => s.knife && s.score >= 65).sort((a,b) => rankKey(b) - rankKey(a)).slice(0,8);
  const C = dom() === "coin", f = fresh();
  const nearHtml = near.length ? `<div class="mh">${C ? "곧 진입 구간" : "곧 매수 구간"} <small>${C ? "신호가 임박한 코인" : "좋은 기업인데 매수가에 근접"}</small></div><div class="mini">${near.map(s => `
    <div class="mcard tn-${s.tone}" data-open="${esc(s.ticker)}"><b>${esc(s.name)}</b><div class="sub">${price(s.price,s.currency)} · ${C ? "점수" : "기업 질"} ${s.quality}점</div>
    <span class="pill near">${C ? "진입가" : "매수가"} ${price(s.levels.buy,s.currency)}</span></div>`).join("")}</div>` : "";
  const knifeHtml = knives.length ? `<div class="mh">${C ? "신호는 났지만 아직 떨어지는 중" : "저평가지만 아직 떨어지는 중"} <small>🔪 추세가 돌아설 때까지 관망 · 나눠서 매수</small></div><div class="mini">${knives.map(s => `
    <div class="mcard tn-${s.tone}" data-open="${esc(s.ticker)}"><b>${esc(s.name)}</b><div class="sub">${price(s.price,s.currency)} · 점수 ${s.score}</div>
    <span class="pill tr-knife">🔪 ${C ? "1년 고점" : "3년 고점"} 대비 ${sgn(C ? s.dd365 : DATA.px[s.ticker]?.dd_3y)}</span></div>`).join("")}</div>` : "";
  return `
  <div class="hd"><h1>오늘의 추천 <em>TOP 5</em></h1>
    <div class="asof2"><i class="dot ${f.lvl}"></i>${f.abs} 기준 · ${f.rel}</div></div>
  ${segHtml()}
  ${perspHtml()}
  ${picks.length ? `<div class="picks">${picks.map(pickCard).join("")}</div>` : (C
    ? `<div class="empty">지금은 ${esc(v.name)} 기준의 매수 신호가 나온 코인이 없습니다.<br>신호 없는 날에는 쉬는 것도 매매입니다.</div>`
    : `<div class="empty">지금은 이 시장에서 ${esc(v.name)} 기준을 통과한 종목이 없습니다.<br>좋은 기업이어도 가격이 비싸면 사지 않는 것이 가치투자의 원칙입니다.</div>`)}
  ${fold("homemore", "더 보기", nearHtml + knifeHtml + `<div class="mh">시장 분포</div>` + distHtml(all), "곧 매수 구간 · 떨어지는 칼날")}
  <p class="disc" style="margin-top:16px"><b>참고용 모의 평가</b>이며 투자 권유가 아닙니다. 판단과 책임은 본인에게 있습니다.${C ? " 코인은 변동성이 매우 커 원금을 크게 잃을 수 있습니다." : ""}</p>`;
}
function distHtml(all){
  const counts = {}; all.forEach(s => counts[s.tone] = (counts[s.tone]||0)+1);
  const TL = tones(), ks = Object.keys(TL).filter(k => counts[k]);
  return `<div class="panel" style="padding:16px"><div class="dist">${ks.map(k => `<i style="width:${counts[k]/all.length*100}%;background:${TONE_COLOR[k]}"></i>`).join("")}</div>
    <div class="legend-chips">${ks.map(k => `<button class="chip tn-${k}" data-legend="${k}" title="눌러서 이 평가의 종목 보기">${TL[k]} <b>${counts[k]}</b></button>`).join("")}</div>
    <div class="sub" style="margin-top:8px">💡 칩을 누르면 해당 평가의 종목 목록으로 이동해요</div></div>`;
}

/* ── 종목 ── */
function rowHtml(s, i){
  return `<div class="row tn-${s.tone}" data-open="${esc(s.ticker)}" style="animation-delay:${Math.min(i,10)*25}ms">
    ${ring(s)}
    <div><div class="nm2">${esc(s.name)}<small>${esc(tk(s))}</small></div>
      <div class="sub">${isCoin(s) ? subLine(s) : `${esc(s.sector||"")} · ${price(s.price,s.currency)}`}</div>
      <div class="line"><span class="tag t-${s.tone}">${esc(s.verdict)}</span>${bk(s)}</div>
      <div class="tgs">${tagsHtml(s, 3, st.view === "list" || st.view === "tags")}</div></div>
    <button class="star ${watch.has(s.ticker)?"on":""}" data-star="${esc(s.ticker)}" aria-label="관심종목" aria-pressed="${watch.has(s.ticker)}"><svg viewBox="0 0 24 24">${ICONS.star}</svg></button>
  </div>`;
}
function filtered(){
  const q = st.q.trim().toLowerCase();
  let a = inv().stocks.filter(s => s.market === st.market);
  if(st.tone !== "all") a = a.filter(s => s.tone === st.tone);
  if(st.only === "growth") a = a.filter(s => s.struct === "growth");
  if(st.only === "nodown") a = a.filter(s => s.trend !== "down");
  if(st.only === "align") a = a.filter(s => s.align);
  if(q) a = a.filter(s => s.name.toLowerCase().includes(q) || s.ticker.toLowerCase().includes(q));
  const key = {score:rankKey, mos:s=>s.mos ?? -9, roe:s=>s.roe ?? -9, quality:s=>s.quality, upside:s=>s.levels ? s.levels.to_buy : -99, growth:s=>s.gh ?? -1, tags:tagScore,
    chg:s=>s.change24 ?? -9, vol:s=>s.value24 ?? 0, mom:s=>s.ret30 ?? -9}[st.sort] || rankKey;
  return a.sort((x,y) => key(y) - key(x) || y.score - x.score);
}
const SORTS_STOCK = [["tags","긍정 태그 많은 순"],["growth","성장 체질순"],["mos","안전마진순"],["roe","ROE순"],["quality","기업 질순"],["upside","매수가 근접순"]];
const SORTS_COIN = [["tags","긍정 태그 많은 순"],["chg","24시간 상승률순"],["mom","30일 상승률순"],["vol","거래대금순"],["upside","진입가 근접순"]];
function viewList(){
  const first = isCons(inv()) ? "추천 많은 순" : "총점순";
  const sorts = dom() === "coin" ? SORTS_COIN : SORTS_STOCK;
  if(!["score", ...sorts.map(x => x[0])].includes(st.sort)) st.sort = "score";
  return `<h2 style="margin-top:18px">${dom() === "coin" ? "전체 코인" : "전체 종목"}</h2>
  ${segHtml()}
  ${perspHtml()}
  <div class="tools" style="margin-top:10px"><input id="q" type="search" placeholder="종목명 · 티커 검색" value="${esc(st.q)}" aria-label="종목 검색">
    <select id="sort" aria-label="정렬">${[["score",first], ...sorts].map(([v,t]) => `<option value="${v}" ${st.sort===v?"selected":""}>${t}</option>`).join("")}</select></div>
  <div id="listBody"></div>`;
}
function fillList(){
  const all = inv().stocks.filter(s => s.market === st.market);
  const counts = {}; all.forEach(s => counts[s.tone] = (counts[s.tone]||0)+1);
  const list = filtered();
  const ex = DATA.excluded.filter(e => e.market === st.market);
  $("listBody").innerHTML =
    `<div class="filters"><button class="chip" aria-pressed="${st.tone==='all'}" data-f="all">전체 ${all.length}</button>` +
    Object.keys(tones()).filter(k => counts[k]).map(k => `<button class="chip tn-${k}" aria-pressed="${st.tone===k}" data-f="${k}">${tones()[k]} <b>${counts[k]}</b></button>`).join("") + `</div>
    <details class="persp sub-f"><summary><span>추세·체질 필터</span><span class="chev">${st.only === "all" ? "전체" : "적용 중"}</span></summary><div class="filters">${(dom() === "coin" ? [["all","추세 전체"],["align","📶 이평선 정배열만"],["nodown","📉 하락 추세 제외"]] : [["all","추세·체질 전체"],["align","📶 이평선 정배열만"],["growth","🌱 성장 체질만"],["nodown","📉 하락 추세 제외"]]).map(([k,t]) => `<button class="chip alt" aria-pressed="${st.only===k}" data-o="${k}">${t}</button>`).join("")}</div></details>
    <div class="sub" style="margin:2px 2px 10px">${list.length}개 종목</div>` +
    (list.length ? list.map(rowHtml).join("") : `<div class="empty">조건에 맞는 종목이 없어요.</div>`) +
    (ex.length ? `<details class="excl"><summary>데이터 부족으로 평가하지 못한 종목 ${ex.length}개</summary><ul>${ex.map(e => `<li>${esc(e.name)} (${esc(e.ticker)}): ${esc(e.issue)}</li>`).join("")}</ul></details>` : "");
}

/* ── 태그 탭: 태그를 고르면 그 태그를 가진 종목만 점수 높은 순으로 ── */
const TAGDESC = {buyzone:"현재가가 매수가 이하", near:"현재가가 매수가의 +10% 이내", over:"현재가가 적정가(매도가) 이상", wait:"아직 매수가보다 한참 위", nolv:"내재가치를 추정할 수 없음",
  severe:"하락 추세 + 3년 고점 대비 -50% 이하(또는 1년 -40% 이하)", knife:"하락 추세 + 3년 고점 대비 -30% 이하", down:"주가가 40주선 아래 + 1년 -15% 이하(또는 40주선 하락)",
  up:"주가가 40주선 위 + 40주선 상승", rebound:"40주선 위인데 40주선은 아직 하락", flat:"뚜렷한 방향 없음", align:"4·12·24·40주선이 위에서부터 차례로 + 주가가 4주선 위",
  pain:"과거 5년 버티기 난이도 75 이상", growth:"성장 체질 점수 60 이상", slow:"성장 체질 점수 35 미만", mature:"성장 체질 점수 35~60", revhi:"매출 연평균 +20% 이상",
  revneg:"매출 연평균 마이너스", loss:"최근 연도 순이익 적자", nihi:"최근 이익 +25% 이상", nilo:"최근 이익 -15% 이하", roehi:"평균 ROE 20% 이상", roelo:"평균 ROE 8% 미만",
  mgnhi:"평균 영업이익률 20% 이상(금융업 제외)", mgnlo:"영업이익률 5% 미만", debtlo:"부채가 순이익의 1.5배 이하 또는 무차입", debthi:"부채가 순이익의 5배 초과",
  netcash:"현금이 부채보다 많음", fcfneg:"최근 잉여현금흐름 적자", fcfhi:"3년 평균 FCF 수익률 6% 이상", perlo:"PER 12배 이하", perhi:"PER 40배 이상", pblo:"PBR 1배 이하",
  peglo:"PEG 1 이하", div:"배당수익률 3% 이상", warn:"재무 손절 신호 1개 이상", clean:"재무 손절 신호 없음",
  cbuy:"현재가가 진입 구간(진입가 −0.5ATR ~ +1ATR) 안", cnear:"진입 구간까지 1ATR 이내", clate:"진입가보다 1ATR 넘게 올라 추격하기엔 늦음", csell:"목표가 이상", cwait:"진입가보다 한참 아래",
  a200:"가격이 200일 이동평균선 위", b200:"가격이 200일 이동평균선 아래", brk55:"현재가가 직전 55일 최고가 위", volhi:"최근 3일 거래대금이 20일 평균의 1.5배 이상",
  rshi:"최근 90일 수익률이 BTC보다 10%p 이상 높음", oversold:"RSI(2) 10 이하인데 가격은 200일선 위(상승 추세 속 눌림)", adxhi:"ADX 25 이상 (추세가 뚜렷)", squeeze:"볼린저 밴드폭이 최근 120일 중 하위 20%",
  macdx:"MACD가 최근 3일 안에 시그널선을 상향 돌파", mom:"최근 30일 +25% 이상", liq:"24시간 거래대금 500억 원 이상", lowliq:"24시간 거래대금 100억 원 미만 (체결 위험)",
  hot:"RSI(14) 75 이상", volx:"하루 변동폭(ATR)이 가격의 7% 이상", deepdd:"1년 고점 대비 -50% 이하", cwarn:"200일선 이탈·데드크로스·과열 등 추세 훼손 신호 1개 이상", cclean:"추세 훼손 신호 없음"};
const PRESETS_COIN = [["🎯 눌림 + 📈 상승 추세", ["oversold","up"]], ["🚀 55일 돌파 + 📊 거래량 급증", ["brk55","volhi"]], ["📶 정배열 + 🧭 추세 뚜렷", ["align","adxhi"]],
  ["✨ MACD 골든크로스 + 🏔 200일선 위", ["macdx","a200"]], ["🗜 스퀴즈 + 🏔 200일선 위", ["squeeze","a200"]], ["🔪 급락 중 (피할 코인)", ["severe"]]];
const PRESETS = [["📶 정배열 + 🌱 성장 체질", ["align","growth"]], ["✅ 매수 구간 + 📈 상승 추세", ["buyzone","up"]], ["🏷 저PER + 💪 고ROE", ["perlo","roehi"]],
  ["🛡 안전형 (부채 낮음·순현금)", ["debtlo","netcash"]], ["🔥 이익 급증 + 🚀 매출 고성장", ["nihi","revhi"]], ["🔪 급락 중 (피할 종목)", ["severe"]]];
const presets = () => dom() === "coin" ? PRESETS_COIN : PRESETS;
function tagResults(all){
  return all.filter(s => st.tags.every(id => tagsOf(s).some(t => t.id === id)))
    .sort((a, b) => b.score - a.score || rankKey(b) - rankKey(a));
}
function viewTags(){
  const v = inv(), all = v.stocks.filter(s => s.market === st.market);
  const cat = {};
  all.forEach(s => tagsOf(s).forEach(t => { (cat[t.id] ||= {k: t.k, n: 0, p: t.p}).n++; }));
  const group = (k, title, cls) => {
    const ids = Object.keys(cat).filter(id => cat[id].k === k && TAGNAME[id]).sort((a, b) => cat[b].p - cat[a].p || cat[b].n - cat[a].n);
    return ids.length ? `<div class="tgroup"><div class="tg-h"><span class="gl-l ${cls}">${title}</span></div><div class="tgrid">${ids.map(id =>
      `<button class="tg btn ${k}${st.tags.includes(id) ? " on" : ""}" data-tagsel="${id}" title="${esc(TAGDESC[id] || "")}">${esc(TAGNAME[id])} <b>${cat[id].n}</b></button>`).join("")}</div></div>` : "";
  };
  const res = st.tags.length ? tagResults(all) : [];
  return `<h2 style="margin-top:18px">태그로 찾기 <span class="sub">고른 태그를 모두 가진 ${dom() === "coin" ? "코인" : "종목"} · 점수 높은 순</span></h2>
  ${segHtml()}
  ${perspHtml()}
  <div class="sub" style="margin:10px 2px 6px">💡 태그를 여러 개 고르면 그 태그를 <b>모두</b> 가진 종목만 나와요 (점수는 위에서 고른 투자자 기준)</div>
  ${st.tags.length ? `<div class="selbar"><span>선택한 태그</span>${st.tags.map(id => `<button class="tg ${(cat[id] || {k:"neu"}).k} on" data-tagsel="${id}">${esc(TAGNAME[id] || id)} ✕</button>`).join("")}<button class="chip" data-tagclear="1">모두 해제</button></div>`
    : `<div class="presets"><div class="tg-h"><span class="sub"><b>추천 조합</b> 눌러서 바로 보기</span></div><div class="tgrid">${presets().map(([t, ids], i) => `<button class="chip" data-preset="${i}">${esc(t)}</button>`).join("")}</div></div>`}
  ${group("pos", "긍정", "pos")}${group("neg", "주의", "neg")}${group("neu", "참고", "neu")}
  <h2>${st.tags.length ? `결과 <span class="sub">${res.length}개 종목 · 점수 높은 순</span>` : `<span class="sub">위에서 태그를 골라 보세요</span>`}</h2>
  ${st.tags.length ? (res.length ? res.map(rowHtml).join("") : `<div class="empty">이 태그를 모두 가진 종목이 없어요.<br>태그를 하나 빼 보세요.</div>`) : ""}
  <details class="excl" style="margin-top:16px"><summary>태그 기준 보기</summary><ul style="padding-left:18px">${Object.keys(TAGDESC).map(id => `<li><b>${esc(TAGNAME[id])}</b>: ${esc(TAGDESC[id])}</li>`).join("")}</ul></details>`;
}

/* ── 관심 / 투자자 / 정보 ── */
function viewWatch(){
  const list = [...watch].map(t => baseOf(t)).filter(Boolean).sort((a,b) => rankKey(b) - rankKey(a));
  return `<h2 style="margin-top:18px">관심종목 <span class="sub">${list.length}개</span></h2>` +
    (list.length ? list.map(rowHtml).join("") : `<div class="empty">아직 관심종목이 없어요.<br>종목 오른쪽의 ★을 눌러 담아 보세요.<br><button class="btn" style="margin-top:14px" data-go="list">종목 둘러보기</button></div>`);
}
function viewGuide(){
  const v = inv(), C = dom() === "coin";
  return `<h2 style="margin-top:18px">${C ? "매매이론" : "투자 거장"} <span class="sub">${members().length}${C ? "개 · 추세추종 / 돌파·변동성 / 눌림·역추세" : "인 · 현인 15 (성장주 / 저평가 / 복합) + 차트 현인 5"}</span></h2>
  ${segHtml()}
  ${profileCard(v)}
  ${groupsNow().map(g => `<div class="gh-t"><span class="gtag g-${g}">${esc(DATA.groups[g].name)}</span><small>${esc(DATA.investors[BY_ID[g]].tagline)}</small></div>
    ${members(g).map(x => `<button class="icard" data-inv="${BY_ID[x.id]}" aria-pressed="${x.id===v.id}">${pf(x, 54)}<span><b>${esc(x.name)}</b><small>${esc(x.profile.role)}</small></span></button>`).join("")}`).join("")}
  ${isCons(v) ? "" : `<h2>점수는 이렇게 매겨요 <span class="sub">${esc(v.name)} · 100점 만점</span></h2>
  <div class="card">${(v.rubric || []).map(([name, max]) => `<div class="pts-row"><span>${esc(name)}</span><b>${max}점</b></div>`).join("")}
    <p class="note">${C ? "거래대금이 작은 코인은 점수를 최대 15% 깎습니다(체결·유동성 위험). 점수와 별개로 '신호 충족' 여부가 매수 신호 등급을 정합니다." : "금융업 등 일부 종목은 해당 없는 항목을 빼고 나머지 점수를 100점으로 환산합니다."}</p></div>`}
  <h2>${C ? "진입가 · 목표가 · 손절가는요?" : "매수가 · 매도가 · 손절가는요?"}</h2>
  <div class="card"><ol class="steps">${(v.price_rules||[]).map(p => `<li>${esc(p)}</li>`).join("")}</ol>
    <p class="note">${C ? "코인은 재무제표가 없어 가격 전략을 ATR(평균 변동폭)로 계산합니다. 가격 흐름은 '버틸 수 있나'를 점검하는 용도로 따로 보여줍니다." : "가격 전략은 차트가 아니라 재무제표로 추정한 내재가치에서 계산합니다. 주가 흐름은 '버틸 수 있나'를 점검하는 용도로 따로 보여줍니다."}</p></div>`;
}
function viewAbout(){
  const ios = /iphone|ipad|ipod/i.test(navigator.userAgent) && !standalone;
  return `<h2 style="margin-top:18px">더보기</h2>
  <div class="menu"><button data-go="guide"><b>👤 투자 거장 소개</b><small>누가 어떤 기준으로 보는지</small></button></div>
  <div class="card"><h3>앱으로 설치</h3>
    ${standalone ? `<p class="disc" style="margin:0">이미 앱으로 실행 중입니다. ✓</p>` : `
    <p class="disc" style="margin:0 0 12px">홈 화면에 추가하면 앱처럼 열리고, 인터넷이 끊겨도 마지막 화면을 볼 수 있어요.</p>
    <button class="btn" id="installBtn" ${deferred ? "" : "hidden"}>앱으로 설치하기</button>
    ${ios ? `<div class="hint">Safari 하단의 공유 버튼 → "홈 화면에 추가"를 눌러 주세요.</div>` : (!deferred ? `<div class="hint">브라우저 메뉴(⋮)에서 "앱 설치" 또는 "홈 화면에 추가"를 선택하세요.</div>` : "")}`}
  </div>
  <div class="card"><h3>어떻게 순위를 정하나요?</h3><p class="disc" style="margin:0 0 8px">${DATA.investors.filter(x => !isCons(x) && x.domain === "stock").length}명의 투자자(재무로 판단하는 현인 15명 + 일봉 차트로 판단하는 차트 현인 5명)가 각자의 기준으로 종목을 채점합니다. 종합 순위는 성장주·저평가·복합·차트 네 진영의 추천 비율을 똑같이 반영하고, 아래 세 가지 보정을 더합니다.</p>
    <ol class="steps"><li><b>성장 체질</b>: 매출 성장과 산업 성장이 멈춘 '가치 함정'은 등급을 낮춥니다.</li><li><b>주가 추세</b>: 싸 보여도 계속 떨어지는 종목(떨어지는 칼날)은 등급과 순위를 낮춥니다.</li><li><b>업종 분산</b>: TOP 5에는 같은 업종을 최대 2개까지만 올립니다.</li></ol>
    <p class="disc" style="margin:10px 0 0">📶 <b>이평선 정배열</b>은 4·12·24·40주 이동평균(약 20·60·120·200일선)이 위에서부터 차례로 쌓이고 주가가 그 위에 있는 종목에 붙는 표시입니다. 순위에는 반영하지 않고 참고용으로만 보여줍니다.</p></div>
  ${BY_ID.call !== undefined ? `<div class="card"><h3>코인은 어떻게 평가하나요?</h3>
    <p class="disc" style="margin:0 0 8px">코인은 재무제표가 없어서 <b>차트 매매이론 15개</b>(추세추종 5·돌파·변동성 5·눌림·역추세 5)가 각자의 규칙으로 채점합니다. 터틀, 와인스타인, 미너비니, 다우, 일목균형표, 래리 윌리엄스, 리버모어, 다바스, 오닐, 볼린저, 코너스, 그랜빌, 와일더, 아펠, 엘더의 공개된 규칙을 단순화한 모의 평가입니다.</p>
    <p class="disc" style="margin:0 0 8px">종합 순위는 세 진영의 신호 비율을 똑같이 반영하고, 하락 추세(떨어지는 칼날)·급락 중 코인은 등급과 순위를 낮춥니다. 진입·목표·손절가는 ATR(평균 변동폭) 기준입니다.</p>
    <p class="disc" style="margin:0">시세는 <b>업비트 공개 시세</b>(원화마켓 거래대금 상위 ${DATA.coin_count ?? ""}개, 일봉 최대 600일)이고, <b>매시간</b> 주식과 함께 갱신되고, 업비트 4시간 봉이 마감되는 시각(01·05·09·13·17·21시)에도 반드시 갱신됩니다. 마지막 코인 갱신: ${esc(DATA.coin_fetched || "-")}. 코인은 24시간 거래되고 변동성이 매우 커 원금을 크게 잃을 수 있습니다.</p></div>` : ""}
  <div class="card"><h3>QR 코드 · 사이트 링크</h3>
    <div class="share"><img src="qr.png" alt="사이트로 연결되는 QR 코드" width="150" height="150">
      <div><div class="sub" style="margin-bottom:4px">폰 카메라로 찍으면 바로 열려요</div>
        <a class="url" href="${SITE_URL}" target="_blank" rel="noopener">${SITE_URL.replace("https://", "")}</a>
        <div class="btns"><button class="chip" data-copy="1">🔗 링크 복사</button><button class="chip" data-share="1">📤 공유하기</button><a class="chip" href="qr.png" download="legend-picks-qr.png">⬇ QR 저장</a></div></div></div>
    <p class="note">친구에게 이 QR을 보여주거나 링크를 보내면 같은 앱을 바로 열 수 있어요. 열린 뒤 홈 화면에 추가하면 앱처럼 쓸 수 있습니다.</p></div>
  <div class="card"><h3>화면 모드</h3><div class="legend-chips">${THEMES.map(([k, t]) => `<button class="chip" data-theme-set="${k}" aria-pressed="${themeMode === k}">${t}</button>`).join("")}</div>
    <p class="note">파스텔 카드 색은 라이트 모드에서 가장 선명하게 보여요. 자동은 폰의 화면 모드 설정을 따라갑니다.</p></div>
  <div class="card"><h3>카드 색 안내</h3><div class="palette">
    ${[["strong","민트","강력 매수 후보","여러 투자자가 한목소리로 좋게 봐요"],["buy","스카이","매수 후보","일부 투자자가 매수 후보로 봐요"],["wait","버터","훌륭한 기업 · 가격 부담","기업은 좋은데 가격이 비싸요"],["hold","라벤더","보통 · 관찰","의견이 갈리거나 조건 일부만 충족해요"],["pass","로즈","부적합","기준에 맞지 않아요"]]
      .map(([k, c, t, d]) => `<div class="sw tn-${k}"><i></i><span>${c} · ${t}<small>${d}</small></span></div>`).join("")}</div></div>
  <div class="card"><h3>데이터와 방법</h3><p class="disc" style="margin:0 0 8px">Yahoo Finance(yfinance) 연간 재무제표(최근 약 4년)와 최근 5년 주간 주가를 씁니다. 매시간 자동으로 갱신합니다.</p>
    <p class="disc" style="margin:0 0 8px">🕐 <b>시세·평가 기준 시각</b>: ${esc(DATA.fetched)} (한국시간, ${esc(fresh().rel)}). 이 시각에 시세와 재무를 받아 점수·가격 전략·태그를 다시 계산했어요. 장중에는 실시간 가격과 다를 수 있습니다.</p>
    <p class="disc" style="margin:0 0 8px">📒 <b>재무제표 기준</b>: 대부분 ${DATA.fy}년 결산을 포함한 최근 연간 재무입니다. 새 결산이 나오면 데이터 제공처에 반영되는 시점부터 바뀌어요.</p>
    <p class="disc" style="margin:0">내재가치는 최근 3년 평균 잉여현금흐름(금융업은 순이익)을 할인율 10%·최대 8% 성장·영구성장 3%로 계산한 보수적 추정치이고, 성장주 투자자는 이익 성장률을 반영한 5년 뒤 가치를 씁니다. 일부 종목은 데이터가 비어 평가에서 제외됩니다. 투자자 소개는 공개된 정보를 요약한 것이며 사진은 Wikimedia Commons의 자유 이용 사진입니다.</p></div>
  <div class="card"><h3>꼭 읽어주세요</h3><p class="disc" style="margin:0"><b>참고용 모의 평가입니다.</b> 이 앱은 투자 거장들이 공개적으로 밝힌 원칙을 수치로 옮긴 것으로, 해당 투자자 본인의 판단이 아니며 투자 권유나 투자 자문이 아닙니다. 제시된 매수가·매도가·손절가도 재무 기반 추정치일 뿐 수익을 보장하지 않습니다. 투자 판단과 그 결과에 대한 책임은 본인에게 있습니다.</p></div>`;
}

/* ── 상세 시트 ── */
function ladder(L, cur){
  const vals = [L.stop, L.buy, L.price, L.sell];
  const lo = Math.min(...vals) * 0.9, hi = Math.max(...vals) * 1.08, span = hi - lo;
  const p = v => Math.max(7, Math.min(93, (v - lo) / span * 100));
  const w = (a, b) => Math.max(0, (b - a) / span * 100);
  const zones = `<i class="z-x" style="width:${w(lo,L.stop)}%"></i><i class="z-b" style="width:${w(L.stop,L.buy)}%"></i><i class="z-w" style="width:${w(L.buy,L.sell)}%"></i><i class="z-s" style="width:${w(L.sell,hi)}%"></i>`;
  // 가격표가 서로 겹치지 않게: 손절은 눈금 왼쪽(r), 진입·매수는 눈금 오른쪽(l)에서 시작, 목표·매도는 눈금 왼쪽으로 끝(r)
  const pin = (cls, pos, label, v, dir, al = "c") => `<div class="pin ${cls} ${dir} ${al}" style="left:${pos}%"><span>${label}</span><b>${cur === "KRW" && Math.abs(v) >= 1e7 ? (v / 1e8).toFixed(2).replace(/0$/, "") + "억" : priceS(v,cur)}</b></div>`;
  const nm = L.kind === "coin" ? ["손절", "진입", "목표"] : ["손절", "매수", "매도"];
  return `<div class="ladder"><div class="track">${zones}</div>
    ${pin("x", p(L.stop), nm[0], L.stop, "up", "r")}${pin("b", p(L.buy), nm[1], L.buy, "up", "l")}${pin("s", p(L.sell), nm[2], L.sell, "up", "r")}
    ${pin("now", p(L.price), "현재가", L.price, "dn")}</div>`;
}
/* 분할 매수 계획: 한 번에 사지 않고 3번에 나눠, 떨어져도 버틸 수 있게 한다 */
function trancheHtml(s, L){
  const coin = L.kind === "coin";
  const c = s.currency, p1 = L.buy, p2 = coin ? L.buy - L.atr : L.buy * 0.92, p3 = coin ? L.buy - 2 * L.atr : L.buy * 0.85;
  const avg = (p1 + p2 + p3) / 3, stopAvg = coin ? L.stop : avg * (1 - L.stop_pct);
  const now = L.status === "buy";
  const down = s.trend === "down";
  return `<div class="plan"><div class="plan-t">분할 ${coin ? "진입" : "매수"} 계획 <span class="sub">3번에 나눠서 ${coin ? "들어가요" : "사요"}</span></div>
    <div class="tr3">
      <div class="t"><span>1차 · 1/3</span><b>${priceS(p1,c)}</b><small>${now ? "지금 가능한 가격" : "이 가격까지 기다리기"}</small></div>
      <div class="t"><span>2차 · 1/3</span><b>${priceS(p2,c)}</b><small>${coin ? "1ATR 더 눌렸거나, 추세가 확인되면" : "더 빠지거나, 추세가 돌아서면(40주선 회복)"}</small></div>
      <div class="t"><span>3차 · 1/3</span><b>${priceS(p3,c)}</b><small>${coin ? "추세 훼손 신호가 없을 때만" : "재무 손절 신호가 없을 때만"}</small></div>
    </div>
    <p class="note">3번 모두 ${coin ? "들어가면" : "사면"} 평균단가는 약 ${price(avg,c)}, 손절은 ${coin ? "처음 정한 손절가인" : `평균단가의 -${Math.round(L.stop_pct*100)}%인`} ${price(stopAvg,c)}입니다. 현재가가 이미 더 낮다면 현재가를 기준으로 같은 방식으로 나눠 ${coin ? "들어가세요" : "사세요"}.${down ? ` <b>지금은 하락 추세라 1차도 절반만 ${coin ? "들어가는" : "사는"} 편이 마음 편합니다.</b>` : ""}</p></div>`;
}
function stratHtml(s, v){
  const L = s.levels, c = s.currency, si = statusInfo(s), coin = L && L.kind === "coin";
  if(!L) return `<div class="strat"><h4>${isCoin(s) ? "매매 전략" : "가격 전략"}</h4><div class="status wait">${esc(si.long)}</div></div>`;
  const lowQ = !isCons(v) && !coin && s.quality < 65 ? `<p class="note" style="color:var(--wait)">※ 기업 질 점수가 낮아 ${esc(v.name)} 기준으로는 매수 대상이 아닙니다. 가격 전략은 참고용입니다.</p>` : "";
  const how = coin ? (isCons(v) ? "신호를 낸 이론들이 제시한 가격의 평균입니다" : `진입가는 이론의 신호 가격, 손절가는 진입가 아래 ${(L.stop_pct*100).toFixed(1)}%(ATR 기준), 목표가는 위험의 ${(L.rr || 0).toFixed(1)}배입니다`)
    : (isCons(v) ? "추천한 투자자들이 제시한 가격의 평균입니다" : `매수가 = 적정가 − 안전마진 ${Math.round(L.req_mos*100)}% · 매도가 = 적정가 · 손절가 = 진입가의 -${Math.round(L.stop_pct*100)}%`);
  const nm = coin ? ["진입가", "목표가", "손절가"] : ["매수가", "매도가", "손절가"];
  return `<div class="strat">
    <h4>${coin ? "매매 전략" : "가격 전략"} <span class="sub">${coin ? `ATR ${pct(L.atr_pct)} 기준` : `재무 기준 · 적정가 ${price(L.fair,c)}`}</span></h4>
    <div class="status ${si.k}">${esc(si.long)}</div>
    ${ladder(L, c)}
    <div class="tiles">
      <div class="tile b"><span>${nm[0]}</span><b>${priceS(L.buy,c)}</b><small>현재가 ${sgn(L.to_buy)}</small></div>
      <div class="tile s"><span>${nm[1]}</span><b>${priceS(L.sell,c)}</b><small>현재가 ${sgn(L.to_sell)}</small></div>
      <div class="tile x"><span>${nm[2]}</span><b>${priceS(L.stop,c)}</b><small>${coin ? "진입가 " : "진입가 "}-${(L.stop_pct*100).toFixed(coin ? 1 : 0)}%</small></div>
    </div>
    ${fold("plan", coin ? "분할 진입 계획 · 기대수익" : "분할 매수 계획 · 기대수익", `<div class="kv3">
      <div class="stat"><b>${sgn(L.upside)}</b><span>${coin ? "목표까지 기대수익" : "진입 후 기대수익"}</span></div>
      <div class="stat"><b>1 : ${L.rr.toFixed(1)}</b><span>손익비</span></div>
      <div class="stat"><b>${coin ? pct(L.atr_pct) : Math.round(L.req_mos*100) + "%"}</b><span>${coin ? "하루 변동폭(ATR)" : "요구 안전마진"}</span></div>
    </div>
    <p class="note">${how}.</p>${lowQ}
    ${trancheHtml(s, L)}`)}
  </div>`;
}
/* 5년 주가 흐름: 사람이 이 종목을 들고 어떤 시간을 보냈을지 보여준다 */
function chartSvg(t, L, cur){
  const sp = DATA.charts[t];
  if(!sp || sp.length < 10) return "";
  const W = 320, H = 132, px = 6, py = 12;
  const lo = Math.min(...sp), hi = Math.max(...sp);
  const nm = L && L.kind === "coin" ? ["진입", "목표", "손절"] : ["매수", "매도", "손절"];
  const lines = L ? [[nm[0], L.buy, "var(--c-buy)"], [nm[1], L.sell, "var(--c-sell)"], [nm[2], L.stop, "var(--c-stop)"]] : [];
  const inR = v => v > lo * 0.55 && v < hi * 1.7;
  let dlo = lo, dhi = hi;
  lines.forEach(([, v]) => { if(inR(v)){ dlo = Math.min(dlo, v); dhi = Math.max(dhi, v); } });
  const pad = (dhi - dlo) * 0.08 || 1; dlo -= pad; dhi += pad;
  const X = i => px + (W - 2*px) * i / (sp.length - 1), Y = v => H - py - (H - 2*py) * (v - dlo) / (dhi - dlo);
  const path = sp.map((v,i) => (i ? "L" : "M") + X(i).toFixed(1) + " " + Y(v).toFixed(1)).join("");
  const last = sp.length - 1;
  const hl = lines.map(([k, v, col]) => inR(v) ? `<line x1="${px}" x2="${W-px}" y1="${Y(v).toFixed(1)}" y2="${Y(v).toFixed(1)}" style="stroke:${col}" stroke-dasharray="4 3" stroke-width="1.2"/><text x="${W-px-2}" y="${(Y(v)-3).toFixed(1)}" text-anchor="end" font-size="9.5" font-weight="700" style="fill:${col}">${k}</text>` : "").join("");
  return `<svg class="spark" viewBox="0 0 ${W} ${H}" role="img" aria-label="최근 가격 흐름">
    <defs><linearGradient id="sg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" style="stop-color:var(--gold);stop-opacity:.35"/><stop offset="1" style="stop-color:var(--gold);stop-opacity:0"/></linearGradient></defs>
    <path d="${path}L${X(last).toFixed(1)} ${H-py}L${X(0).toFixed(1)} ${H-py}Z" fill="url(#sg)"/>${hl}
    <path d="${path}" fill="none" style="stroke:var(--ink)" stroke-width="1.8" stroke-linejoin="round"/>
    <circle cx="${X(last).toFixed(1)}" cy="${Y(sp[last]).toFixed(1)}" r="3.6" style="fill:var(--gold);stroke:var(--card)" stroke-width="1.5"/></svg>
    <div class="axis"><span>${String(t).startsWith("KRW-") ? "약 20개월 전" : "5년 전"}</span><span>현재 ${price(sp[last], cur)}</span></div>`;
}
function painHtml(s){
  const p = DATA.px[s.ticker];
  if(!p) return "";
  const C = isCoin(s);
  const pain = s.pain ?? 0;
  const lvl = pain < 25 ? ["낮음","ok"] : pain < 50 ? ["보통","mid"] : pain < 75 ? ["높음","high"] : ["매우 높음","max"];
  const why = C ? ((p.ret_1y ?? 0) < -0.3 ? "코인은 한 번 크게 빠지면 회복에 오래 걸리는 경우가 많아요. 추세가 돌아선 뒤에 들어가는 편이 안전합니다." : "")
    : (s.ni_yoy != null && s.ni_yoy < 0 && (p.ret_1y ?? 0) < -0.1) ? "주가가 빠지는 동안 이익도 줄었습니다. 하락 이유가 재무에 있을 수 있어요(가치 함정 주의)."
            : ((p.ret_1y ?? 0) < -0.15 && (s.ni_yoy == null || s.ni_yoy >= 0)) ? "이익은 줄지 않았는데 주가만 빠졌습니다. 시장의 불안 심리 때문일 수 있어요."
            : "";
  const span = C ? "약 20개월" : "5년";
  const wait = p.cur_uw > 8 ? ` 지금도 ${span} 내 최고가 아래에서 ${months(p.cur_uw)}개월째 머무는 중입니다.` : "";
  return `<div class="card chartcard">
    <h4>${C ? "가격 흐름" : "주가 흐름"} · 버틸 수 있나? <span class="sub">${C ? "최근 약 20개월(일봉)" : "최근 5년(주간)"}</span></h4>
    <div class="line" style="margin:2px 0 6px">${trendPill(s)}${alignPill(s)}${s.knife ? `<span class="sub">${C ? "1년" : "3년"} 고점 대비 ${sgn(p.dd_3y)}</span>` : ""}</div>
    ${s.align ? `<p class="note" style="margin:0 0 6px">📶 <b>이평선 정배열</b>: ${C ? "20·60·120·200일 이동평균" : "4주·12주·24주·40주 이동평균(약 20·60·120·200일선)"}이 위에서부터 차례로 쌓여 있고 ${C ? "가격이" : "주가가"} 그 위에 있어, 상승 추세가 이어지는 모양입니다.</p>` : ""}
    ${chartSvg(s.ticker, s.levels, s.currency)}
    <div class="kv4">
      <div class="stat ${p.ret_1y<0?"bad":"good"}"><b>${sgn(p.ret_1y)}</b><span>1년 수익률</span></div>
      <div class="stat ${p.dd_3y<-0.3?"bad":""}"><b>${sgn(p.dd_3y)}</b><span>${C ? "1년" : "3년"} 고점 대비</span></div>
      <div class="stat"><b>${sgn(p.max_dd)}</b><span>${C ? "최대 낙폭" : "5년 최대 낙폭"}</span></div>
      <div class="stat"><b>${months(p.longest_uw)}개월</b><span>고점 회복 최장</span></div>
    </div>
    <div class="gauge"><div class="gl"><b>버티기 난이도 <em class="pn-${lvl[1]}">${lvl[0]}</em></b><span>${pain}/100</span></div><div class="bar"><i class="pn-${lvl[1]}" data-w="${pain}"></i></div></div>
    <p class="note">지난 ${span} 동안 이 ${C ? "코인은" : "종목은"} 최대 ${sgn(p.max_dd)}까지 빠졌고, 한 번 빠진 뒤 이전 고점을 되찾기까지 최장 ${months(p.longest_uw)}개월이 걸렸습니다.${wait} ${why}</p>
    ${s.knife ? `<div class="warn" style="margin:10px 0 0"><b>🔪 떨어지는 칼날 주의</b>${C ? "단기 신호가 있어도 장기 추세가 아직 아래를 향합니다. 반등이 짧게 끝나기 쉬워요. 한 번에 들어가지 말고 분할 진입 계획대로 나눠서, 추세가 돌아선 뒤에 비중을 늘리세요."
      : "재무상 싸 보여도 추세가 아직 아래를 향합니다. 저평가가 4~5년 이어져도 사람이 버티기는 쉽지 않아요. 한 번에 사지 말고 분할 매수 계획대로 나눠서, 추세가 돌아선 뒤에 비중을 늘리세요."}</div>` : ""}
  </div>`;
}
function growthHtml(s){
  if(s.gh == null) return "";
  const lab = {growth:["성장 체질","ok"], mature:["성숙·안정","mid"], slow:["성장 둔화 우려","high"], unknown:["미분류","mid"]}[s.struct];
  return `<div class="card">
    <h4 style="margin:0 0 6px;font-family:var(--serif);font-size:17px">성장 체질 <em class="pn-${lab[1] === "ok" ? "ok" : lab[1]}" style="font-style:normal">${lab[0]}</em> <span class="sub">${s.gh}/100</span></h4>
    <div class="kv3"><div class="stat"><b>${pct(s.rev_cagr)}</b><span>매출 연평균</span></div><div class="stat"><b>${pct(s.rev_yoy)}</b><span>최근 매출 성장</span></div><div class="stat ${s.ni_yoy<0?"bad":""}"><b>${pct(s.ni_yoy)}</b><span>최근 이익 성장</span></div></div>
    <p class="note">${esc(s.industry || "")} 산업의 평균 성장까지 합쳐 계산합니다. 점수가 낮으면 '싸 보이지만 성장이 멈춘 업종(가치 함정)'일 수 있어 추천 등급을 낮춥니다.</p></div>`;
}
function votesHtml(s){
  const C = isCoin(s);
  return `<div class="sec-t">${C ? "매매이론별 판단" : "투자자별 판단"} <span class="sub">누르면 그 ${C ? "이론" : "투자자"}의 상세 보기</span></div>` + s.votes.map(x => {
    const idx = BY_ID[x.id], iv = DATA.investors[idx];
    return `<div class="vote" data-sinv="${idx}">${pf(iv, 34)}
      <div><b>${esc(x.name)}</b><small class="gtag g-${x.group}">${esc(DATA.groups[x.group].name)}</small><div class="vb"><i style="width:${x.score}%;background:${TONE_COLOR[x.tone]}"></i></div></div>
      <div class="r"><span class="tag t-${x.tone}">${esc(x.verdict)}</span><div>${x.score}점</div></div></div>`;
  }).join("");
}
function checksHtml(s){
  return s.checks.map(c => {
    const mk = c.ok === null ? `<span class="mk x">–</span>` : c.ok ? `<span class="mk y">✓</span>` : `<span class="mk n">✕</span>`;
    const r = c.max ? c.points / c.max : 0;
    const cls = c.ok === null ? "" : r >= .7 ? "" : r >= .4 ? "m" : "n";
    return `<div class="chk"><div class="h">${mk}${esc(c.name)}<span class="pts">${c.max ? c.points + " / " + c.max : "해당없음"}</span></div>
      ${c.max ? `<div class="bar"><i class="${cls}" data-w="${Math.round(r*100)}"></i></div>` : `<div style="height:8px"></div>`}<div class="d">${esc(c.detail)}</div></div>`;
  }).join("");
}
function sheetHtml(t){
  const v = sinv(), s = IDX[st.sheetInv].get(t), base = baseOf(t), C = isCoin(s);
  const w = s.warnings || [];
  const tabs = DATA.investors.map((x,i) => IDX[i].has(t) && (!isCons(x) || isAllCons(x) || i === st.sheetInv)
    ? `<button class="ic ${isAllCons(x)?"all":""}" data-sinv="${i}" aria-pressed="${i===st.sheetInv}">${isCons(x) ? "" : pf(x, 24)}${esc(x.short)}</button>` : "").join("");
  const stats = C ? [[(base.rsi14 ?? 0).toFixed(0), "RSI(14)"], [(base.adx ?? 0).toFixed(0), "ADX(추세 강도)"], [pct(base.atr_pct), "하루 변동폭 ATR"], [Math.round((base.value24 ?? 0) / 1e8).toLocaleString() + "억", "24시간 거래대금"]]
    : [[pct(base.roe), "평균 ROE"], [pct(base.op_margin), "영업이익률"], [base.per ? base.per.toFixed(1)+"배" : "-", "PER"], [sgn(base.mos), "안전마진"]];
  const cls = C ? ["", "", "", ""] : ["", "", "", base.mos>=.15?"good":base.mos<0?"bad":""];
  return `<div class="grab"></div>
  <div class="head">${(i => st.seq.length > 1 && i >= 0 ? `<span class="nv"><button data-snav="-1" aria-label="이전 종목" ${i === 0 ? "disabled" : ""}>‹</button><small>${i + 1}/${st.seq.length}</small><button data-snav="1" aria-label="다음 종목" ${i === st.seq.length - 1 ? "disabled" : ""}>›</button></span>` : "")(st.seq.indexOf(t))}<span class="pill">${isCons(v) ? esc(v.short) + " " + (s.count ?? 0) + "/" + (s.total ?? 0) : esc(v.name) + " 기준"}</span><span class="sp"></span>
    <button class="star ${watch.has(t)?"on":""}" data-star="${esc(t)}" aria-label="관심종목"><svg viewBox="0 0 24 24">${ICONS.star}</svg></button>
    <button class="xbtn" data-close aria-label="닫기">✕</button></div>
  <div class="body">
    <div class="sh-top">${ring(s)}<div><h3>${esc(s.name)}</h3><div class="sub">${esc(tk(s))} · ${esc(s.sector||"")}<br>현재 ${price(s.price,s.currency)} · ${C ? `24시간 ${sgn(s.change24)}` : `시총 ${money(s.market_cap,s.currency)}`}<br><span class="asof-s">🕐 시세 ${fresh().abs} 기준 (${fresh().rel})</span></div><span class="tag t-${s.tone}">${esc(s.verdict)}</span> ${alignPill(base)}</div></div>
    <div class="tgs sh-tags">${tagsHtml(s, 4)}</div>
    <p class="summary">${v.detailLoaded ? esc(s.summary) : (st.detailErr ? "상세 평가를 불러오지 못했어요. 인터넷 연결을 확인해 주세요." : "평가 상세를 불러오는 중…")}</p>
    ${stratHtml(s, v)}
    ${w.length ? `<div class="warn"><b>⚠ ${C ? "추세 훼손 신호" : "재무 손절 신호"}</b><ul>${w.map(x => `<li>${esc(x)}</li>`).join("")}</ul>${C ? "이런 신호가 겹치면 진입을 미루거나 비중을 줄이는 것을 검토하세요." : "이런 신호는 가격과 무관하게 매도를 검토할 이유입니다."}</div>`
               : `<div class="safe">✓ ${C ? "추세 훼손 신호 없음" : "재무 손절 신호 없음"}</div>`}
    ${fold("who", C ? "이론별 판단 · 체크리스트" : "투자자별 판단 · 체크리스트", `<div class="stabs">${tabs}</div>` +
      (isCons(v) ? votesHtml(s) : `<div class="sec-t">${esc(v.name)} 체크리스트 <span class="sub">${C ? "" : `기업 질 ${s.quality}점 · `}총점 ${s.score}점</span></div>${v.detailLoaded ? checksHtml(s) : `<div class="empty">${st.detailErr ? "체크리스트를 불러오지 못했어요." : "체크리스트를 불러오는 중…"}</div>`}`),
      isCons(v) ? `${s.count ?? 0}/${s.total ?? 0}${C ? "개 신호" : "명 추천"}` : esc(v.short))}
    ${fold("flow", C ? "가격 흐름 · 버틸 수 있나?" : "주가 흐름 · 버틸 수 있나?", painHtml(base), "")}
    ${fold("growth", "성장 체질", growthHtml(base), "")}
    ${fold("tags", "태그 전체", glanceHtml(s).replace('<div class="gl-h">한눈에 보기</div>', ""), "")}
    ${fold("stats", C ? "지표" : "재무 지표", `<div class="kv">${stats.map(([val, lab], i) => `<div class="stat ${cls[i]}"><b>${val}</b><span>${lab}</span></div>`).join("")}</div>`, "")}
    <p class="note">${C ? `시세는 ${fresh().full}(한국시간)에 업비트에서 받은 값이고, 지표는 일봉(마감 봉 + 오늘 진행 중인 봉) 기준입니다. 코인은 24시간 거래되고 변동성이 매우 커 원금을 크게 잃을 수 있어요. 참고용 추정이며 투자 권유가 아닙니다.`
      : `시세는 ${fresh().full}(한국시간) 수집 값이며 장중에는 실시간 가격과 다를 수 있어요. 재무 데이터는 ${esc(base.years)} 연간 결산 기준입니다. 참고용 추정이며 투자 권유가 아닙니다.`}</p>
  </div>`;
}
function renderSheet(keepScroll){
  const sh = $("sheet"), old = keepScroll ? (sh.querySelector(".body")||{}).scrollTop : 0;
  sh.innerHTML = sheetHtml(st.sheet);
  const b = sh.querySelector(".body"); b.scrollTop = old || 0;
  requestAnimationFrame(() => requestAnimationFrame(() => sh.querySelectorAll(".bar i").forEach(x => x.style.width = x.dataset.w + "%")));
}
/* 시트를 그리고, 상세가 아직 없으면 불러온 뒤 다시 그린다 */
function showSheet(){
  if(!st.seq.includes(st.sheet)) st.seq = currentSeq().includes(st.sheet) ? currentSeq() : [st.sheet];
  const i = st.sheetInv;
  st.detailErr = false;
  renderSheet(false);
  if(!DATA.investors[i].detailLoaded) loadDetail(i).then(ok => {
    if(st.sheet && st.sheetInv === i){ st.detailErr = !ok; renderSheet(true); }
  });
}
/* ── 뒤로가기: 탭 이동과 상세 팝업을 브라우저 기록에 남겨, 뒤로가기가 앱 종료가 아니라 이전 화면으로 가게 한다 ── */
const snap = () => ({k: "app", view: st.view, inv: st.inv, market: st.market, tags: st.tags, sheet: st.sheet, sheetInv: st.sheetInv});
const pushNav = () => { try{ history.pushState(snap(), ""); }catch(e){} };
/* 현재 기록 항목을 지금 화면 상태로 갱신 (필터·투자자·시장을 바꿔도 뒤로 갔다 오면 그대로 복원) */
const syncNav = () => { try{ if(history.state && history.state.k === "app") history.replaceState(snap(), ""); }catch(e){} };
const sheetVisual = on => { $("sheet").classList.toggle("on", on); $("scrim").classList.toggle("on", on); document.body.classList.toggle("lock", on); };
const sheetInvFor = t => IDX[st.inv].has(t) ? st.inv : (t.startsWith("KRW-") ? BY_ID.call : BY_ID.all);
/* 지금 보고 있는 목록의 순서(홈 TOP5 · 종목 · 태그 결과 · 관심): 상세에서 옆으로 밀면 이 순서대로 넘어간다 */
function currentSeq(){
  const all = inv().stocks.filter(s => s.market === st.market);
  const L = st.view === "home" ? topPicks(all) : st.view === "list" ? filtered() : st.view === "tags" ? tagResults(all)
          : st.view === "watch" ? [...watch].map(baseOf).filter(Boolean).sort((a,b) => rankKey(b) - rankKey(a)) : [];
  return L.map(s => s.ticker);
}
function openSheet(t, push = true){
  if(!baseOf(t)) return;
  st.sheet = t; st.fold = {};
  st.seq = currentSeq();
  st.sheetInv = sheetInvFor(t);
  showSheet();
  sheetVisual(true);
  if(push) pushNav();
}
function stepSheet(d){
  const i = st.seq.indexOf(st.sheet), j = i + d;
  if(i < 0 || j < 0 || j >= st.seq.length){ if(i >= 0) toast(d > 0 ? "마지막 종목이에요" : "첫 번째 종목이에요"); return; }
  st.sheet = st.seq[j];
  st.sheetInv = sheetInvFor(st.sheet);
  showSheet(); syncNav();
  const b = $("sheet").querySelector(".body");
  if(b && b.animate) b.animate([{transform: `translateX(${d > 0 ? 36 : -36}px)`, opacity: 0}, {transform: "none", opacity: 1}], {duration: 220, easing: "ease-out"});
}
function closeSheet(fromPop){
  if(!st.sheet) return;
  st.sheet = null;
  sheetVisual(false);
  if(!fromPop && history.state && history.state.sheet) history.back();   // 열 때 쌓은 기록을 되돌린다
}

/* ── 내비/렌더 ── */
function renderNav(){
  $("nav").innerHTML = TABS.map(([k,l,ic]) => `<button data-go="${k}" ${(st.view===k || (k==="about" && st.view==="guide"))?'aria-current="page"':""}><svg class="i" viewBox="0 0 24 24">${ICONS[ic]}</svg>${l}${k==="watch"&&watch.size?`<span class="badge2" style="display:grid">${watch.size}</span>`:""}</button>`).join("");
}
function render(){
  updateStamp();
  renderNav();
  const f = fresh();
  const stale = f.lvl === "old" ? `<div class="stale">⚠ 데이터가 오래됐어요. 마지막 갱신은 <b>${f.full}</b>(${f.rel})입니다. 갱신하는 PC가 꺼져 있었을 수 있어요. 지금 보이는 가격은 그 시각 기준입니다.</div>` : "";
  $("view").innerHTML = stale + {home:viewHome, list:viewList, tags:viewTags, watch:viewWatch, guide:viewGuide, about:viewAbout}[st.view]();
  if(st.view === "list") fillList();
  const ib = $("installBtn"); if(ib) ib.onclick = doInstall;
  syncNav();
}
function go(v){
  if(v !== st.view){ st.view = v; pushNav(); } else st.view = v;   // 다른 탭으로 갈 때만 기록을 쌓는다
  render(); window.scrollTo(0,0); const el = $("view"); el.style.animation = "none"; void el.offsetWidth; el.style.animation = "";
}
function toast(msg){ const t = $("toast"); t.textContent = msg; t.classList.add("on"); clearTimeout(toast.h); toast.h = setTimeout(() => t.classList.remove("on"), 1600); }

document.addEventListener("click", e => {
  const star = e.target.closest("[data-star]");
  if(star){
    e.stopPropagation();
    const t = star.dataset.star;
    if(watch.has(t)){ watch.delete(t); toast("관심종목에서 뺐어요"); } else { watch.add(t); toast("관심종목에 담았어요 ★"); }
    saveWatch(); renderNav();
    document.querySelectorAll(`[data-star="${CSS.escape(t)}"]`).forEach(b => { b.classList.toggle("on", watch.has(t)); b.setAttribute("aria-pressed", watch.has(t)); });
    if(st.view === "watch" && !st.sheet) render();
    return;
  }
  /* 종목의 태그를 누르면 태그 탭으로 이동(목록에서) 하거나 선택을 켜고 끈다(태그 탭에서) */
  const tg = e.target.closest("[data-tag]");
  if(tg && (st.view === "list" || st.view === "tags")){
    e.stopPropagation();
    const id = tg.dataset.tag;
    if(st.view === "list"){ st.tags = [id]; return go("tags"); }
    st.tags = st.tags.includes(id) ? st.tags.filter(x => x !== id) : [...st.tags, id];
    return render();
  }
  if(e.target.closest("[data-copy]")) return copyLink();
  if(e.target.closest("[data-share]")) return shareLink();
  const th = e.target.closest("[data-theme-set]");
  if(th){ setTheme(th.dataset.themeSet); return render(); }
  /* 시장 분포 칩: 눌러서 그 평가의 종목 목록으로 */
  const lg = e.target.closest("[data-legend]");
  if(lg){ st.tone = lg.dataset.legend; return go("list"); }
  const sel = e.target.closest("[data-tagsel]");
  if(sel){ const id = sel.dataset.tagsel; st.tags = st.tags.includes(id) ? st.tags.filter(x => x !== id) : [...st.tags, id]; return render(); }
  if(e.target.closest("[data-tagclear]")){ st.tags = []; return render(); }
  const pr = e.target.closest("[data-preset]");
  if(pr){ st.tags = [...presets()[+pr.dataset.preset][1]]; return render(); }
  const sn = e.target.closest("[data-snav]");
  if(sn) return stepSheet(+sn.dataset.snav);
  const t = e.target.closest("[data-open],[data-go],[data-m],[data-f],[data-o],[data-inv],[data-sinv],[data-close]");
  if(!t) return;
  if(t.dataset.close !== undefined) return closeSheet();
  if(t.dataset.sinv !== undefined){ st.sheetInv = +t.dataset.sinv; return showSheet(); }
  if(t.dataset.open) return openSheet(t.dataset.open);
  if(t.dataset.go){
    const v = t.dataset.go;
    // 상세 팝업이 열려 있으면 먼저 그 기록을 되돌려 닫고(popstate 에서), 그다음 이동한다 → 같은 화면 기록이 중복되지 않는다
    if(st.sheet && history.state && history.state.sheet){ pendingGo = v; return closeSheet(); }
    if(st.sheet){ st.sheet = null; sheetVisual(false); }
    return go(v);
  }
  if(t.dataset.m){ setMarket(t.dataset.m); return render(); }
  if(t.dataset.f){ st.tone = t.dataset.f; return fillList(); }
  if(t.dataset.o){ st.only = t.dataset.o; return fillList(); }
  if(t.dataset.inv !== undefined){
    st.inv = +t.dataset.inv; st.tone = "all"; render();
    if(st.view === "guide" || st.view === "home") window.scrollTo({top: 0, behavior: "smooth"});
    return;
  }
});
$("scrim").addEventListener("click", () => closeSheet());
document.addEventListener("keydown", e => {
  if(e.key === "Escape") closeSheet();
  if(st.sheet && e.key === "ArrowRight") stepSheet(1);
  if(st.sheet && e.key === "ArrowLeft") stepSheet(-1);
});
/* 상세 화면에서 손가락을 왼쪽으로 밀면 다음 순서(오른쪽에 있던 것이 나타남), 오른쪽으로 밀면 이전 순서 */
(() => {
  let x0 = 0, y0 = 0, ok = false;
  const sh = $("sheet");
  sh.addEventListener("touchstart", e => { const t = e.touches[0]; x0 = t.clientX; y0 = t.clientY; ok = e.touches.length === 1 && !e.target.closest(".stabs,.spark,.ichips,input,select"); }, {passive: true});
  sh.addEventListener("touchend", e => {
    if(!ok) return; ok = false;
    const t = e.changedTouches[0], dx = t.clientX - x0, dy = t.clientY - y0;
    if(Math.abs(dx) > 70 && Math.abs(dx) > Math.abs(dy) * 1.6) stepSheet(dx < 0 ? 1 : -1);
  }, {passive: true});
})();
let lastRootBack = 0, pendingGo = null;
window.addEventListener("popstate", e => {
  const s = e.state;
  if(s && s.k === "app"){
    // 기록 속 화면 상태로 되돌린다 (이전 탭, 상세 팝업 열림/닫힘)
    const same = s.view === st.view && s.inv === st.inv && s.market === st.market && JSON.stringify(s.tags || []) === JSON.stringify(st.tags);
    Object.assign(st, {view: s.view, inv: s.inv, market: s.market, tags: s.tags || [], sheet: s.sheet || null, sheetInv: s.sheetInv || 0});
    if(!same) render();
    if(st.sheet){ showSheet(); sheetVisual(true); } else sheetVisual(false);
    if(pendingGo){ const v = pendingGo; pendingGo = null; go(v); }
    return;
  }
  // 첫 기록(루트)까지 돌아왔다: 설치된 앱에서는 실수로 종료되지 않도록 '한 번 더 누르면 종료'
  if(standalone){
    if(Date.now() - lastRootBack < 2200) history.back();
    else { lastRootBack = Date.now(); toast("한 번 더 누르면 앱이 종료돼요"); pushNav(); }
  }
});
document.addEventListener("toggle", e => { const k = e.target.dataset && e.target.dataset.fold; if(k) st.fold[k] = e.target.open; }, true);
document.addEventListener("input", e => { if(e.target.id === "q"){ st.q = e.target.value; fillList(); } });
document.addEventListener("change", e => { if(e.target.id === "sort"){ st.sort = e.target.value; fillList(); } });

/* ── 설치 (PWA) ── */
let deferred = null;
const standalone = matchMedia("(display-mode: standalone)").matches || navigator.standalone || location.search.includes("standalone=1");  // 뒤의 조건은 테스트용
async function doInstall(){ if(!deferred) return; deferred.prompt(); await deferred.userChoice; deferred = null; if(st.view === "about") render(); }
window.addEventListener("beforeinstallprompt", e => { e.preventDefault(); deferred = e; if(st.view === "about") render(); });
window.addEventListener("appinstalled", () => { deferred = null; toast("앱이 설치됐어요 🎉"); });
if("serviceWorker" in navigator && location.protocol.startsWith("http")) navigator.serviceWorker.register("sw.js").catch(() => {});

/* 기록 초기화: 설치 앱은 [루트] → [홈] 두 칸으로 시작해 첫 화면에서의 뒤로가기를 가로챈다 */
if(history.state && history.state.k === "app"){
  const s = history.state;   // 새로고침: 보던 화면으로 복원 (상세 팝업은 닫은 채)
  Object.assign(st, {view: s.view, inv: s.inv, market: s.market, tags: s.tags || []});
} else if(standalone){
  try{ history.replaceState({k: "root"}, ""); history.pushState(snap(), ""); }catch(e){}
} else {
  try{ history.replaceState(snap(), ""); }catch(e){}
}
render();
/* 첫 화면이 뜬 뒤 종합 상세를 미리 받아 둔다 (종목을 누르면 바로 열리도록) */
setTimeout(() => { [0, 1, 2, 3].forEach(i => loadDetail(i)); }, 1200);
