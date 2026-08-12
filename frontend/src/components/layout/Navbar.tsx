import { Link, useNavigate } from 'react-router-dom';
import { useAuthStore } from '../../store/authStore';
import { useThemeStore } from '../../store/themeStore';
import { Button } from '../ui/Button';
import { LogOut, User, LayoutDashboard, TicketPlus, Sun, Moon, Search, Ticket } from 'lucide-react';
import { useSearchStore } from '../../store/searchStore';

export const Navbar = () => {
  const { user, isAuthenticated, logout } = useAuthStore();
  const { theme, toggleTheme } = useThemeStore();
  const navigate = useNavigate();
  const { setIsOpen } = useSearchStore();

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  return (
    <nav className="sticky top-0 z-50 w-full glass border-b transition-colors duration-300">
      <div className="container mx-auto px-4 h-16 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-1 sm:gap-2 text-primary font-bold text-xl sm:text-2xl tracking-tighter shrink-0 mr-1 sm:mr-0">
          <img src="/eventify-img.png" alt="Eventify Logo" className="w-6 h-6 sm:w-8 sm:h-8 object-contain" />
          <span className="hidden min-[360px]:block">Eventify</span>
        </Link>

        <div className="flex items-center gap-1 sm:gap-4">
          {/* Search Button */}
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setIsOpen(true)}
            className="text-zinc-600 dark:text-zinc-400 w-8 h-8 sm:w-10 sm:h-10 shrink-0"
            title="Buscar"
          >
            <Search className="w-4 h-4 sm:w-5 sm:h-5" />
          </Button>

          <Button variant="ghost" size="icon" onClick={toggleTheme} className="text-zinc-600 dark:text-zinc-400 w-8 h-8 sm:w-10 sm:h-10 shrink-0" title="Alternar Tema">
            {theme === 'dark' ? <Sun className="w-4 h-4 sm:w-5 sm:h-5" /> : <Moon className="w-4 h-4 sm:w-5 sm:h-5" />}
          </Button>

          <div className="h-6 w-px bg-zinc-300 dark:bg-zinc-700 mx-1 hidden sm:block" />

          {!isAuthenticated() ? (
            <div className="flex items-center gap-1 sm:gap-2">
              <Link to="/login">
                <Button variant="ghost" size="sm" className="px-2 sm:px-4 text-xs sm:text-sm h-8 sm:h-10">Entrar</Button>
              </Link>
              <Link to="/register">
                <Button size="sm" className="px-2 sm:px-4 text-xs sm:text-sm h-8 sm:h-10 whitespace-nowrap">Criar Conta</Button>
              </Link>
            </div>
          ) : (
            <div className="flex items-center gap-4">
              {user?.role === 'CLIENT' && (
                <Link to="/tickets">
                  <Button variant="ghost" size="sm" className="gap-2">
                    <TicketPlus className="w-4 h-4" />
                    Meus Ingressos
                  </Button>
                </Link>
              )}
              {user?.role === 'ORGANIZER' && (
                <Link to="/organizer">
                  <Button variant="ghost" size="sm" className="gap-2">
                    <LayoutDashboard className="w-4 h-4" />
                    Painel
                  </Button>
                </Link>
              )}
              {user?.role === 'GATEKEEPER' && (
                <Link to="/gatekeeper">
                  <Button variant="primary" size="sm" className="gap-2">
                    <Ticket className="w-4 h-4" />
                    Validar
                  </Button>
                </Link>
              )}

              <div className="h-6 w-px bg-zinc-300 dark:bg-zinc-700 mx-2" />

              <div className="flex items-center gap-2 text-sm text-zinc-600 dark:text-zinc-300">
                <div className="w-8 h-8 rounded-full bg-zinc-200 dark:bg-zinc-800 flex items-center justify-center border border-zinc-300 dark:border-zinc-700">
                  <User className="w-4 h-4" />
                </div>
                <span className="hidden md:inline-block font-medium">{user?.name}</span>
              </div>

              <Button variant="ghost" size="icon" onClick={handleLogout} title="Sair">
                <LogOut className="w-4 h-4 text-zinc-400 hover:text-red-500 transition-colors" />
              </Button>
            </div>
          )}
        </div>
      </div>
    </nav>
  );
};
