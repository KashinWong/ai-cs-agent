import { WidgetSocket, type Envelope } from "./ws-client";

const params = new URLSearchParams(location.search);
let CHANNEL_TOKEN = params.get("token") || (window as any).__CHANNEL_TOKEN__ || "";
const STORE_KEY = "ai_cs_conversation_id";

const root = document.getElementById("app")!;
root.innerHTML = `
  <div style="max-width:420px;margin:24px auto;font-family:system-ui,sans-serif;border:1px solid #e5e7eb;border-radius:12px;overflow:hidden;display:flex;flex-direction:column;height:72vh">
    <div style="padding:12px 16px;background:#111827;color:#fff;font-weight:600">AI 客服</div>
    <div id="msgs" style="flex:1;overflow-y:auto;padding:16px;background:#f9fafb"></div>
    <div style="display:flex;border-top:1px solid #e5e7eb">
      <input id="inp" placeholder="输入问题…" style="flex:1;border:0;padding:12px 16px;outline:none;font-size:14px" />
      <button id="send" style="border:0;background:#2563eb;color:#fff;padding:0 20px;cursor:pointer">发送</button>
    </div>
  </div>`;

const msgs = document.getElementById("msgs")!;
const inp = document.getElementById("inp") as HTMLInputElement;
const sendBtn = document.getElementById("send")!;

function bubble(source: string, text: string): HTMLSpanElement {
  const mine = source === "user";
  const bg = mine ? "#2563eb" : source === "agent" ? "#059669" : source === "system" ? "#e5e7eb" : "#fff";
  const fg = mine || source === "agent" ? "#fff" : "#111827";
  const wrap = document.createElement("div");
  wrap.style.cssText = `display:flex;justify-content:${mine ? "flex-end" : "flex-start"};margin-bottom:10px`;
  const b = document.createElement("div");
  b.style.cssText = `max-width:80%;padding:8px 12px;border-radius:10px;background:${bg};color:${fg};white-space:pre-wrap;word-break:break-word;box-shadow:0 1px 2px rgba(0,0,0,.06);font-size:14px`;
  if (source === "agent") {
    const tag = document.createElement("div");
    tag.textContent = "人工";
    tag.style.cssText = "font-size:11px;opacity:.85;margin-bottom:2px";
    b.appendChild(tag);
  }
  const span = document.createElement("span");
  span.textContent = text;
  b.appendChild(span);
  wrap.appendChild(b);
  msgs.appendChild(wrap);
  msgs.scrollTop = msgs.scrollHeight;
  return span;
}

let streaming: HTMLSpanElement | null = null;

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
      (d.messages || []).forEach((m: any) => bubble(m.source, m.content));
      break;
    case "ai_token":
      if (!streaming) streaming = bubble("ai", "");
      streaming.textContent = (streaming.textContent || "") + (d.delta || "");
      msgs.scrollTop = msgs.scrollHeight;
      break;
    case "ai_done":
      streaming = null;
      break;
    case "noise_reply":
      streaming = null;
      bubble("ai", d.content || "");
      break;
    case "handoff":
      streaming = null;
      bubble("system", d.notice || "正在为您转接人工，请稍候");
      break;
    case "agent_message":
      bubble("agent", d.content || "");
      break;
    case "mode_changed":
      bubble("system", d.mode === "human" ? "已转人工" : "已切回 AI");
      break;
    case "error":
      bubble("system", `错误：${d.message || d.code || "unknown"}`);
      break;
  }
}

const sock = new WidgetSocket(wsUrl, onEnvelope);

function submit() {
  const text = inp.value.trim();
  if (!text) return;
  bubble("user", text);
  streaming = null;
  sock.send("user_message", { text });
  inp.value = "";
}

sendBtn.addEventListener("click", submit);

// 输入法（IME）组合态检测：中文/日文等选词按 Enter 不应发送
let composing = false;
inp.addEventListener("compositionstart", () => {
  composing = true;
});
inp.addEventListener("compositionend", () => {
  composing = false;
});
inp.addEventListener("keydown", (e) => {
  // e.isComposing / keyCode 229 覆盖各浏览器 IME 组合态；Shift+Enter 换行不发送
  if (e.key !== "Enter" || e.shiftKey) return;
  if (composing || e.isComposing || (e as any).keyCode === 229) return;
  e.preventDefault();
  submit();
});

// 先取默认渠道 token（未在 URL 显式指定时），再连 WS
async function boot() {
  if (!CHANNEL_TOKEN) {
    try {
      const r = await fetch("/api/v1/widget/config");
      const cfg = await r.json();
      if (cfg.channel_token) CHANNEL_TOKEN = cfg.channel_token;
    } catch {
      /* ignore — wsUrl 会带空 token，后端拒连后由重连兜底 */
    }
  }
  if (!CHANNEL_TOKEN) {
    bubble("system", "未获取到客服渠道配置，请稍后重试。");
    return;
  }
  sock.connect();
}

boot();
