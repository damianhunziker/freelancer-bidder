const path = require('path');

module.exports = {
  mode: 'development', // 'production' für Produktionsumgebungen
  entry: './src/index.js', // Der Einstiegspunkt Ihrer Anwendung
  output: {
    filename: 'bundle.js', // Der Name der Ausgabedatei
    path: path.resolve(__dirname, 'dist'), // Der Ausgabepfad
  },
  module: {
    rules: [
      {
        test: /\.js$/, // Regulärer Ausdruck, der alle .js Dateien abgleicht
        exclude: /node_modules/, // node_modules Verzeichnis ausschließen
        use: {
          loader: 'babel-loader', // Babel Loader verwenden, um ES6 in ES5 zu transpilieren
          options: {
            presets: ['@babel/preset-env'] // Babel Preset für moderne JavaScript Features
          }
        }
      },
      {
        test: /\.vue$/,
        loader: 'vue-loader'
      }
    ]
  }
}; 