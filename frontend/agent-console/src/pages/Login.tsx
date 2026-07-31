import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { login } from "../api/client";

export default function Login() {
  const [u, setU] = useState("agent");
  const [p, setP] = useState("agent123");
  const [err, setErr] = useState("");
  const nav = useNavigate();

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setErr("");
    try {
      await login(u, p);
      nav("/");
    } catch (ex: any) {
      setErr(ex.message === "invalid_credentials" ? "用户名或密码错误" : `登录失败：${ex.message}`);
    }
  }

  return (
    <div style={{ maxWidth: 320, margin: "80px auto", fontFamily: "system-ui" }}>
      <h2>坐席登录</h2>
      <form onSubmit={submit}>
        <input value={u} onChange={(e) => setU(e.target.value)} placeholder="用户名"
          style={{ width: "100%", padding: 10, marginBottom: 10, boxSizing: "border-box" }} />
        <input value={p} type="password" onChange={(e) => setP(e.target.value)} placeholder="密码"
          style={{ width: "100%", padding: 10, marginBottom: 10, boxSizing: "border-box" }} />
        <button type="submit" style={{ width: "100%", padding: 10, background: "#2563eb", color: "#fff", border: 0, borderRadius: 6 }}>
          登录
        </button>
      </form>
      {err && <p style={{ color: "#dc2626" }}>{err}</p>}
    </div>
  );
}
