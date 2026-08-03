import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import "./theme.css";
import "./app.css";
import Inbox from "./pages/Inbox";
import KnowledgeAdmin from "./pages/KnowledgeAdmin";
import Login from "./pages/Login";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter basename="/console">
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/" element={<Inbox />} />
        <Route path="/knowledge" element={<KnowledgeAdmin />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  </React.StrictMode>,
);
