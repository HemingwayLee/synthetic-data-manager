import { useEffect, useState } from "react";
import { api } from "../api";

// Document types and their setting fields come from the backend; fetch once and share.
let cache = null;
let pending = null;

export default function useDocTypes() {
  const [data, setData] = useState(cache);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (cache) return;
    pending ??= api.bizdocTypes().then((d) => (cache = d));
    pending.then(setData).catch((e) => {
      pending = null;
      setError(e.message);
    });
  }, []);

  const docTypes = data?.doc_types ?? [];
  return {
    docTypes,
    sections: data?.sections ?? [],
    random: data?.random ?? "random",
    loading: !data && !error,
    error,
    findDocType: (id) => docTypes.find((d) => d.id === id),
  };
}
