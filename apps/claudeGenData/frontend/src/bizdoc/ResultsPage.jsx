import { useCallback, useEffect, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  IconButton,
  List,
  ListItemButton,
  ListItemText,
  Stack,
  Tab,
  Tabs,
  Tooltip,
  Typography,
} from "@mui/material";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import DoNotDisturbOnOutlinedIcon from "@mui/icons-material/DoNotDisturbOnOutlined";
import DownloadIcon from "@mui/icons-material/Download";
import ErrorOutlineIcon from "@mui/icons-material/ErrorOutline";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import TableChartOutlinedIcon from "@mui/icons-material/TableChartOutlined";
import { Link } from "react-router";
import { api, documentPdfUrl } from "../api";
import { DOCUMENTS_CHANGED } from "./BizDocSidebar";

const POLL_MS = 3000;
const isActive = (doc) => doc.status === "queued" || doc.status === "running";

function elapsed(from, now) {
  const s = Math.max(0, Math.round((now - new Date(from)) / 1000));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}

function StatusIcon({ doc }) {
  if (isActive(doc)) return <CircularProgress size={16} />;
  if (doc.status === "failed") return <ErrorOutlineIcon fontSize="small" color="error" />;
  if (doc.status === "cancelled") return <DoNotDisturbOnOutlinedIcon fontSize="small" color="disabled" />;
  return null;
}

const preSx = {
  m: 0,
  p: 2,
  fontSize: 12,
  fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace",
  whiteSpace: "pre-wrap",
  wordBreak: "break-word",
  bgcolor: "action.hover",
  borderRadius: 1,
};

function DocumentDetail({ doc, now, onDelete }) {
  const [tab, setTab] = useState("document");

  if (isActive(doc)) {
    return (
      <Stack sx={{ flex: 1, alignItems: "center", justifyContent: "center", gap: 2, p: 4 }}>
        <CircularProgress />
        <Typography color="text.secondary">
          {doc.status === "queued"
            ? "Waiting for another generation to finish…"
            : `Claude Code is writing the document… ${elapsed(doc.started_at, now)}`}
        </Typography>
      </Stack>
    );
  }

  if (doc.status === "failed" || doc.status === "cancelled") {
    return (
      <Box sx={{ p: 2 }}>
        <Alert
          severity={doc.status === "failed" ? "error" : "info"}
          action={
            <Button color="inherit" size="small" onClick={() => onDelete(doc)}>
              Delete
            </Button>
          }
        >
          {doc.status === "cancelled" ? "Cancelled before generation started." : doc.error || "Generation failed."}
        </Alert>
      </Box>
    );
  }

  return (
    <Stack sx={{ flex: 1, minHeight: 0 }}>
      <Stack direction="row" sx={{ alignItems: "center", px: 2, pt: 1, gap: 1 }}>
        <Typography variant="subtitle1" noWrap sx={{ flex: 1, fontWeight: 600 }}>
          {doc.title}
        </Typography>
        <Tooltip title="Open PDF in new tab">
          <IconButton component="a" href={documentPdfUrl(doc.id)} target="_blank" rel="noopener">
            <OpenInNewIcon />
          </IconButton>
        </Tooltip>
        <Tooltip title="Download PDF">
          <IconButton component="a" href={documentPdfUrl(doc.id, { download: true })}>
            <DownloadIcon />
          </IconButton>
        </Tooltip>
        <Tooltip title="Delete">
          <IconButton onClick={() => onDelete(doc)}>
            <DeleteOutlineIcon />
          </IconButton>
        </Tooltip>
      </Stack>
      <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ px: 2, minHeight: 40, "& .MuiTab-root": { minHeight: 40 } }}>
        <Tab value="document" label="Document" />
        <Tab value="labels" label="Labels" />
        <Tab value="settings" label="Settings used" />
      </Tabs>
      <Box sx={{ flex: 1, minHeight: { xs: "70vh", lg: 0 }, overflow: "auto", p: 2, pt: 1 }}>
        {tab === "document" && (
          <Box
            component="iframe"
            title={doc.title}
            src={documentPdfUrl(doc.id)}
            sx={{ width: "100%", height: "100%", minHeight: 480, border: 1, borderColor: "divider", borderRadius: 1 }}
          />
        )}
        {tab === "labels" && (
          <Box component="pre" sx={preSx}>
            {JSON.stringify(doc.labels, null, 2)}
          </Box>
        )}
        {tab === "settings" && (
          <Box component="pre" sx={preSx}>
            {JSON.stringify({ model: doc.model, ...doc.settings }, null, 2)}
          </Box>
        )}
      </Box>
    </Stack>
  );
}

