const { createProxyMiddleware } = require('http-proxy-middleware');

// Get environment configuration
const isProduction = process.env.NODE_ENV === 'production';
const apiTarget = process.env.REACT_APP_API_BASE_URL || 'https://3.115.141.166';
const wsTarget = process.env.REACT_APP_WS_URL || 'wss://3.115.141.166';

module.exports = function(app) {
  // WebSocket proxy for development server
  app.use(
    '/ws',
    createProxyMiddleware({
      target: wsTarget,
      ws: true,
      changeOrigin: true,
      secure: isProduction, // Use SSL verification in production
      onError: (err, req, res) => {
        console.error('WebSocket proxy error:', err);
      }
    })
  );
  
  // API proxy
  app.use(
    '/api',
    createProxyMiddleware({
      target: apiTarget,
      changeOrigin: true,
      secure: isProduction, // Use SSL verification in production
      onError: (err, req, res) => {
        console.error('API proxy error:', err);
        res.status(500).json({ error: 'Proxy error' });
      }
    })
  );
};