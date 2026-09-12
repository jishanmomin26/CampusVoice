import './App.css';

function App() {
  return (
    <div className="container">
      <main className="hero-card">
        <div className="status-badge">
          <span className="pulse-dot"></span>
          Step 1 &bull; Project Initialized
        </div>
        <h1 className="title">CampusVoice</h1>
        <p className="subtitle">AI-Powered Student Feedback Intelligence System</p>
        <div className="divider"></div>
        <div className="meta-footer">
          <span className="meta-item">React Frontend</span>
          <span>&bull;</span>
          <span className="meta-item">FastAPI Backend</span>
          <span>&bull;</span>
          <span className="meta-item">NLP & ML Pipeline</span>
        </div>
      </main>
    </div>
  );
}

export default App;
