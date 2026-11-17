import { useEffect, useRef, useState } from "react";
import {
  AppBar,
  Box,
  ListItemText,
  Menu,
  MenuItem,
  Tab,
  Tabs,
  Toolbar,
  Typography,
} from "@mui/material";
import ArrowDropDownIcon from "@mui/icons-material/ArrowDropDown";
import { Navigate, Route, Routes, useLocation, useNavigate } from "react-router";
import useDocTypes from "./bizdoc/useDocTypes";
import ThemeToggle from "./components/ThemeToggle";
import BizDocPage from "./pages/BizDocPage";
import ChatPage from "./pages/ChatPage";

const DEFAULT_BIZDOC_PATH = "/bizdoc/contracts/settings";

export default function App() {
  const location = useLocation();
  const navigate = useNavigate();
  const { docTypes, findDocType } = useDocTypes();
  const section = location.pathname.startsWith("/bizdoc") ? "bizdoc" : "chat";
  const [, , docTypeId, view] = location.pathname.split("/");
  const currentDocType = section === "bizdoc" ? findDocType(docTypeId) : null;

  // Remember the last Biz Doc view so picking a document type keeps Settings/Results.
  const lastBizDocPath = useRef(DEFAULT_BIZDOC_PATH);
  useEffect(() => {
    if (section === "bizdoc") lastBizDocPath.current = location.pathname;
  }, [section, location.pathname]);

  const [menuAnchor, setMenuAnchor] = useState(null);
  const pickDocType = (id) => {
    setMenuAnchor(null);
    const lastView = lastBizDocPath.current.split("/")[3] || "settings";
    navigate(`/bizdoc/${id}/${section === "bizdoc" ? view || lastView : lastView}`);
  };

  return (
    <Box sx={{ display: "flex", flexDirection: "column", height: "100dvh" }}>
      <AppBar position="static" color="inherit" elevation={0} sx={{ borderBottom: 1, borderColor: "divider" }}>
        <Toolbar variant="dense" sx={{ gap: 2 }}>
          <Typography variant="h6" sx={{ fontWeight: 700, display: { xs: "none", sm: "block" } }}>
            claudeGenData
          </Typography>
          <Tabs
            value={section}
            onChange={(_, v) => v === "chat" && navigate("/chat")}
            sx={{ flex: 1, minHeight: 48, "& .MuiTab-root": { minHeight: 48 } }}
          >
            <Tab value="chat" label="Chat" />
            <Tab
              value="bizdoc"
              label={currentDocType ? `Biz Doc · ${currentDocType.label}` : "Biz Doc"}
              icon={<ArrowDropDownIcon />}
              iconPosition="end"
              aria-haspopup="menu"
              aria-expanded={Boolean(menuAnchor)}
              onClick={(e) => setMenuAnchor(e.currentTarget)}
            />
          </Tabs>
          <ThemeToggle />
        </Toolbar>
      </AppBar>

      <Menu anchorEl={menuAnchor} open={Boolean(menuAnchor)} onClose={() => setMenuAnchor(null)}>
        {docTypes.map((d) => (
          <MenuItem key={d.id} selected={d.id === currentDocType?.id} onClick={() => pickDocType(d.id)}>
            <ListItemText primary={d.label} secondary={d.ja} />
          </MenuItem>
        ))}
      </Menu>

      {/* Chat stays mounted while hidden so a streaming reply isn't interrupted by switching tabs. */}
      <Box sx={{ display: section === "chat" ? "flex" : "none", flex: 1, minHeight: 0 }}>
        <ChatPage />
      </Box>

      <Routes>
        <Route path="/" element={<Navigate to="/chat" replace />} />
        <Route path="/chat" element={null} />
        <Route path="/bizdoc" element={<Navigate to={DEFAULT_BIZDOC_PATH} replace />} />
        <Route path="/bizdoc/:docType" element={<Navigate to="settings" replace />} />
        <Route path="/bizdoc/:docType/:view" element={<BizDocPage />} />
        <Route path="*" element={<Navigate to="/chat" replace />} />
      </Routes>
    </Box>
  );
}
