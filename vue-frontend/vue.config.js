const { defineConfig } = require('@vue/cli-service')
const config = require('./config-loader')
const portfinder = require('portfinder')

// Force port to be 8080
const port = 8080
console.log('Forcing development server to use port:', port)

// Configure portfinder to only use port 8080
portfinder.basePort = port
portfinder.highestPort = port

module.exports = defineConfig({
  transpileDependencies: true,
  devServer: {
    open: true,
    port: port,
    host: 'localhost',
    allowedHosts: 'all',
    historyApiFallback: {
      rewrites: [
        { from: /^\/admin.*$/, to: '/index.html' },
        { from: /^\/projects.*$/, to: '/index.html' },
        { from: /^\/jobs.*$/, to: '/index.html' },
        { from: /./, to: '/index.html' }
      ]
    },
    proxy: {
      '/api': {
        target: config.FRONTEND_API_URL,
        changeOrigin: true,
        secure: false,
        logLevel: 'debug'
      }
    }
  }
})
