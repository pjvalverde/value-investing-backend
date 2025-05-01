/**
 * Job para actualizar los precios y calcular indicadores de momentum
 * Se ejecuta cada hora
 */

const axios = require('axios');
const { Pool } = require('pg');
require('dotenv').config();

// Configurar conexiu00f3n a la base de datos
const pool = new Pool({
  connectionString: process.env.DATABASE_URL
});

// Funciu00f3n principal
async function refreshPrices() {
  console.log('Iniciando actualizaciu00f3n de precios y momentum...');
  
  try {
    // 1. Obtener lista de su00edmbolos a actualizar
    const symbolsResult = await pool.query('SELECT ticker FROM symbols');
    const symbols = symbolsResult.rows.map(row => row.ticker);
    
    console.log(`Actualizando ${symbols.length} su00edmbolos...`);
    
    // 2. Para cada su00edmbolo, obtener datos de Alpha Vantage
    const ALPHA_VANTAGE_API_KEY = process.env.ALPHAVANTAGE_API_KEY;
    
    if (!ALPHA_VANTAGE_API_KEY) {
      throw new Error('ALPHAVANTAGE_API_KEY no estu00e1 configurada');
    }
    
    // Procesar en lotes para evitar rate limits
    const batchSize = 5;
    const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
    
    for (let i = 0; i < symbols.length; i += batchSize) {
      const batch = symbols.slice(i, i + batchSize);
      
      await Promise.all(batch.map(async (ticker) => {
        try {
          // Obtener series de tiempo diarias ajustadas
          const timeSeriesUrl = `https://www.alphavantage.co/query?function=TIME_SERIES_DAILY_ADJUSTED&symbol=${ticker}&outputsize=full&apikey=${ALPHA_VANTAGE_API_KEY}`;
          const timeSeriesResponse = await axios.get(timeSeriesUrl);
          const timeSeriesData = timeSeriesResponse.data;
          
          if (timeSeriesData && timeSeriesData['Time Series (Daily)']) {
            const timeSeries = timeSeriesData['Time Series (Daily)'];
            const dates = Object.keys(timeSeries).sort().reverse(); // Ordenar por fecha descendente
            
            if (dates.length > 0) {
              // Obtener el precio mu00e1s reciente
              const latestDate = dates[0];
              const latestPrice = parseFloat(timeSeries[latestDate]['4. close']);
              
              // Calcular SMA50
              const sma50 = dates.slice(0, Math.min(50, dates.length))
                .reduce((sum, date) => sum + parseFloat(timeSeries[date]['4. close']), 0) / Math.min(50, dates.length);
              
              // Calcular SMA200
              const sma200 = dates.slice(0, Math.min(200, dates.length))
                .reduce((sum, date) => sum + parseFloat(timeSeries[date]['4. close']), 0) / Math.min(200, dates.length);
              
              // Calcular retorno de 6 meses
              let sixMonthsAgoPrice = latestPrice;
              if (dates.length >= 126) { // Aproximadamente 6 meses (126 du00edas de trading)
                sixMonthsAgoPrice = parseFloat(timeSeries[dates[125]]['4. close']);
              }
              const return6m = (latestPrice / sixMonthsAgoPrice) - 1;
              
              // Actualizar precio en fundamentals
              await pool.query(
                `UPDATE fundamentals SET price = $1 WHERE ticker = $2 AND asof = $3`,
                [latestPrice, ticker, new Date().toISOString().split('T')[0]]
              );
              
              // Actualizar o insertar en momentum
              await pool.query(
                `INSERT INTO momentum (ticker, sma50, sma200, return_6m, asof)
                 VALUES ($1, $2, $3, $4, $5)
                 ON CONFLICT (ticker, asof) DO UPDATE
                 SET sma50 = $2, sma200 = $3, return_6m = $4`,
                [ticker, sma50, sma200, return6m, new Date().toISOString().split('T')[0]]
              );
              
              console.log(`Actualizado ${ticker}: precio=${latestPrice}, sma50=${sma50.toFixed(2)}, sma200=${sma200.toFixed(2)}, return6m=${(return6m*100).toFixed(2)}%`);
            } else {
              console.log(`No hay datos de series de tiempo para ${ticker}`);
            }
          } else {
            console.log(`No se encontraron datos para ${ticker}`);
          }
        } catch (error) {
          console.error(`Error al actualizar ${ticker}:`, error.message);
        }
      }));
      
      // Esperar para evitar rate limits
      if (i + batchSize < symbols.length) {
        console.log('Esperando para evitar rate limits...');
        await delay(12000); // Esperar 12 segundos entre lotes
      }
    }
    
    console.log('Actualizaciu00f3n de precios y momentum completada');
  } catch (error) {
    console.error('Error en el job de actualizaciu00f3n de precios:', error);
  } finally {
    // Cerrar la conexiu00f3n a la base de datos
    await pool.end();
  }
}

// Ejecutar el job
refreshPrices().catch(console.error);
