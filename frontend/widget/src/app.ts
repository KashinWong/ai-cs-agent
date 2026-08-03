import "./theme.css";
import "./widget.css";
import { WidgetSocket, type Envelope } from "./ws-client";

const params = new URLSearchParams(location.search);
let CHANNEL_TOKEN = params.get("token") || (window as any).__CHANNEL_TOKEN__ || "";
const STORE_KEY = "ai_cs_conversation_id";

const root = document.getElementById("app")!;
root.innerHTML = `
  <div class="cs-widget">
    <header class="cs-head">
      <div class="cs-head-avatar">AI</div>
      <div class="cs-head-meta">
        <div class="cs-head-title">AI 智能客服</div>
        <div class="cs-head-sub"><span class="cs-dot"></span>在线为您服务</div>
      </div>
    </header>
    <div id="msgs" class="cs-msgs"></div>
    <div id="typing" class="cs-typing" hidden><span></span><span></span><span></span></div>
    <div class="cs-input">
      <textarea id="inp" rows="1" placeholder="输入您的问题…（Enter 发送，Shift+Enter 换行）"></textarea>
      <button id="send" class="cs-send" aria-label="发送">
        <svg viewBox="0 0 24 24" width="18" height="18"><path fill="currentColor" d="M3.4 20.4l17.45-7.48a1 1 0 000-1.84L3.4 3.6a.993.993 0 00-1.39.91L2 9.12c0 .5.37.93.87.99L17 12 2.87 13.88c-.5.07-.87.5-.87 1l.01 4.61c0 .71.73 1.2 1.39.91z"/></svg>
      </button>
    </div>
  </div>`;

const msgs = document.getElementById("msgs")!;
const inp = document.getElementById("inp") as HTMLTextAreaElement;
const sendBtn = document.getElementById("send")!;
const typing = document.getElementById("typing")!;

function scrollDown() {
  msgs.scrollTop = msgs.scrollHeight;
}

function showWelcome() {
  const el = document.createElement("div");
  el.className = "cs-welcome";
  el.innerHTML = `👋 您好！我是 AI 客服助手，可以帮您解答账号、支付、退款等常见问题。<br/>请描述您遇到的问题，答不上来时会为您转接人工。`;
  msgs.appendChild(el);
}

function bubble(source: string, text: string): HTMLSpanElement {
  const row = document.createElement("div");
  row.className = `cs-row cs-${source}`;
  const wrap = document.createElement("div");
  wrap.className = "cs-bubble-wrap";
  if (source === "agent") {
    const tag = document.createElement("div");
    tag.className = "cs-tag";
    tag.textContent = "人工客服";
    wrap.appendChild(tag);
  }
  const b = document.createElement("div");
  b.className = "cs-bubble";
  const span = document.createElement("span");
  span.textContent = text;
  b.appendChild(span);
  wrap.appendChild(b);
  row.appendChild(wrap);
  msgs.appendChild(row);
  scrollDown();
  return span;
}

function systemNote(text: string) {
  const el = document.createElement("div");
  el.className = "cs-note";
  el.textContent = text;
  msgs.appendChild(el);
  scrollDown();
}

let streaming: HTMLSpanElement | null = null;

function setTyping(on: boolean) {
  typing.hidden = !on;
  if (on) scrollDown();
}

function wsUrl(): string {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  const cid = localStorage.getItem(STORE_KEY);
  let u = `${proto}://${location.host}/ws/widget?channel_token=${encodeURIComponent(CHANNEL_TOKEN)}`;
  if (cid) u += `&conversation_id=${encodeURIComponent(cid)}`;
  return u;
}

function onEnvelope(env: Envelope) {
  const d = env.data || {};
  switch (env.type) {
    case "conversation":
      if (d.id) localStorage.setItem(STORE_KEY, String(d.id));
      break;
    case "history":
      msgs.innerHTML = "";
      if (!d.messages || d.messages.length === 0) showWelcome();
      else d.messages.forEach((m: any) => bubble(m.source, m.content));
      break;
    case "ai_token":
      setTyping(false);
      if (!streaming) streaming = bubble("ai", "");
      streaming.textContent = (streaming.textContent || "") + (d.delta || "");
      scrollDown();
      break;
    case "ai_done":
      streaming = null;
      break;
    case "noise_reply":
      setTyping(false);
      streaming = null;
      bubble("ai", d.content || "");
      break;
    case "handoff":
      setTyping(false);
      streaming = null;
      systemNote(d.notice || "正在为您转接人工，请稍候");
      break;
    case "agent_message":
      setTyping(false);
      bubble("agent", d.content || "");
      break;
    case "mode_changed":
      systemNote(d.mode === "human" ? "已转接人工客服" : "已切回 AI 客服");
      break;
    case "error":
      setTyping(false);
      systemNote(`出错了：${d.message || d.code || "unknown"}`);
      break;
  }
}

const sock = new WidgetSocket(wsUrl, onEnvelope);

function autosize() {
  inp.style.height = "auto";
  inp.style.height = Math.min(inp.scrollHeight, 120) + "px";
}

function submit() {
  const text = inp.value.trim();
  if (!text) return;
  bubble("user", text);
  streaming = null;
  setTyping(true);
  sock.send("user_message", { text });
  inp.value = "";
  autosize();
}

sendBtn.addEventListener("click", submit);
inp.addEventListener("input", autosize);

// 输入法（IME）组合态检测：中文选词按 Enter 不应发送
let composing = false;
inp.addEventListener("compositionstart", () => {
  composing = true;
});
inp.addEventListener("compositionend", () => {
  composing = false;
});
inp.addEventListener("keydown", (e) => {
  if (e.key !== "Enter" || e.shiftKey) return;
  if (composing || e.isComposing || (e as any).keyCode === 229) return;
  e.preventDefault();
  submit();
});

async function boot() {
  if (!CHANNEL_TOKEN) {
    try {
      const r = await fetch("/api/v1/widget/config");
      const cfg = await r.json();
      if (cfg.channel_token) CHANNEL_TOKEN = cfg.channel_token;
    } catch {
      /* ignore */
    }
  }
  if (!CHANNEL_TOKEN) {
    systemNote("未获取到客服渠道配置，请稍后重试。");
    return;
  }
  sock.connect();
}

boot();
