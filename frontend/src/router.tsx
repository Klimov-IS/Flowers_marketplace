import { createBrowserRouter } from 'react-router-dom';
import App from './App';
import CatalogPage from './features/catalog/CatalogPage';
import BuyerDashboard from './features/buyer/BuyerDashboard';
import SellerDashboard from './features/seller/SellerDashboard';
import LoginPage from './features/auth/LoginPage';

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
]);
