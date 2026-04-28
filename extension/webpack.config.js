const path = require("path");
const CopyWebpackPlugin = require("copy-webpack-plugin");

const target = process.env.TARGET || "chrome";
const outDir = path.resolve(__dirname, `dist-${target}`);

module.exports = {
  entry: {
    background: "./src/background/index.ts",
    popup: "./src/popup/popup.ts",
    content: "./src/content/index.ts",
  },
  output: {
    path: outDir,
    filename: "[name].js",
    clean: true,
  },
  resolve: {
    extensions: [".ts", ".js"],
  },
  module: {
    rules: [
      {
        test: /\.ts$/,
        use: "ts-loader",
        exclude: /node_modules/,
      },
    ],
  },
  plugins: [
    new CopyWebpackPlugin({
      patterns: [
        { from: "manifest.json", to: "manifest.json" },
        { from: "src/popup/popup.html", to: "popup.html" },
        { from: "src/popup/popup.css", to: "popup.css" },
        { from: "icons", to: "icons", noErrorOnMissing: true },
      ],
    }),
  ],
  // Disable eval-based source maps for CSP compliance in extensions
  devtool: process.env.NODE_ENV === "development" ? "inline-source-map" : false,
};
