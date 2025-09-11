const { createProxyMiddleware } = require('http-proxy-middleware');

module.exports = function(app) {
  // WebSocket proxy for development server
  app.use(
    '/ws',
    createProxyMiddleware({
      target: 'wss://3.115.141.166',
      ws: true,
      changeOrigin: true,
      secure: false, // Allow self-signed certificates
      onError: (err, req, res) => {
        console.error('WebSocket proxy error:', err);
      }
    })
  );
  
  // API proxy
  app.use(
    '/api',
    createProxyMiddleware({
      target: 'https://3.115.141.166',
      changeOrigin: true,
      secure: false, // Allow self-signed certificates
      onError: (err, req, res) => {
        console.error('API proxy error:', err);
        res.status(500).json({ error: 'Proxy error' });
      }
    })
  );
};