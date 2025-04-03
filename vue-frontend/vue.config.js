const { defineConfig } = require('@vue/cli-service')

module.exports = defineConfig({
  transpileDependencies: true,
  devServer: {
    open: true,
    port: 8080,
    proxy: {
      '/api': {
        target: 'http://localhost:8080',
        changeOrigin: true,
        pathRewrite: {
          '^/api': '/api'
        },
        logLevel: 'debug',
        onProxyReq(proxyReq, req, res) {
          console.log('[Proxy] Request:', req.method, req.url);
        },
        onProxyRes(proxyRes, req, res) {
          console.log('[Proxy] Response:', proxyRes.statusCode, req.url);
        },
        onError(err, req, res) {
          console.error('[Proxy] Error:', err);
        }
      }
    }
  }
})
