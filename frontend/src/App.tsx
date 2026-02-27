import { Outlet, useLocation } from 'react-router-dom';
import { useAppSelector } from './hooks/useAppSelector';
import Header from './components/layout/Header';
import Footer from './components/layout/Footer';

function App() {
  const isAuthenticated = useAppSelector((state) => state.auth.isAuthenticated);
  const location = useLocation();

  // Landing page has its own header/footer — don't wrap with standard layout
  const isLandingPage = !isAuthenticated && location.pathname === '/';

  if (isLandingPage) {
    return <Outlet />;
  }

  return (
    <div className="min-h-screen flex flex-col bg-gray-50">
      <Header />
      <main className="flex-1">
        <Outlet />
      </main>
      <Footer />
    </div>
  );
}

export default App;
