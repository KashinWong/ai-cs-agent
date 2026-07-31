import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import { api, clearToken, getToken } from "../api/client";

type Conv = { id: number; status: string; lang: string; assigned_agent_id: number | null; last_activity_at: string | null };
type Msg = { id: number; source: string; content: string; created_at: string | null };

const STATUS_LABEL: Record<string, string> = {
  ai: "AI 应答中", pending_human: "待接管", human: "人工中", closed: "已结束",
};

export default function Inbox() {
  const nav = useNavigate();
  const [convs, setConvs] = useState<Conv[]>([]);
  const [sel, setSel] = useState<number | null>(null);
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [text, setText] = useState("");
  const selRef = useRef<number | null>(null);
  selRef.current = sel;

  useEffect(() => {
    if (!getToken()) nav("/login");
  }, [nav]);

  async function loadConvs() {
    try {
      setConvs(await api<Conv[]>("/conversations"));
    } catch (e: any) {
      if (e.message === "401" || e.message === "unauthorized") {
        clearToken();
        nav("/login");
      }
    }
  }

  async function loadMsgs(id: number) {
    setMsgs(await api<Msg[]>(`/conversations/${id}/messages`));
  }

  useEffect(() => {
    loadConvs();
    const t = setInterval(() => {
      loadConvs();
      if (selRef.current) loadMsgs(selRef.current).catch(() => {});
    }, 2500);
    return () => clearInterval(t);
  }, []);

  async function open(id: number) {
    setSel(id);
    await loadMsgs(id);
  }

  async function act(path: string, body?: any) {
    if (!sel) return;
    await api(`/conversations/${sel}/${path}`, {
      method: "POST",
      body: body ? JSON.stringify(body) : undefined,
    });
    await loadConvs();
    await loadMsgs(sel);
  }

  const cur = convs.find((c) => c.id === sel);
  const pending = convs.filter((c) => c.status === "pending_human").length;

  return (
    <div style={{ display: "flex", height: "100vh", fontFamily: "system-ui" }}>
      <div style={{ width: 300, borderRight: "1px solid #e5e7eb", overflowY: "auto" }}>
        <div style={{ padding: 12, fontWeight: 600, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <span>会话{pending > 0 && <span style={{ color: "#dc2626" }}>（待接管 {pending}）</span>}</span>
          <span style={{ display: "flex", gap: 10 }}>
            <a href="/console/knowledge" style={{ color: "#2563eb", textDecoration: "none", fontWeight: 400, fontSize: 13 }}>知识库</a>
            <button onClick={() => { clearToken(); nav("/login"); }} style={{ border: 0, background: "none", color: "#6b7280", cursor: "pointer" }}>退出</button>
          </span>
        </div>
        {convs.map((c) => (
          <div key={c.id} onClick={() => open(c.id)}
            style={{ padding: "10px 12px", cursor: "pointer", background: c.id === sel ? "#eff6ff" : "#fff", borderBottom: "1px solid #f3f4f6" }}>
            <div>#{c.id} · {STATUS_LABEL[c.status] || c.status}</div>
            <div style={{ fontSize: 12, color: "#9ca3af" }}>{c.last_activity_at?.slice(11, 19)}</div>
          </div>
        ))}
      </div>
      <div style={{ flex: 1, display: "flex", flexDirection: "column" }}>
        {!cur ? (
          <div style={{ margin: "auto", color: "#9ca3af" }}>选择一个会话</div>
        ) : (
          <>
            <div style={{ padding: 12, borderBottom: "1px solid #e5e7eb", display: "flex", gap: 8 }}>
              <b>#{cur.id} · {STATUS_LABEL[cur.status]}</b>
              <div style={{ marginLeft: "auto", display: "flex", gap: 8 }}>
                {(cur.status === "pending_human" || cur.status === "ai") && (
                  <button onClick={() => act("claim")}>接管</button>
                )}
                {cur.status === "human" && (
                  <button onClick={() => act("mode", { mode: "ai" })}>切回 AI</button>
                )}
                {cur.status !== "closed" && <button onClick={() => act("close")}>结束</button>}
              </div>
            </div>
            <div style={{ flex: 1, overflowY: "auto", padding: 16, background: "#f9fafb" }}>
              {msgs.map((m) => (
                <div key={m.id} style={{ display: "flex", justifyContent: m.source === "user" ? "flex-start" : "flex-end", marginBottom: 8 }}>
                  <div style={{ maxWidth: "70%", padding: "8px 12px", borderRadius: 8, whiteSpace: "pre-wrap",
                    background: m.source === "user" ? "#fff" : m.source === "agent" ? "#059669" : m.source === "system" ? "#e5e7eb" : "#2563eb",
                    color: m.source === "user" || m.source === "system" ? "#111827" : "#fff" }}>
                    <div style={{ fontSize: 11, opacity: 0.7 }}>{m.source}</div>
                    {m.content}
                  </div>
                </div>
              ))}
            </div>
            <div style={{ display: "flex", borderTop: "1px solid #e5e7eb" }}>
              <input value={text} onChange={(e) => setText(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter" && text.trim()) { act("reply", { content: text }); setText(""); } }}
                placeholder={cur.status === "human" ? "输入回复…" : "需先接管才能回复"}
                disabled={cur.status !== "human"}
                style={{ flex: 1, border: 0, padding: 12, outline: "none" }} />
              <button disabled={cur.status !== "human" || !text.trim()}
                onClick={() => { act("reply", { content: text }); setText(""); }}
                style={{ border: 0, background: "#2563eb", color: "#fff", padding: "0 20px" }}>发送</button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
