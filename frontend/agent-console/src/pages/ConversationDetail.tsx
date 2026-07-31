import { api } from "../api/client";

type Msg = { id: number; source: string; content: string; created_at: string | null };

const SOURCE_STYLE: Record<string, { bg: string; fg: string; label: string; align: string }> = {
  user: { bg: "#2563eb", fg: "#fff", label: "用户", align: "flex-start" },
  ai: { bg: "#fff", fg: "#111827", label: "AI", align: "flex-end" },
  agent: { bg: "#059669", fg: "#fff", label: "坐席", align: "flex-end" },
  system: { bg: "#e5e7eb", fg: "#374151", label: "系统", align: "center" },
};

/** 会话详情：完整时间序历史 + 操作区（接管/切换/结束）（T070）。 */
export default function ConversationDetail(props: {
  status: string;
  messages: Msg[];
  onAct: (path: string, body?: any) => void;
}) {
  const { status, messages, onAct } = props;
  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <div style={{ padding: "8px 12px", borderBottom: "1px solid #e5e7eb", display: "flex", gap: 8 }}>
        {(status === "pending_human" || status === "ai") && (
          <button onClick={() => onAct("claim")}>接管</button>
        )}
        {status === "human" && (
          <button onClick={() => onAct("mode", { mode: "ai" })}>切回 AI</button>
        )}
        {status !== "closed" && <button onClick={() => onAct("close")}>结束</button>}
      </div>
      <div style={{ flex: 1, overflowY: "auto", padding: 16, background: "#f9fafb" }}>
        {messages.map((m) => {
          const s = SOURCE_STYLE[m.source] || SOURCE_STYLE.system;
          return (
            <div key={m.id} style={{ display: "flex", justifyContent: s.align, marginBottom: 10 }}>
              <div style={{ maxWidth: "78%", padding: "8px 12px", borderRadius: 10, background: s.bg, color: s.fg, whiteSpace: "pre-wrap", boxShadow: "0 1px 2px rgba(0,0,0,.06)" }}>
                <div style={{ fontSize: 11, opacity: 0.8, marginBottom: 2 }}>{s.label}</div>
                {m.content}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
