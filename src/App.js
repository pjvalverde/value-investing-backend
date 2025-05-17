import './App.css';
import { useState } from 'react';
import PortfolioForm from './components/PortfolioForm';
import PortfolioTable from './components/PortfolioTable';
import PortfolioCharts from './components/PortfolioCharts';
import MethodologyDoc from './components/MethodologyDoc';
import HistoricalChart from './components/HistoricalChart';
import ComparativeTable from './components/ComparativeTable';

function App() {
  const [portfolio, setPortfolio] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [historicalData, setHistoricalData] = useState([]);
  const [comparativeData, setComparativeData] = useState([]);
  const [showAnalysis, setShowAnalysis] = useState(false);
  const [analysis, setAnalysis] = useState('');
  const [analysisLoading, setAnalysisLoading] = useState(false);

  const fetchPortfolio = async (formData) => {
    setLoading(true);
    setError('');
    setShowAnalysis(false);
    try {
      const BASE_URL = process.env.REACT_APP_BACKEND_URL.replace(/\/$/, '');
      const resGen = await fetch(`${BASE_URL}/generate_portfolio`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      });
      if (!resGen.ok) throw new Error('No se pudo generar el portafolio');
      await new Promise(res => setTimeout(res, 2000));
      const res = await fetch(`${BASE_URL}/portfolio`, { method: 'GET' });
      if (!res.ok) throw new Error('No se pudo obtener el portafolio');
      const data = await res.json();
      setPortfolio(data);
      setHistoricalData([]);
      setComparativeData([]);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleShowAnalysis = async () => {
    setAnalysisLoading(true);
    setShowAnalysis(true);
    setAnalysis('');
    try {
      const BASE_URL = process.env.REACT_APP_BACKEND_URL.replace(/\/$/, '');
      const res = await fetch(`${BASE_URL}/justification`);
      if (!res.ok) throw new Error('No se pudo obtener el análisis detallado');
      const data = await res.json();
      setAnalysis(data.html);
    } catch (e) {
      setAnalysis(`<span style='color:red'>${e.message}</span>`);
    } finally {
      setAnalysisLoading(false);
    }
  };

  return (
    <div className="App" style={{ maxWidth: 1200, margin: '0 auto', padding: 24 }}>
      <h1>Value Investing Portfolio App</h1>
      <PortfolioForm onSubmit={fetchPortfolio} loading={loading} />
      {error && <div style={{ color: 'red' }}>{error}</div>}
      {portfolio.length > 0 && (
        <>
          <PortfolioCharts portfolio={portfolio} />
          <PortfolioTable portfolio={portfolio} />
          <div style={{ margin: '24px 0', display: 'flex', justifyContent: 'flex-end', gap: 16 }}>
            <button onClick={() => fetchPortfolio()} disabled={loading}>Regenerar portafolio</button>
            <button onClick={handleShowAnalysis} disabled={analysisLoading} style={{ background: '#3b5998', color: 'white', padding: '8px 20px', borderRadius: 6 }}>
              {analysisLoading ? 'Generando análisis...' : 'Ver análisis detallado'}
            </button>
          </div>
        </>
      )}
      {showAnalysis && (
        <div className="card" style={{ marginTop: 24, padding: 24, background: '#fffbe8' }}>
          <h2>Análisis Detallado del Portafolio</h2>
          <div dangerouslySetInnerHTML={{ __html: analysis }} />
        </div>
      )}
      {historicalData.length > 0 && (
        <HistoricalChart data={historicalData} title="Evolución Histórica del Portfolio" companies={["CompanyA","CompanyB"]} />
      )}
      {comparativeData.length > 0 && (
        <ComparativeTable data={comparativeData} metrics={["ROE","P/E","Margen de Beneficio","Ratio de Deuda","Crecimiento de FCF","Moat Cualitativo"]} />
      )}
      <div style={{ marginTop: 32 }}>
        <h2>Justificación y Metodología</h2>
        <MethodologyDoc highlightMetrics={["ROE","P/E"]} />
      </div>
    </div>
  );
}

export default App;
