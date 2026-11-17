import { Alert, Box, CircularProgress, Typography } from "@mui/material";
import { Navigate, useParams } from "react-router";
import BizDocSidebar from "../bizdoc/BizDocSidebar";
import ResultsPage from "../bizdoc/ResultsPage";
import SettingsPage from "../bizdoc/SettingsPage";
import useDocTypes from "../bizdoc/useDocTypes";
import SplitLayout from "../layout/SplitLayout";

const VIEWS = ["settings", "results"];

export default function BizDocPage() {
  const { docType: docTypeId, view } = useParams();
  const { findDocType, loading, error } = useDocTypes();

  if (loading || error) {
    return (
      <Box sx={{ flex: 1, display: "grid", placeItems: "center", p: 2 }}>
        {error ? <Alert severity="error">Cannot load document types: {error}</Alert> : <CircularProgress />}
      </Box>
    );
  }

  const docType = findDocType(docTypeId);
  if (!docType || !VIEWS.includes(view)) {
    return <Navigate to="/bizdoc/contracts/settings" replace />;
  }

  return (
    <SplitLayout
      sidebar={<BizDocSidebar docType={docType} view={view} />}
      header={
        <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
          {docType.label} <Box component="span" sx={{ color: "text.secondary", fontWeight: 400 }}>{docType.ja}</Box>
          {" · "}
          {view === "settings" ? "Settings" : "Results"}
        </Typography>
      }
    >
      {/* key resets page state when switching document type */}
      {view === "settings" ? (
        <SettingsPage key={docType.id} docType={docType} />
      ) : (
        <ResultsPage key={docType.id} docType={docType} />
      )}
    </SplitLayout>
  );
}
