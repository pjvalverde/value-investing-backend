/**
 * Job para actualizar los datos fundamentales de las acciones
 * Se ejecuta diariamente a las 02:00 UTC
 */

const axios = require('axios');
const { Pool } = require('pg');
require('dotenv').config();

// Configurar conexiu00f3n a la base de datos
const pool = new Pool({
  connectionString: process.env.DATABASE_URL
});

// Funciu00f3n principal
async function refreshFundamentals() {
  console.log('Iniciando actualizaciu00f3n de datos fundamentales...');
  
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
          // Obtener overview para datos fundamentales
          const overviewUrl = `https://www.alphavantage.co/query?function=OVERVIEW&symbol=${ticker}&apikey=${ALPHA_VANTAGE_API_KEY}`;
          const overviewResponse = await axios.get(overviewUrl);
          const overviewData = overviewResponse.data;
          
          if (overviewData && overviewData.Symbol) {
            // Extraer datos relevantes
            const fundamentals = {
              ticker,
              yoy_rev_growth: parseFloat(overviewData.RevenueTTM || 0) / parseFloat(overviewData.RevenueTTM || 1) - 1,
              gross_margin: parseFloat(overviewData.GrossProfitTTM || 0) / parseFloat(overviewData.RevenueTTM || 1),
              roe_ttm: parseFloat(overviewData.ReturnOnEquityTTM || 0),
              forward_pe: parseFloat(overviewData.ForwardPE || 0),
              price: parseFloat(overviewData.AnalystTargetPrice || 0),
              asof: new Date().toISOString().split('T')[0]
            };
            
            // Actualizar en la base de datos
            await pool.query(
              `INSERT INTO fundamentals (ticker, yoy_rev_growth, gross_margin, roe_ttm, forward_pe, price, asof)
               VALUES ($1, $2, $3, $4, $5, $6, $7)
               ON CONFLICT (ticker, asof) DO UPDATE
               SET yoy_rev_growth = $2, gross_margin = $3, roe_ttm = $4, forward_pe = $5, price = $6`,
              [fundamentals.ticker, fundamentals.yoy_rev_growth, fundamentals.gross_margin, 
               fundamentals.roe_ttm, fundamentals.forward_pe, fundamentals.price, fundamentals.asof]
            );
            
            console.log(`Actualizado ${ticker} correctamente`);
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
    
    console.log('Actualizaciu00f3n de datos fundamentales completada');
  } catch (error) {
    console.error('Error en el job de actualizaciu00f3n de fundamentales:', error);
  } finally {
    // Cerrar la conexiu00f3n a la base de datos
    await pool.end();
  }
}

// Ejecutar el job
refreshFundamentals().catch(console.error);
