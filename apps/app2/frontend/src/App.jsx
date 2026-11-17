import { useEffect, useState } from "react";
import { api } from "./api";

const ACCENT = "#3c7dc1";

export default function App() {
  const [health, setHealth] = useState(null);
  const [items, setItems] = useState([]);
  const [name, setName] = useState("");
  const [error, setError] = useState(null);

  useEffect(() => {
    Promise.all([api.health(), api.listItems()])
      .then(([h, list]) => {
        setHealth(h);
        setItems(list);
      })
      .catch((e) => setError(e.message));
  }, []);

  async function add(e) {
    e.preventDefault();
    if (!name.trim()) return;
    try {
      const item = await api.createItem(name.trim());
      setItems((prev) => [item, ...prev]);
      setName("");
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <main style={{ fontFamily: "system-ui, sans-serif", maxWidth: 560, margin: "48px auto", padding: "0 16px" }}>
      <h1 style={{ color: ACCENT, marginBottom: 4 }}>App 2</h1>
      <p style={{ color: "#666", marginTop: 0 }}>
        {health ? `backend: ${health.app} · database: ${health.database}` : "connecting…"}
        {" · "}
        <a href={`${import.meta.env.BASE_URL}api/docs`}>API docs</a>
      </p>
      {error && <p style={{ color: "crimson" }}>{error}</p>}
      <form onSubmit={add} style={{ display: "flex", gap: 8 }}>
        <input value={name} onChange={(e) => setName(e.target.value)} placeholder="New item" style={{ flex: 1, padding: 8 }} />
        <button style={{ background: ACCENT, color: "white", border: 0, padding: "8px 16px", borderRadius: 6 }}>Add</button>
      </form>
      <ul>
        {items.map((item) => (
          <li key={item.id}>
            {item.name} <small style={{ color: "#999" }}>{new Date(item.created_at).toLocaleString()}</small>
          </li>
        ))}
      </ul>
    </main>
  );
}
