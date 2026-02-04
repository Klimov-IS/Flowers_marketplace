import { createBrowserRouter } from 'react-router-dom';
import App from './App';
import CatalogPage from './features/catalog/CatalogPage';
import BuyerDashboard from './features/buyer/BuyerDashboard';
import SellerDashboard from './features/seller/SellerDashboard';
import LoginPage from './features/auth/LoginPage';

// Get basename from Vite's base config (set via VITE_BASE_PATH env var)
const basename = import.meta.env.BASE_URL || '/';

export const router = createBrowserRouter([
  {
    path: '/',
    element: <App />,
    children: [
      {
        index: true,
        element: <CatalogPage />,
      },
      {
        path: 'buyer',
        element: <BuyerDashboard />,
      },
      {
        path: 'seller',
        element: <SellerDashboard />,
      },
      {
        path: 'login',
        element: <LoginPage />,
      },
    ],
  },
], {
  basename: basename.endsWith('/') ? basename.slice(0, -1) : basename,
});
