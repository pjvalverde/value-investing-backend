import React from 'react';
import PortfolioTable from './PortfolioTable';
import PortfolioCharts from './PortfolioCharts';

// Componente que muestra el resultado del portafolio optimizado
// Espera props: portfolio (objeto con allocation, metrics, id, source), amount (monto invertido)
const PortfolioResults = ({ portfolio, amount }) => {
  if (!portfolio) return <div>No hay datos de portafolio.</div>;

  const { allocation = [], metrics = {}, id, source } = portfolio;

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
    </div>
  );
};

export default PortfolioResults;
