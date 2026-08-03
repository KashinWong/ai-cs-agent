import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import { api, clearToken, getToken } from "../api/client";

type Conv = { id: number; status: string; lang: string; assigned_agent_id: number | null; last_activity_at: string | null };
type Msg = { id: number; source: string; content: string; created_at: string | null };

const STATUS: Record<string, { label: string; cls: string }> = {
  ai: { label: "AI 应答中", cls: "badge-ai" },
  pending_human: { label: "待接管", cls: "badge-pending" },
  human: { label: "人工中", cls: "badge-human" },
  closed: { label: "已结束", cls: "badge-closed" },
};

const SRC: Record<string, { label: string; bg: string; fg: string; align: string; border: string }> = {
  user: { label: "用户", bg: "var(--surface)", fg: "var(--text)", align: "flex-start", border: "1px solid var(--border)" },
  ai: { label: "AI", bg: "var(--brand)", fg: "#fff", align: "flex-end", border: "0" },
  agent: { label: "坐席", bg: "var(--agent-soft)", fg: "#0f4f4e", align: "flex-end", border: "1px solid #b8f0eb" },
  system: { label: "系统", bg: "var(--surface-2)", fg: "var(--text-2)", align: "center", border: "0" },
};

export default function Inbox() {
  const nav = useNavigate();
  const [convs, setConvs] = useState<Conv[]>([]);
  const [sel, setSel] = useState<number | null>(null);
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [text, setText] = useState("");
  const selRef = useRef<number | null>(null);
  const bodyRef = useRef<HTMLDivElement>(null);
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

  useEffect(() => {
    if (bodyRef.current) bodyRef.current.scrollTop = bodyRef.current.scrollHeight;
  }, [msgs]);

  async function open(id: number) {
    setSel(id);
    await loadMsgs(id);
  }
  async function act(path: string, body?: any) {
    if (!sel) return;
    await api(`/conversations/${sel}/${path}`, { method: "POST", body: body ? JSON.stringify(body) : undefined });
    await loadConvs();
    await loadMsgs(sel);
  }

  const cur = convs.find((c) => c.id === sel);
  const pending = convs.filter((c) => c.status === "pending_human").length;

  return (
    <div style={{ display: "flex", height: "100vh" }}>
      {/* 侧栏 */}
      <aside style={{ width: 300, borderRight: "1px solid var(--border)", display: "flex", flexDirection: "column", background: "var(--surface)" }}>
        <div style={{ padding: "16px 16px 12px", borderBottom: "1px solid var(--border)", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div>
            <div style={{ fontWeight: 600, fontSize: 15 }}>会话</div>
            {pending > 0 && <div style={{ fontSize: 12, color: "var(--warn)", marginTop: 2 }}>{pending} 个待接管</div>}
          </div>
          <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
            <a href="/console/knowledge" style={{ fontSize: 13 }}>知识库</a>
            <button className="btn-link" onClick={() => { clearToken(); nav("/login"); }}>退出</button>
          </div>
        </div>
        <div style={{ flex: 1, overflowY: "auto" }}>
          {convs.length === 0 && <div className="muted" style={{ padding: 24, textAlign: "center", fontSize: 13 }}>暂无会话</div>}
          {convs.map((c) => {
            const s = STATUS[c.status] || STATUS.ai;
            return (
              <div key={c.id} onClick={() => open(c.id)}
                style={{ padding: "12px 16px", cursor: "pointer", borderLeft: c.id === sel ? "3px solid var(--brand)" : "3px solid transparent", background: c.id === sel ? "var(--brand-soft)" : "transparent", borderBottom: "1px solid var(--surface-2)" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
                  <span style={{ fontWeight: 600, fontSize: 13.5 }}>会话 #{c.id}</span>
                  <span className={`badge ${s.cls}`}>{s.label}</span>
                </div>
                <div className="muted" style={{ fontSize: 12 }}>{c.last_activity_at?.slice(5, 19).replace("T", " ")}</div>
              </div>
            );
          })}
        </div>
      </aside>

      {/* 主区 */}
      <main style={{ flex: 1, display: "flex", flexDirection: "column", background: "var(--bg)" }}>
        {!cur ? (
          <div className="muted" style={{ margin: "auto", textAlign: "center" }}>
            <div style={{ fontSize: 40, marginBottom: 8 }}>💬</div>
            选择左侧会话查看对话
          </div>
        ) : (
          <>
            <header style={{ padding: "14px 20px", borderBottom: "1px solid var(--border)", background: "var(--surface)", display: "flex", alignItems: "center", gap: 12 }}>
              <b style={{ fontSize: 15 }}>会话 #{cur.id}</b>
              <span className={`badge ${(STATUS[cur.status] || STATUS.ai).cls}`}>{(STATUS[cur.status] || STATUS.ai).label}</span>
              <div style={{ marginLeft: "auto", display: "flex", gap: 8 }}>
                {(cur.status === "pending_human" || cur.status === "ai") && <button className="btn btn-primary btn-sm" onClick={() => act("claim")}>接管</button>}
                {cur.status === "human" && <button className="btn btn-ghost btn-sm" onClick={() => act("mode", { mode: "ai" })}>切回 AI</button>}
                {cur.status !== "closed" && <button className="btn btn-ghost btn-sm" onClick={() => act("close")}>结束</button>}
              </div>
            </header>
            <div ref={bodyRef} style={{ flex: 1, overflowY: "auto", padding: 20, display: "flex", flexDirection: "column", gap: 12 }}>
              {msgs.map((m) => {
                const s = SRC[m.source] || SRC.system;
                return (
                  <div key={m.id} style={{ display: "flex", justifyContent: s.align }}>
                    <div style={{ maxWidth: "72%" }}>
                      <div className="muted" style={{ fontSize: 11, margin: s.align === "flex-end" ? "0 4px 3px auto" : "0 0 3px 4px", textAlign: s.align === "flex-end" ? "right" : "left" }}>{s.label}</div>
                      <div style={{ padding: "9px 13px", borderRadius: 12, background: s.bg, color: s.fg, border: s.border, whiteSpace: "pre-wrap", fontSize: 14, lineHeight: 1.55, boxShadow: "var(--shadow-sm)" }}>
                        {m.content}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
            <div style={{ display: "flex", gap: 8, padding: 12, borderTop: "1px solid var(--border)", background: "var(--surface)" }}>
              <input className="field" value={text} onChange={(e) => setText(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter" && text.trim()) { act("reply", { content: text }); setText(""); } }}
                placeholder={cur.status === "human" ? "输入回复，Enter 发送…" : "需先「接管」才能回复"}
                disabled={cur.status !== "human"} />
              <button className="btn btn-primary" disabled={cur.status !== "human" || !text.trim()}
                onClick={() => { act("reply", { content: text }); setText(""); }}>发送</button>
            </div>
          </>
        )}
      </main>
    </div>
  );
}
