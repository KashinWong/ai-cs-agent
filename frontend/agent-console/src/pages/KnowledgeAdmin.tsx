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

  const statusColor: Record<string, string> = {
    indexed: "#059669",
    pending: "#d97706",
    stale: "#dc2626",
  };

  return (
    <div style={{ maxWidth: 900, margin: "0 auto", padding: 24, fontFamily: "system-ui" }}>
      <div style={{ display: "flex", alignItems: "center", marginBottom: 16 }}>
        <h2 style={{ margin: 0 }}>知识库管理</h2>
        <div style={{ marginLeft: "auto", display: "flex", gap: 12 }}>
          <a href="/console/" style={{ color: "#2563eb", textDecoration: "none" }}>← 返回工作台</a>
          <button onClick={() => { clearToken(); nav("/login"); }}
            style={{ border: 0, background: "none", color: "#6b7280", cursor: "pointer" }}>退出</button>
        </div>
      </div>

      {/* 新增/编辑表单 */}
      <form onSubmit={save} style={{ border: "1px solid #e5e7eb", borderRadius: 10, padding: 16, marginBottom: 20, background: "#fafafa" }}>
        <div style={{ fontWeight: 600, marginBottom: 10 }}>{editing ? `编辑 #${form.id}` : "新增知识条目"}</div>
        <div style={{ display: "flex", gap: 10, marginBottom: 10 }}>
          <input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })}
            placeholder="标题（如：如何重置密码）"
            style={{ flex: 2, padding: 9, border: "1px solid #d1d5db", borderRadius: 6 }} />
          <select value={form.lang} onChange={(e) => setForm({ ...form, lang: e.target.value })}
            style={{ padding: 9, border: "1px solid #d1d5db", borderRadius: 6 }}>
            <option value="zh">中文</option>
            <option value="en">English</option>
          </select>
          <input value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })}
            placeholder="分类(可选)"
            style={{ flex: 1, padding: 9, border: "1px solid #d1d5db", borderRadius: 6 }} />
        </div>
        <textarea value={form.content} onChange={(e) => setForm({ ...form, content: e.target.value })}
          placeholder="回答内容（AI 将严格依据此内容作答）" rows={4}
          style={{ width: "100%", padding: 9, border: "1px solid #d1d5db", borderRadius: 6, boxSizing: "border-box", resize: "vertical" }} />
        <div style={{ marginTop: 10, display: "flex", gap: 10, alignItems: "center" }}>
          <button type="submit" disabled={busy}
            style={{ padding: "9px 18px", background: "#2563eb", color: "#fff", border: 0, borderRadius: 6, cursor: "pointer" }}>
            {editing ? "保存修改" : "新增"}
          </button>
          {editing && (
            <button type="button" onClick={resetForm}
              style={{ padding: "9px 18px", background: "#fff", border: "1px solid #d1d5db", borderRadius: 6, cursor: "pointer" }}>取消</button>
          )}
          {msg && <span style={{ color: msg.includes("失败") ? "#dc2626" : "#059669", fontSize: 13 }}>{msg}</span>}
        </div>
      </form>

      {/* Markdown 批量导入 */}
      <form onSubmit={importMd} style={{ border: "1px dashed #cbd5e1", borderRadius: 10, padding: 16, marginBottom: 20 }}>
        <div style={{ fontWeight: 600, marginBottom: 8 }}>从 Markdown 文件导入</div>
        <div style={{ fontSize: 12, color: "#6b7280", marginBottom: 10 }}>
          按标题（# / ##）切分，每个标题为一条 FAQ，标题下正文为回答内容。导入后自动向量索引。
        </div>
        <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
          <input type="file" accept=".md,.markdown,.txt,text/markdown"
            onChange={(e) => setImpFile(e.target.files?.[0] || null)} />
          <select value={impLang} onChange={(e) => setImpLang(e.target.value)}
            style={{ padding: 8, border: "1px solid #d1d5db", borderRadius: 6 }}>
            <option value="zh">中文</option>
            <option value="en">English</option>
          </select>
          <button type="submit" disabled={busy || !impFile}
            style={{ padding: "8px 16px", background: "#0f766e", color: "#fff", border: 0, borderRadius: 6, cursor: impFile ? "pointer" : "not-allowed" }}>
            导入
          </button>
          {impMsg && <span style={{ color: impMsg.includes("失败") ? "#dc2626" : "#0f766e", fontSize: 13 }}>{impMsg}</span>}
        </div>
      </form>

      {/* 过滤 + 列表 */}
      <div style={{ display: "flex", alignItems: "center", marginBottom: 10 }}>
        <b>知识条目（{items.length}）</b>
        <select value={langFilter} onChange={(e) => setLangFilter(e.target.value)}
          style={{ marginLeft: 12, padding: 6, border: "1px solid #d1d5db", borderRadius: 6 }}>
          <option value="">全部语言</option>
          <option value="zh">中文</option>
          <option value="en">English</option>
        </select>
      </div>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
        <thead>
          <tr style={{ textAlign: "left", borderBottom: "2px solid #e5e7eb", color: "#6b7280" }}>
            <th style={{ padding: "8px 6px", width: 40 }}>#</th>
            <th style={{ padding: "8px 6px", width: 48 }}>语言</th>
            <th style={{ padding: "8px 6px" }}>标题</th>
            <th style={{ padding: "8px 6px", width: 80 }}>索引</th>
            <th style={{ padding: "8px 6px", width: 110 }}>操作</th>
          </tr>
        </thead>
        <tbody>
          {items.map((it) => (
            <tr key={it.id} style={{ borderBottom: "1px solid #f3f4f6" }}>
              <td style={{ padding: "8px 6px", color: "#9ca3af" }}>{it.id}</td>
              <td style={{ padding: "8px 6px" }}>{it.lang}</td>
              <td style={{ padding: "8px 6px" }}>{it.title}</td>
              <td style={{ padding: "8px 6px", color: statusColor[it.vector_status] || "#6b7280" }}>{it.vector_status}</td>
              <td style={{ padding: "8px 6px" }}>
                <button onClick={() => startEdit(it)} style={{ marginRight: 8, border: 0, background: "none", color: "#2563eb", cursor: "pointer" }}>编辑</button>
                <button onClick={() => remove(it)} style={{ border: 0, background: "none", color: "#dc2626", cursor: "pointer" }}>删除</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
