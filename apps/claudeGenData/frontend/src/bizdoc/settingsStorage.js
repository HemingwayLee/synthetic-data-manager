// Settings chosen on the Settings page, saved per document type in this browser.
// The sidebar's Batch Generation reads the same values.

const settingsKey = (docTypeId) => `bizdoc-settings:${docTypeId}`;
const MODEL_KEY = "bizdoc-model";

export function defaultsFor(docType) {
  return Object.fromEntries(docType.fields.map((f) => [f.id, f.default]));
}

export function loadSettings(docType) {
  const values = defaultsFor(docType);
  try {
    const saved = JSON.parse(localStorage.getItem(settingsKey(docType.id)) || "{}");
    // Ignore saved values for fields or options that no longer exist.
    for (const f of docType.fields) {
      const v = saved[f.id];
      if (v === undefined) continue;
      if (f.type === "select" && v !== "random" && !f.options.includes(v)) continue;
      if (f.type === "multiselect" && (!Array.isArray(v) || v.some((x) => !f.options.includes(x)))) continue;
      values[f.id] = v;
    }
  } catch {
    // Storage unavailable or corrupt: fall back to defaults.
  }
  return values;
}

export function saveSettings(docTypeId, values) {
  try {
    localStorage.setItem(settingsKey(docTypeId), JSON.stringify(values));
  } catch {
    // ignore
  }
}

/** The saved model id, or null to let the backend use its default. */
export function loadModel() {
  try {
    return localStorage.getItem(MODEL_KEY);
  } catch {
    return null;
  }
}

export function saveModel(model) {
  try {
    localStorage.setItem(MODEL_KEY, model);
  } catch {
    // ignore
  }
}
