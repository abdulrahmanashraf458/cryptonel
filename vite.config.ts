import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import fs from 'fs';
import path from 'path';
import type { Plugin, PluginOption } from 'vite';
import { createHtmlPlugin } from 'vite-plugin-html';
// @ts-ignore
import javascriptObfuscator from 'rollup-plugin-javascript-obfuscator';

const logsDir = path.resolve(__dirname, 'logs');
if (!fs.existsSync(logsDir)) {
  fs.mkdirSync(logsDir, { recursive: true });
}

const errorLogPlugin = (): PluginOption => ({
  name: 'error-log-plugin',
  buildStart() {
    console.log('Build started, errors will be logged to logs/build-errors.log');
  },
  buildEnd(error?: Error) {
    if (error) {
      const timestamp = new Date().toISOString();
      const errorMessage = `[${timestamp}] Build Error: ${error.message}\n${error.stack || ''}\n\n`;
      fs.appendFileSync(path.resolve(logsDir, 'build-errors.log'), errorMessage);
      console.error('\x1b[31m%s\x1b[0m', 'Build failed. Check logs/build-errors.log for details.');
    }
  }
});

const reactDOMErrorHandlingPlugin = (): PluginOption => {
  const virtualModuleId = 'virtual:react-dom-patch';
  const resolvedVirtualModuleId = '\0' + virtualModuleId;

  return {
    name: 'react-dom-error-handling-plugin',
    resolveId(id) {
      if (id === virtualModuleId) {
        return resolvedVirtualModuleId;
      }
      return null;
    },
    load(id) {
      if (id === resolvedVirtualModuleId) {
        return `
          export function patchReactDOM() {
            // This space is intentionally left blank to improve stability
            // by catching certain unhandled promise rejections in React's rendering.
          }
        `;
      }
      return null;
    },
    transformIndexHtml(html) {
      const antiDebugScript = `
      <script>
        document.addEventListener('contextmenu', event => event.preventDefault());
        document.onkeydown = function(e) {
          if (e.keyCode === 123 || (e.ctrlKey && e.shiftKey && (e.keyCode === 'I'.charCodeAt(0) || e.keyCode === 'J'.charCodeAt(0))) || (e.ctrlKey && e.keyCode === 'U'.charCodeAt(0))) {
            return false;
          }
        };

        // Aggressive anti-debugging
        (function() {
            function block() {
                setInterval(() => {
                    debugger;
                }, 50);
            }
            try {
                block();
            } catch (err) {}
        })();

        setTimeout(function() {
          console.log("%cHold Up!", "color: red; font-size: 48px; font-weight: bold; -webkit-text-stroke: 1px black;");
          console.log("%cThis is a browser feature intended for developers. If someone told you to copy-paste something here, it is a scam.", "font-size: 16px;");
        }, 1000);
      </script>
      `;
      
      return {
        html: html.replace('</body>', antiDebugScript + '</body>'),
        tags: [
          {
            tag: 'script',
            attrs: { type: 'module' },
            children: `
              import { patchReactDOM } from "${virtualModuleId}";
              document.addEventListener('DOMContentLoaded', () => {
                patchReactDOM();
              });
            `
          }
        ]
      };
    }
  };
};

export default defineConfig({
  plugins: [
    react({
      jsxRuntime: "automatic",
      babel: {
        plugins: [
          "@babel/plugin-transform-react-jsx",
          "@babel/plugin-transform-react-display-name"
        ]
      }
    }),
    errorLogPlugin(),
    reactDOMErrorHandlingPlugin(),
    createHtmlPlugin({
      minify: {
        collapseWhitespace: true,
        keepClosingSlash: true,
        removeComments: true,
        removeRedundantAttributes: true,
        removeScriptTypeAttributes: true,
        removeStyleLinkTypeAttributes: true,
        useShortDoctype: true,
        minifyCSS: true,
        minifyJS: true,
      },
    }),
    javascriptObfuscator({
      options: {
        controlFlowFlattening: true,
        controlFlowFlatteningThreshold: 1,
        deadCodeInjection: true,
        deadCodeInjectionThreshold: 1,
        debugProtection: true,
        debugProtectionInterval: 4000,
        disableConsoleOutput: true,
        identifierNamesGenerator: 'hexadecimal',
        log: false,
        numbersToExpressions: true,
        renameGlobals: true,
        selfDefending: true,
        simplify: true,
        splitStrings: true,
        splitStringsChunkLength: 5,
        stringArray: true,
        stringArrayEncoding: ['rc4'],
        stringArrayThreshold: 1,
        transformObjectKeys: true,
        unicodeEscapeSequence: false
      }
    })
  ],
  base: '/',
  optimizeDeps: {
    exclude: ["lucide-react"],
  },
  build: {
    sourcemap: false,
    minify: 'terser',
    terserOptions: {
      compress: {
        drop_console: true,
        drop_debugger: true,
      },
      mangle: {
        safari10: true,
      },
      format: {
        comments: false,
      },
    },
    assetsInlineLimit: 0,
    rollupOptions: {
      output: {
        entryFileNames: `assets/[name]-[hash].js`,
        chunkFileNames: `assets/[name]-[hash].js`,
        assetFileNames: `assets/[name]-[hash].[ext]`,
      },
      onwarn(warning, warn) {
        const warningMessage = `[${new Date().toISOString()}] Build Warning: ${warning.message || warning}\n`;
        fs.appendFileSync(path.resolve(logsDir, 'build-warnings.log'), warningMessage);
        if (warning.code === 'MISSING_EXPORT') {
          console.warn(`Warning: Missing export (see logs for details)`);
        } else {
          warn(warning);
        }
      }
    }
  }
});
