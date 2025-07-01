import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.tsx'
import './index.css'
import './landing/landing.css'
// import ErrorBoundary from './components/ErrorBoundary.tsx'

// Global API throttling control
const GLOBAL_API_THROTTLE = {
  apiCalls: {} as Record<string, number>,
  blockedEndpoints: new Set([
    '/api/auth/check-session',
    '/api/auth/check-rate-limit',
    '/images/1.png'
  ]),
  
  canCall: function(url: string, minInterval = 10000): boolean {
    // Always allow non-blocked endpoints
    if (!this.shouldThrottle(url)) {
      return true;
    }
    
    const now = Date.now();
    const lastCall = this.apiCalls[url] || 0;
    
    // If called too soon, block it
    if (now - lastCall < minInterval) {
      console.log(`API call to ${url} throttled. Last call: ${new Date(lastCall).toISOString()}`);
      return false;
    }
    
    this.apiCalls[url] = now;
    return true;
  },
  
  shouldThrottle: function(url: string): boolean {
    return Array.from(this.blockedEndpoints).some(endpoint => url.includes(endpoint));
  }
};

// Override the global fetch to implement throttling
const originalFetch = window.fetch;
window.fetch = function(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
  let url = '';
  
  if (typeof input === 'string') {
    url = input;
  } else if (input instanceof Request) {
    url = input.url;
  } else {
    // Handle URL object
    url = input.toString();
  }
  
  // If this is a throttled endpoint and we've called it recently, mock the response
  if (!GLOBAL_API_THROTTLE.canCall(url)) {
    // Create a mock response for authentication checks
    if (url.includes('/api/auth/check-session')) {
      // Try to use cached auth state
      const cachedAuth = sessionStorage.getItem('auth_state');
      if (cachedAuth) {
        try {
          const authState = JSON.parse(cachedAuth);
          const mockResponse = new Response(
            JSON.stringify({
              authenticated: authState.isAuthenticated,
              auth_type: 'session',
              user_id: authState.userId,
              has_wallet: true,
              banned: false
            }),
            { status: 200, headers: { 'Content-Type': 'application/json' } }
          );
          return Promise.resolve(mockResponse);
        } catch (e) {
          console.error('Error parsing cached auth state', e);
        }
      }
    }
    
    // For other throttled endpoints, return a generic 200 response
    return Promise.resolve(new Response('', { status: 200 }));
  }
  
  // Otherwise, use the original fetch
  return originalFetch(input, init);
};

// Patch ReactDOM to fix DOM manipulation errors
const originalCreateRoot = ReactDOM.createRoot;
ReactDOM.createRoot = function(container: Element | DocumentFragment) {
  // Make sure we're working with a valid container
  if (!container || !(container instanceof Element || container instanceof DocumentFragment)) {
    console.warn('Invalid container provided to ReactDOM.createRoot');
    return originalCreateRoot(document.createElement('div'));
  }
  
  // Clean up any existing React roots before creating new ones
  // This helps prevent the "removeChild" and "insertBefore" errors
  try {
    const rootElement = container as Element;
    
    // Safety check if we can clean up
    if (rootElement && rootElement.innerHTML && typeof rootElement.innerHTML === 'string') {
      console.log('Safely cleaning up container before mounting React');
      
      // Store original content in case we need to restore it
      const originalContent = rootElement.innerHTML;
      
      try {
        // Instead of directly manipulating DOM which can cause issues,
        // use a controlled approach to reset the container
        rootElement.innerHTML = '';
      } catch (cleanupError) {
        console.error('Error during container cleanup:', cleanupError);
        // If cleanup fails, at least we tried and original ReactDOM will handle it
      }
    }
  } catch (e) {
    console.warn('Error in React root preparation:', e);
  }
  
  // Create the root with original method
  return originalCreateRoot(container);
};

// Prevent repeated requests for favicon
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    // Register a service worker that caches the favicon
    navigator.serviceWorker.register('/favicon-sw.js')
      .catch(error => {
        console.error('Service worker registration failed:', error);
      });

    // Create a service worker script dynamically if it doesn't exist
    fetch('/favicon-sw.js')
      .then(response => {
        if (response.status === 404) {
          const swContent = `
            self.addEventListener('install', (event) => {
              event.waitUntil(
                caches.open('favicon-cache').then((cache) => {
                  return cache.addAll([
                    '/images/1.png',
                  ]);
                })
              );
            });

            self.addEventListener('fetch', (event) => {
              if (event.request.url.includes('/images/1.png')) {
                event.respondWith(
                  caches.match(event.request).then((response) => {
                    return response || fetch(event.request);
                  })
                );
              }
            });
          `;
          
          const blob = new Blob([swContent], { type: 'application/javascript' });
          const url = URL.createObjectURL(blob);
          
          // Create a link element to download the file
          const a = document.createElement('a');
          a.href = url;
          a.download = 'favicon-sw.js';
          document.body.appendChild(a);
          a.click();
          document.body.removeChild(a);
        }
      })
      .catch(() => {});
  });
}

// Add the favicon link just once
const addFavicon = () => {
  if (!document.querySelector('link[rel="icon"]')) {
    const link = document.createElement('link');
    link.rel = 'icon';
    link.href = '/images/1.png';
    link.type = 'image/png';
    document.head.appendChild(link);
  }
};

// Prevent multiple favicon requests
document.addEventListener('DOMContentLoaded', addFavicon);
addFavicon(); // Ensure it runs immediately too

// Safe mount helper function
const safeMount = () => {
  try {
    const rootElement = document.getElementById('root');
    if (!rootElement) {
      console.error('Root element not found');
      return;
    }

    ReactDOM.createRoot(rootElement).render(
      // Disabling strict mode can help prevent double mounting issues
      // that sometimes lead to DOM manipulation errors
      //<React.StrictMode>
          <App />
      //</React.StrictMode>
    );
  } catch (err) {
    console.error('Error during React rendering:', err);
    // Fallback rendering directly to body if root mount fails
    const fallbackRoot = document.createElement('div');
    fallbackRoot.id = 'fallback-root';
    document.body.appendChild(fallbackRoot);
    
    ReactDOM.createRoot(fallbackRoot).render(
        <App />
    );
  }
};

// Use the safe mount function
safeMount();