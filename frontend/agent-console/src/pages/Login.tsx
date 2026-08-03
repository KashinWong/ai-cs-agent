import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { login } from "../api/client";

export default function Login() {
  const [u, setU] = useState("agent");
  const [p, setP] = useState("agent123");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const nav = useNavigate();

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setErr("");
    setBusy(true);
    try {
      await login(u, p);
      nav("/");
    } catch (ex: any) {
      setErr(ex.message === "invalid_credentials" ? "用户名或密码错误" : `登录失败：${ex.message}`);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", padding: 24 }}>
      <div className="card" style={{ width: 360, padding: 32 }}>
        <div style={{ textAlign: "center", marginBottom: 24 }}>
          <div style={{ width: 48, height: 48, margin: "0 auto 12px", borderRadius: 12, background: "linear-gradient(135deg,#4f46e5,#6366f1)", color: "#fff", display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 700, fontSize: 18 }}>
            AI
          </div>
          <h2 style={{ margin: "0 0 4px", fontSize: 19 }}>坐席工作台</h2>
          <div className="muted" style={{ fontSize: 13 }}>登录以管理会话与知识库</div>
        </div>
        <form onSubmit={submit}>
          <label style={{ fontSize: 13, color: "var(--text-2)", display: "block", marginBottom: 6 }}>用户名</label>
          <input className="field" value={u} onChange={(e) => setU(e.target.value)} placeholder="用户名" style={{ marginBottom: 14 }} />
          <label style={{ fontSize: 13, color: "var(--text-2)", display: "block", marginBottom: 6 }}>密码</label>
          <input className="field" value={p} type="password" onChange={(e) => setP(e.target.value)} placeholder="密码" style={{ marginBottom: 20 }} />
          <button type="submit" className="btn btn-primary" disabled={busy} style={{ width: "100%", padding: 10 }}>
            {busy ? "登录中…" : "登录"}
          </button>
        </form>
        {err && <p style={{ color: "var(--danger)", fontSize: 13, marginBottom: 0, marginTop: 14, textAlign: "center" }}>{err}</p>}
      </div>
    </div>
  );
}
