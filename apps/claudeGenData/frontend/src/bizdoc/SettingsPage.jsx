import { useEffect, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Chip,
  MenuItem,
  Paper,
  Snackbar,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import AutoAwesomeIcon from "@mui/icons-material/AutoAwesome";
import RestartAltIcon from "@mui/icons-material/RestartAlt";
import { useNavigate } from "react-router";
import { api } from "../api";
import { defaultsFor, loadModel, loadSettings, saveModel, saveSettings } from "./settingsStorage";
import useDocTypes from "./useDocTypes";

const RANDOM_LABEL = "ランダム (random)";

const SECTION_HELP = {
  "Training labels":
    "Selected issues are deliberately inserted and recorded in the labels, so a model can learn to find them.",
};

function Field({ field, value, onChange, random }) {
  if (field.type === "select") {
    return (
      <TextField select size="small" fullWidth label={field.label} value={value} onChange={(e) => onChange(e.target.value)}>
        <MenuItem value={random}>
          <Typography color="text.secondary">{RANDOM_LABEL}</Typography>
        </MenuItem>
        {field.options.map((o) => (
          <MenuItem key={o} value={o}>
            {o}
          </MenuItem>
        ))}
      </TextField>
    );
  }

  if (field.type === "multiselect") {
    const toggle = (option) =>
      onChange(value.includes(option) ? value.filter((v) => v !== option) : [...value, option]);
    return (
      <Box sx={{ gridColumn: "1 / -1" }}>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
          {field.label}
        </Typography>
        <Stack direction="row" sx={{ flexWrap: "wrap", gap: 1 }}>
          {field.options.map((o) => {
            const selected = value.includes(o);
            return (
              <Chip
                key={o}
                label={o}
                color={selected ? "primary" : "default"}
                variant={selected ? "filled" : "outlined"}
                onClick={() => toggle(o)}
              />
            );
          })}
        </Stack>
      </Box>
    );
  }

  return (
    <TextField
      multiline
      minRows={2}
      fullWidth
      label={field.label}
      placeholder={field.placeholder}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      sx={{ gridColumn: "1 / -1" }}
    />
  );
}

export default function SettingsPage({ docType }) {
  const navigate = useNavigate();
  const { sections, random } = useDocTypes();
  const [values, setValues] = useState(() => loadSettings(docType));
  const [models, setModels] = useState([]);
  const [model, setModel] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [notice, setNotice] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.models().then(({ models, default: def }) => {
      setModels(models);
      const saved = loadModel();
      setModel(models.some((m) => m.id === saved) ? saved : def);
    });
  }, []);

  useEffect(() => saveSettings(docType.id, values), [docType.id, values]);

  const setValue = (id, v) => setValues((prev) => ({ ...prev, [id]: v }));

  const changeModel = (m) => {
    setModel(m);
    saveModel(m);
  };

  const generate = async () => {
    setSubmitting(true);
    setError(null);
    try {
      await api.generateDocument(docType.id, values, model);
      setNotice(`Generating a ${docType.ja}. It usually takes under a minute.`);
    } catch (e) {
      setError(e.message);
    } finally {
      setSubmitting(false);
    }
  };

  const bySection = sections
    .map((name) => ({ name, fields: docType.fields.filter((f) => f.section === name) }))
    .filter((s) => s.fields.length > 0);

  return (
    <>
      <Box sx={{ flex: 1, overflowY: "auto", px: 2, pb: 2 }}>
        <Stack spacing={2} sx={{ maxWidth: 960, mx: "auto" }}>
          {bySection.map((section) => (
            <Paper key={section.name} variant="outlined" sx={{ p: 2 }}>
              <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: SECTION_HELP[section.name] ? 0.5 : 2 }}>
                {section.name}
              </Typography>
              {SECTION_HELP[section.name] && (
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  {SECTION_HELP[section.name]}
                </Typography>
              )}
              <Box
                sx={{
                  display: "grid",
                  gap: 2,
                  gridTemplateColumns: { xs: "1fr", sm: "repeat(2, 1fr)", lg: "repeat(3, 1fr)" },
                }}
              >
                {section.fields.map((f) => (
                  <Field key={f.id} field={f} value={values[f.id]} random={random} onChange={(v) => setValue(f.id, v)} />
                ))}
              </Box>
            </Paper>
          ))}
        </Stack>
      </Box>

      <Box sx={{ borderTop: 1, borderColor: "divider", px: 2, py: 1.5 }}>
        <Stack
          direction="row"
          spacing={1.5}
          sx={{ maxWidth: 960, mx: "auto", alignItems: "center", flexWrap: "wrap", rowGap: 1 }}
        >
          <TextField
            select
            size="small"
            label="Model"
            value={models.length ? model : ""}
            onChange={(e) => changeModel(e.target.value)}
            sx={{ minWidth: 200 }}
          >
            {models.map((m) => (
              <MenuItem key={m.id} value={m.id}>
                {m.name}
              </MenuItem>
            ))}
          </TextField>
          <Button startIcon={<RestartAltIcon />} onClick={() => setValues(defaultsFor(docType))}>
            Reset
          </Button>
          <Box sx={{ flex: 1 }} />
          {error && (
            <Alert severity="error" sx={{ py: 0 }} onClose={() => setError(null)}>
              {error}
            </Alert>
          )}
          <Button
            variant="contained"
            size="large"
            startIcon={<AutoAwesomeIcon />}
            onClick={generate}
            disabled={submitting || !model}
          >
            Generate
          </Button>
        </Stack>
      </Box>

      <Snackbar
        open={Boolean(notice)}
        autoHideDuration={6000}
        onClose={() => setNotice(null)}
        message={notice}
        action={
          <Button color="primary" size="small" onClick={() => navigate(`/bizdoc/${docType.id}/results`)}>
            View results
          </Button>
        }
      />
    </>
  );
}
