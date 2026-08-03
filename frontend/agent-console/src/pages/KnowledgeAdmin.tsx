import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { api, clearToken, getToken } from "../api/client";

type KBItem = {
  id: number;
  title: string;
  content: string;
  lang: string;
  vector_status: string;
  meta: Record<string, unknown>;
};

const EMPTY = { id: 0, title: "", content: "", lang: "zh", category: "" };

export default function KnowledgeAdmin() {
  const nav = useNavigate();
  const [items, setItems] = useState<KBItem[]>([]);
  const [langFilter, setLangFilter] = useState("");
  const [form, setForm] = useState({ ...EMPTY });
  const [editing, setEditing] = useState(false);
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);
  const [impFile, setImpFile] = useState<File | null>(null);
  const [impLang, setImpLang] = useState("zh");
  const [impMsg, setImpMsg] = useState("");

  useEffect(() => {
    if (!getToken()) nav("/login");
  }, [nav]);

  async function load() {
    try {
      const q = langFilter ? `?lang=${langFilter}` : "";
      setItems(await api<KBItem[]>(`/kb/items${q}`));
    } catch (e: any) {
      if (e.message === "401" || e.message === "unauthorized") {
        clearToken();
        nav("/login");
      }
    }
  }

  useEffect(() => {
    load();
  }, [langFilter]);

  function resetForm() {
    setForm({ ...EMPTY });
    setEditing(false);
  }

  function startEdit(it: KBItem) {
    setForm({
      id: it.id,
      title: it.title,
      content: it.content,
      lang: it.lang,
      category: String((it.meta && (it.meta as any).category) || ""),
    });
    setEditing(true);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  async function save(e: React.FormEvent) {
    e.preventDefault();
    if (!form.title.trim() || !form.content.trim()) return;
    setBusy(true);
    setMsg("");
    const body = {
      title: form.title,
      content: form.content,
      lang: form.lang,
      meta: form.category ? { category: form.category } : {},
    };
    try {
      if (editing) {
        await api(`/kb/items/${form.id}`, { method: "PUT", body: JSON.stringify(body) });
        setMsg("已更新并重建向量索引");
      } else {
        await api("/kb/items", { method: "POST", body: JSON.stringify(body) });
        setMsg("已新增并完成向量索引，可立即在 widget 提问命中");
      }
      resetForm();
      await load();
    } catch (ex: any) {
      setMsg(`保存失败：${ex.message}`);
    } finally {
      setBusy(false);
    }
  }

  async function importMd(e: React.FormEvent) {
    e.preventDefault();
    if (!impFile) return;
    setBusy(true);
    setImpMsg("");
    const fd = new FormData();
    fd.append("file", impFile);
    fd.append("lang", impLang);
    try {
      const res = await fetch("/api/v1/kb/import", {
        method: "POST",
        headers: { Authorization: `Bearer ${getToken()}` },
        body: fd,
      });
      if (!res.ok) throw new Error(String(res.status));
      const r = await res.json();
      setImpMsg(
        `导入 ${r.imported} 条，已索引 ${r.indexed ?? r.imported} 条` +
          (r.note ? `（${r.note}）` : ""),
      );
      setImpFile(null);
      await load();
    } catch (ex: any) {
      setImpMsg(`导入失败：${ex.message}`);
    } finally {
      setBusy(false);
    }
  }

  async function remove(it: KBItem) {
    if (!confirm(`删除知识条目「${it.title}」？`)) return;
    setBusy(true);
    try {
      await api(`/kb/items/${it.id}`, { method: "DELETE" });
      if (editing && form.id === it.id) resetForm();
      await load();
    } catch (ex: any) {
      setMsg(`删除失败：${ex.message}`);
    } finally {
      setBusy(false);
    }
  }

  const statusBadge: Record<string, string> = {
    indexed: "badge-human",
    pending: "badge-pending",
    stale: "badge-closed",
  };

  return (
    <div style={{ minHeight: "100vh" }}>
      {/* 顶栏 */}
      <header style={{ background: "var(--surface)", borderBottom: "1px solid var(--border)", padding: "14px 24px", display: "flex", alignItems: "center", gap: 12, position: "sticky", top: 0, zIndex: 10 }}>
        <a href="/console/" style={{ fontSize: 13 }}>← 工作台</a>
        <h2 style={{ margin: 0, fontSize: 17 }}>知识库管理</h2>
        <span className="muted" style={{ fontSize: 13 }}>{items.length} 条</span>
        <button className="btn-link" style={{ marginLeft: "auto" }} onClick={() => { clearToken(); nav("/login"); }}>退出</button>
      </header>

      <div style={{ maxWidth: 940, margin: "0 auto", padding: 24 }}>
        {/* 新增/编辑表单 */}
        <form onSubmit={save} className="card" style={{ padding: 20, marginBottom: 20 }}>
          <div style={{ fontWeight: 600, marginBottom: 14, fontSize: 15 }}>{editing ? `编辑条目 #${form.id}` : "新增知识条目"}</div>
          <div style={{ display: "flex", gap: 10, marginBottom: 12 }}>
            <input className="field" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })}
              placeholder="标题（如：如何重置密码）" style={{ flex: 2 }} />
            <select className="field" value={form.lang} onChange={(e) => setForm({ ...form, lang: e.target.value })} style={{ width: 110, flex: "none" }}>
              <option value="zh">中文</option>
              <option value="en">English</option>
            </select>
            <input className="field" value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })}
              placeholder="分类（可选）" style={{ flex: 1 }} />
          </div>
          <textarea className="field" value={form.content} onChange={(e) => setForm({ ...form, content: e.target.value })}
            placeholder="回答内容（AI 将严格依据此内容作答）" rows={4} />
          <div style={{ marginTop: 14, display: "flex", gap: 10, alignItems: "center" }}>
            <button type="submit" className="btn btn-primary" disabled={busy}>{editing ? "保存修改" : "新增"}</button>
            {editing && <button type="button" className="btn btn-ghost" onClick={resetForm}>取消</button>}
            {msg && <span style={{ color: msg.includes("失败") ? "var(--danger)" : "var(--ok)", fontSize: 13 }}>{msg}</span>}
          </div>
        </form>

        {/* Markdown 批量导入 */}
        <form onSubmit={importMd} className="card" style={{ padding: 20, marginBottom: 24, borderStyle: "dashed" }}>
          <div style={{ fontWeight: 600, marginBottom: 6, fontSize: 15 }}>📄 从 Markdown 导入</div>
          <div className="muted" style={{ fontSize: 12.5, marginBottom: 14, lineHeight: 1.6 }}>
            按标题（# / ##）切分，每个标题为一条 FAQ，标题下正文为回答内容。导入后自动向量索引，即刻可被检索命中。
          </div>
          <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
            <input type="file" accept=".md,.markdown,.txt,text/markdown" style={{ fontSize: 13 }}
              onChange={(e) => setImpFile(e.target.files?.[0] || null)} />
            <select className="field" value={impLang} onChange={(e) => setImpLang(e.target.value)} style={{ width: 110 }}>
              <option value="zh">中文</option>
              <option value="en">English</option>
            </select>
            <button type="submit" className="btn btn-accent" disabled={busy || !impFile}>导入</button>
            {impMsg && <span style={{ color: impMsg.includes("失败") ? "var(--danger)" : "var(--agent)", fontSize: 13 }}>{impMsg}</span>}
          </div>
        </form>

        {/* 过滤 + 列表 */}
        <div style={{ display: "flex", alignItems: "center", marginBottom: 12, gap: 12 }}>
          <b style={{ fontSize: 15 }}>知识条目</b>
          <select className="field" value={langFilter} onChange={(e) => setLangFilter(e.target.value)} style={{ width: 130 }}>
            <option value="">全部语言</option>
            <option value="zh">中文</option>
            <option value="en">English</option>
          </select>
        </div>
        <div className="card" style={{ overflow: "hidden" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
            <thead>
              <tr style={{ textAlign: "left", background: "var(--surface-2)", color: "var(--text-2)", fontSize: 12.5 }}>
                <th style={{ padding: "10px 14px", width: 50 }}>#</th>
                <th style={{ padding: "10px 8px", width: 56 }}>语言</th>
                <th style={{ padding: "10px 8px" }}>标题</th>
                <th style={{ padding: "10px 8px", width: 96 }}>索引</th>
                <th style={{ padding: "10px 14px", width: 120, textAlign: "right" }}>操作</th>
              </tr>
            </thead>
            <tbody>
              {items.length === 0 && (
                <tr><td colSpan={5} className="muted" style={{ padding: 32, textAlign: "center" }}>暂无条目，可新增或从 Markdown 导入</td></tr>
              )}
              {items.map((it) => (
                <tr key={it.id} style={{ borderTop: "1px solid var(--surface-2)" }}>
                  <td style={{ padding: "11px 14px", color: "var(--text-3)" }}>{it.id}</td>
                  <td style={{ padding: "11px 8px" }}>{it.lang}</td>
                  <td style={{ padding: "11px 8px" }}>{it.title}</td>
                  <td style={{ padding: "11px 8px" }}><span className={`badge ${statusBadge[it.vector_status] || "badge-closed"}`}>{it.vector_status}</span></td>
                  <td style={{ padding: "11px 14px", textAlign: "right" }}>
                    <button className="btn-link" onClick={() => startEdit(it)}>编辑</button>
                    <button className="btn-link danger" onClick={() => remove(it)}>删除</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
