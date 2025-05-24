import React from 'react';
import PortfolioTable from './PortfolioTable';
import PortfolioCharts from './PortfolioCharts';

// Componente que muestra el resultado del portafolio optimizado
// Espera props: portfolio (objeto con allocation, metrics, id, source), amount (monto invertido)
import React, { useState } from 'react';
import PortfolioTable from './PortfolioTable';
import PortfolioCharts from './PortfolioCharts';

const PortfolioResults = ({ portfolio, amount }) => {
  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  if (!portfolio) return <div>No hay datos de portafolio.</div>;

  const { allocation = [], metrics = {}, id, source } = portfolio;

  const handleAnalyze = async () => {
    setLoading(true);
    setError('');
    setAnalysis(null);
    try {
      const BASE_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8000';
      const response = await fetch(`${BASE_URL}/api/portfolio/analysis`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ portfolio: allocation, language: 'es' })
      });
      if (!response.ok) {
        const errorData = await response.text();
        throw new Error(`Error al analizar con Claude: ${response.status} ${errorData}`);
      }
      const data = await response.json();
      setAnalysis(data.analysis || 'Sin análisis disponible');
    } catch (err) {
      setError(err.message || 'Error desconocido al analizar con Claude');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="portfolio-results-container">
      <h3>Composición del Portafolio</h3>
      <PortfolioTable portfolio={allocation} />

      <h3>Distribución por Sector</h3>
      <PortfolioCharts portfolio={allocation} />

      <h3>Métricas del Portafolio</h3>
      <div className="portfolio-metrics">
        <div><b>Retorno esperado:</b> {metrics.expected_return != null ? `${metrics.expected_return}%` : 'N/D'}</div>
        <div><b>Volatilidad:</b> {metrics.volatility != null ? `${metrics.volatility}%` : 'N/D'}</div>
        <div><b>Sharpe Ratio:</b> {metrics.sharpe_ratio != null ? metrics.sharpe_ratio : 'N/D'}</div>
      </div>

      <div className="portfolio-meta">
        <div><b>ID de portafolio:</b> {id}</div>
        <div><b>Fuente de datos:</b> {source}</div>
        <div><b>Monto invertido:</b> {amount ? `$${amount}` : 'N/D'}</div>
      </div>

      <div style={{marginTop: 24}}>
        <button onClick={handleAnalyze} disabled={loading} className="analyze-button">
          {loading ? 'Analizando con Claude...' : 'Ver análisis técnico con Claude'}
        </button>
        {error && <div className="error-message">{error}</div>}
        {analysis && (
          <div className="claude-analysis" style={{marginTop: 16, background: '#f6f6f6', padding: 16, borderRadius: 8}}>
            <h4>Análisis detallado (Claude):</h4>
            <pre style={{whiteSpace: 'pre-wrap'}}>{analysis}</pre>
          </div>
        )}
      </div>
    </div>
  );
};

export default PortfolioResults;
