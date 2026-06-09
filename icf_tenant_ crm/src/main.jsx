import React from 'react';
import ReactDOM from 'react-dom/client';
import { Provider } from 'react-redux';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'react-hot-toast';
import App from './App.jsx';
import { store } from './store/index.js';
import { loadMe } from './store/authSlice.js';
import './index.css';

// Restore session on hard refresh if token exists
if (localStorage.getItem('crm_access_token')) {
  store.dispatch(loadMe());
}

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: (count, err) => count < 2 && err?.status !== 401 && err?.status !== 403,
    },
  },
});

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <Provider store={store}>
      <QueryClientProvider client={queryClient}>
        <App />
        <Toaster
          position="top-right"
          toastOptions={{
            duration: 3500,
            style: { fontSize: 13, fontFamily: 'Inter, sans-serif' },
          }}
        />
      </QueryClientProvider>
    </Provider>
  </React.StrictMode>,
);
