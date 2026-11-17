import { useEffect, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Divider,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  MenuItem,
  TextField,
  Typography,
} from "@mui/material";
import DynamicFeedIcon from "@mui/icons-material/DynamicFeed";
import TableChartOutlinedIcon from "@mui/icons-material/TableChartOutlined";
import TuneIcon from "@mui/icons-material/Tune";
import { Link, useNavigate } from "react-router";
import { api } from "../api";
import { loadModel, loadSettings } from "./settingsStorage";

const ITEMS = [
  { view: "settings", label: "Settings", icon: <TuneIcon /> },
  { view: "results", label: "Results", icon: <TableChartOutlinedIcon /> },
];

/** Tell an open Results page to refresh right away instead of waiting for its next poll. */
export const DOCUMENTS_CHANGED = "bizdoc:documents-changed";

function BatchGeneration({ docType }) {
  const navigate = useNavigate();
  const [sizes, setSizes] = useState([]);
  const [count, setCount] = useState(5);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    api
      .batchSizes()
      .then(({ sizes }) => setSizes(sizes))
      .catch(() => setSizes([5]));
  }, []);

  const run = async () => {
    setBusy(true);
    setError(null);
    try {
      await api.generateBatch(docType.id, loadSettings(docType), loadModel(), count);
      window.dispatchEvent(new Event(DOCUMENTS_CHANGED));
      navigate(`/bizdoc/${docType.id}/results`);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    // Keep clicks here (including the dropdown menu) from closing the mobile drawer.
    <Box sx={{ p: 1.5 }} onClick={(e) => e.stopPropagation()}>
      <Button fullWidth variant="contained" startIcon={<DynamicFeedIcon />} onClick={run} disabled={busy || !sizes.length}>
        Batch Generation
      </Button>
      <TextField
        select
        fullWidth
        size="small"
        label="Documents"
        value={sizes.includes(count) ? count : ""}
        onChange={(e) => setCount(e.target.value)}
        sx={{ mt: 1.5 }}
      >
        {sizes.map((n) => (
          <MenuItem key={n} value={n}>
            {n} {docType.ja}
          </MenuItem>
        ))}
      </TextField>
      <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 1 }}>
        Uses the current Settings. Fields set to random vary per document.
      </Typography>
      {error && (
        <Alert severity="error" sx={{ mt: 1 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}
    </Box>
  );
}

export default function BizDocSidebar({ docType, view }) {
  return (
    <>
      <List sx={{ p: 1.5, pb: 1 }}>
        {ITEMS.map((item) => (
          <ListItemButton
            key={item.view}
            component={Link}
            to={`/bizdoc/${docType.id}/${item.view}`}
            selected={view === item.view}
            sx={{ borderRadius: 1, mb: 0.5 }}
          >
            <ListItemIcon sx={{ minWidth: 36 }}>{item.icon}</ListItemIcon>
            <ListItemText primary={item.label} />
          </ListItemButton>
        ))}
      </List>
      <Divider sx={{ mx: 1.5 }} />
      <BatchGeneration key={docType.id} docType={docType} />
    </>
  );
}
