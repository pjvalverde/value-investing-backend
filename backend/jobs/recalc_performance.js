/**
 * Job para recalcular el rendimiento de los portfolios
 * Se ejecuta diariamente a las 23:00 UTC
 */

const { Pool } = require('pg');
require('dotenv').config();

// Configurar conexiu00f3n a la base de datos
const pool = new Pool({
  connectionString: process.env.DATABASE_URL
});

// Funciu00f3n principal
async function recalcPerformance() {
  console.log('Iniciando cu00e1lculo de rendimiento de portfolios...');
  
  try {
    // 1. Obtener todos los portfolios activos
    const portfoliosResult = await pool.query('SELECT id, current_alloc FROM portfolios WHERE current_alloc IS NOT NULL');
    const portfolios = portfoliosResult.rows;
    
    console.log(`Procesando ${portfolios.length} portfolios...`);
    
    // 2. Obtener precios actuales
    const pricesResult = await pool.query('SELECT ticker, price FROM fundamentals WHERE asof = $1', [new Date().toISOString().split('T')[0]]);
    const prices = pricesResult.rows.reduce((acc, row) => {
      acc[row.ticker] = row.price;
      return acc;
    }, {});
    
    // 3. Para cada portfolio, calcular el valor actual
    for (const portfolio of portfolios) {
      try {
        const currentAlloc = portfolio.current_alloc;
        let totalValue = 0;
        
        // Calcular valor total del portfolio
        for (const position of currentAlloc) {
          const ticker = position.ticker;
          const shares = position.shares;
          const currentPrice = prices[ticker] || position.price; // Usar precio actual o el u00faltimo conocido
          
          const positionValue = shares * currentPrice;
          totalValue += positionValue;
        }
        
        // Insertar en la tabla de rendimiento
        await pool.query(
          `INSERT INTO portfolio_returns (portfolio_id, date, value)
           VALUES ($1, $2, $3)
           ON CONFLICT (portfolio_id, date) DO UPDATE
           SET value = $3`,
          [portfolio.id, new Date().toISOString().split('T')[0], totalValue]
        );
        
        console.log(`Portfolio ${portfolio.id}: valor actual = $${totalValue.toFixed(2)}`);
      } catch (error) {
        console.error(`Error al procesar portfolio ${portfolio.id}:`, error.message);
      }
    }
    
    // 4. Actualizar el rendimiento del S&P 500 (benchmark)
    try {
      // Obtener el precio actual de SPY (ETF que sigue al S&P 500)
      const spyPrice = prices['SPY'] || 450; // Valor por defecto si no hay precio
      
      await pool.query(
        `INSERT INTO benchmark_returns (ticker, date, value)
         VALUES ($1, $2, $3)
         ON CONFLICT (ticker, date) DO UPDATE
         SET value = $3`,
        ['SPY', new Date().toISOString().split('T')[0], spyPrice]
      );
      
      console.log(`Benchmark SPY: valor actual = $${spyPrice.toFixed(2)}`);
    } catch (error) {
      console.error('Error al actualizar benchmark:', error.message);
    }
    
    console.log('Cu00e1lculo de rendimiento completado');
  } catch (error) {
    console.error('Error en el job de cu00e1lculo de rendimiento:', error);
  } finally {
    // Cerrar la conexiu00f3n a la base de datos
    await pool.end();
  }
}

// Ejecutar el job
recalcPerformance().catch(console.error);
