import { useAppSelector } from '../../hooks/useAppSelector';
import CatalogPage from '../catalog/CatalogPage';
import LandingPage from './LandingPage';

export default function HomePage() {
  const isAuthenticated = useAppSelector((state) => state.auth.isAuthenticated);

  if (isAuthenticated) {
    return <CatalogPage />;
  }

  return <LandingPage />;
}
