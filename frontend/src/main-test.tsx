import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import './index.css';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <div className="min-h-screen bg-gray-100 flex items-center justify-center">
      <div className="text-center">
        <h1 className="text-4xl font-bold text-gray-900 mb-4">
          Цветочный B2B
        </h1>
        <p className="text-xl text-gray-600">
          Приложение загружается...
        </p>
      </div>
    </div>
  </StrictMode>
);
