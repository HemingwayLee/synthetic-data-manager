// import.meta.env.BASE_URL is Vite's `base` ("/app2/"), so calls go to /app2/api/..., which nginx (or the Vite
// proxy) forwards to this app's backend. Always build URLs from it rather than starting with "/api".
const API = `${import.meta.env.BASE_URL}api`;

async function request(path, options = {}) {
  const res = await fetch(`${API}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    const detail = typeof body?.detail === "string" ? body.detail : body?.detail?.[0]?.msg;
    throw new Error(detail || `${res.status} ${res.statusText}`);
  }
  return res.status === 204 ? null : res.json();
}

export const api = {
  health: () => request("/health"),
  listItems: () => request("/items"),
  createItem: (name) => request("/items", { method: "POST", body: JSON.stringify({ name }) }),
};
