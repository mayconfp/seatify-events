import { useEffect } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '../../store/authStore';
import { Navbar } from './Navbar';
import { SearchOverlay } from './SearchOverlay';
import { Ticket } from 'lucide-react';

const PUBLIC_ROUTES = ['/', '/login', '/register', '/events'];

export const Layout = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { user } = useAuthStore();

  useEffect(() => {
    // Redireciona para /login se o usuario foi deslogado (401) e nao esta
    // em uma rota publica, preservando o estado SPA sem reload.
    const isPublicRoute = PUBLIC_ROUTES.some(route => 
      location.pathname === route || location.pathname.startsWith('/events/')
    );
    
    if (!user && !isPublicRoute) {
      navigate('/login', { replace: true });
    }
  }, [user, location.pathname, navigate]);

  return (
    <>
      <Navbar />
      <SearchOverlay />
      <main className="flex-1 flex flex-col">
        <Outlet />
      </main>
      
      <footer className="border-t border-slate-200 dark:border-slate-800 bg-white/50 dark:bg-slate-950/50 py-8 mt-auto transition-colors duration-300">
        <div className="container mx-auto px-4 flex flex-col md:flex-row items-center justify-between gap-4 text-slate-500 dark:text-slate-400">
          <div className="flex items-center gap-2">
            <Ticket className="w-5 h-5 text-primary" />
            <span className="font-semibold text-slate-800 dark:text-slate-200">Eventify</span>
            <span className="text-sm">© {new Date().getFullYear()}</span>
          </div>
          <p className="text-sm">Plataforma premium de gestão de eventos e ingressos.</p>
        </div>
      </footer>
    </>
  );
};
