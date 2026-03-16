import React from 'react';
import { Routes, Route } from 'react-router-dom';
import SearchPage from './SearchPage';
import FormPage from './FormPage';
import HistoryView from './HistoryView';
import './App.css';

function App() {
  return (
    <div className="app-shell">
      {/* Header */}
      <header className="app-header">
        <div className="header-content">
          <div className="logo-section">
            <span className="logo-icon">🏥</span>
            <h1 className="logo-text">openEHR<span className="logo-accent">Clinical</span></h1>
          </div>
          <div className="header-badge">Production</div>
        </div>
      </header>

      {/* Main Content */}
      <main className="main-content">
        <Routes>
          <Route path="/" element={<SearchPage />} />
          <Route path="/form/:templateId" element={<FormPage />} />
          <Route path="/history/:ehrId" element={<HistoryView />} />
        </Routes>
      </main>


      {/* Footer */}
      <footer className="app-footer">
        <p>openEHR Clinical Data System &bull; Powered by EHRbase &bull; Medblocks-UI</p>
      </footer>
    </div>
  );
}

export default App;