export default function ResultsPage({ docType }) {
  const [docs, setDocs] = useState(null);
  const [selectedId, setSelectedId] = useState(null);
  const [error, setError] = useState(null);
  const [now, setNow] = useState(() => Date.now());

  const load = useCallback(async () => {
    try {
      const list = await api.listDocuments(docType.id);
      setDocs(list);
      setError(null);
      setSelectedId((id) => (list.some((d) => d.id === id) ? id : list[0]?.id ?? null));
    } catch (e) {
      setError(e.message);
    }
  }, [docType.id]);

  useEffect(() => {
    load();
    window.addEventListener(DOCUMENTS_CHANGED, load);
    return () => window.removeEventListener(DOCUMENTS_CHANGED, load);
  }, [load]);

  // Poll while anything is generating, and tick the elapsed-time display.
  const anyActive = docs?.some(isActive);
  useEffect(() => {
    if (!anyActive) return;
    const poll = setInterval(load, POLL_MS);
    const tick = setInterval(() => setNow(Date.now()), 1000);
    return () => {
      clearInterval(poll);
      clearInterval(tick);
    };
  }, [anyActive, load]);

  const cancelQueued = async () => {
    try {
      await api.cancelQueued(docType.id);
      load();
    } catch (e) {
      setError(e.message);
    }
  };

  const remove = async (doc) => {
    if (!window.confirm(`Delete "${doc.title || `document #${doc.id}`}"? This removes the PDF from disk.`)) return;
    try {
      await api.deleteDocument(doc.id);
      load();
    } catch (e) {
      setError(e.message);
    }
  };

  if (docs === null) {
    return (
      <Box sx={{ flex: 1, display: "grid", placeItems: "center" }}>
        {error ? <Alert severity="error">{error}</Alert> : <CircularProgress />}
      </Box>
    );
  }

  if (docs.length === 0) {
    return (
      <Stack sx={{ flex: 1, alignItems: "center", justifyContent: "center", gap: 1, p: 4, textAlign: "center" }}>
        <TableChartOutlinedIcon sx={{ fontSize: 48, color: "text.disabled" }} />
        <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
          No {docType.label.toLowerCase()} generated yet
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Choose the variations you want and click Generate.
        </Typography>
        <Button component={Link} to={`/bizdoc/${docType.id}/settings`} variant="outlined" sx={{ mt: 1 }}>
          Go to Settings
        </Button>
      </Stack>
    );
  }

  const selected = docs.find((d) => d.id === selectedId);
  const queuedCount = docs.filter((d) => d.status === "queued").length;

  return (
    <Stack direction={{ xs: "column", lg: "row" }} sx={{ flex: 1, minHeight: 0, overflow: { xs: "auto", lg: "hidden" } }}>
      <Box
        sx={{
          width: { lg: 340 },
          flexShrink: 0,
          overflowY: { lg: "auto" },
          maxHeight: { xs: 280, lg: "none" },
          // Width-only responsive borders; a responsive `borderRight: 1` would reset the color to black.
          borderStyle: "solid",
          borderColor: "divider",
          borderWidth: { xs: "0 0 1px 0", lg: "0 1px 0 0" },
        }}
      >
        <Stack direction="row" sx={{ px: 2, pt: 1.5, gap: 1, flexWrap: "wrap", alignItems: "center" }}>
          <Chip size="small" label={`${docs.filter((d) => d.status === "done").length} done`} />
          {anyActive && <Chip size="small" color="primary" label={`${docs.filter(isActive).length} in progress`} />}
          {queuedCount > 0 && (
            <Button size="small" color="inherit" onClick={cancelQueued}>
              Cancel {queuedCount} queued
            </Button>
          )}
        </Stack>
        {error && (
          <Alert severity="error" sx={{ m: 1 }}>
            {error}
          </Alert>
        )}
        <List dense sx={{ p: 1 }}>
          {docs.map((doc) => (
            <ListItemButton
              key={doc.id}
              selected={doc.id === selectedId}
              onClick={() => setSelectedId(doc.id)}
              sx={{ borderRadius: 1, gap: 1 }}
            >
              <ListItemText
                primary={
                  doc.title ||
                  ({ queued: "Queued", running: "Generating…", failed: "Generation failed", cancelled: "Cancelled" }[doc.status] ??
                    `#${doc.id}`)
                }
                secondary={`#${doc.id} · ${new Date(doc.created_at).toLocaleString()}`}
                slotProps={{ primary: { noWrap: true } }}
              />
              <StatusIcon doc={doc} />
            </ListItemButton>
          ))}
        </List>
      </Box>

      <Stack sx={{ flex: 1, minWidth: 0, minHeight: 0 }}>
        {selected ? (
          <DocumentDetail key={selected.id} doc={selected} now={now} onDelete={remove} />
        ) : (
          <Typography color="text.secondary" sx={{ p: 4 }}>
            Select a document.
          </Typography>
        )}
      </Stack>
    </Stack>
  );
}
