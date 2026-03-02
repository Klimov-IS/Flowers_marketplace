import { createBrowserRouter } from 'react-router-dom';
import App from './App';
import HomePage from './features/landing/HomePage';
import CatalogPage from './features/catalog/CatalogPage';
import BuyerDashboard from './features/buyer/BuyerDashboard';
import SellerDashboard from './features/seller/SellerDashboard';
import LoginPage from './features/auth/LoginPage';
import RegisterPage from './features/auth/RegisterPage';
import ResetPasswordPage from './features/auth/ResetPasswordPage';

// Get basename from Vite's base config (set via VITE_BASE_PATH env var)
const basename = import.meta.env.BASE_URL || '/';

export const router = createBrowserRouter([
  {
    path: '/',
    element: <App />,
    children: [
      {
        index: true,
        element: <HomePage />,
      },
      {
        path: 'catalog',
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
      {
        path: 'register',
        element: <RegisterPage />,
      },
      {
        path: 'reset-password',
        element: <ResetPasswordPage />,
      },
    ],
  },
], {
  basename: basename.endsWith('/') ? basename.slice(0, -1) : basename,
});
