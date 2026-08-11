import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { api } from '../../api/axios';
import { useAuthStore } from '../../store/authStore';
import { Button } from '../../components/ui/Button';
import { Input } from '../../components/ui/Input';
import { Mail, Lock, Ticket, X } from 'lucide-react';
import { toast } from 'sonner';

export const Login = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const { setToken, setUser } = useAuthStore();
  const navigate = useNavigate();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      // Create FormData as expected by OAuth2PasswordRequestForm
      const formData = new URLSearchParams();
      formData.append('username', email); // OAuth2 expects 'username'
      formData.append('password', password);

      const response = await api.post('/auth/login', formData, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
      });
      
      const { access_token } = response.data;
      setToken(access_token);
      
      // Fetch /auth/me
      const meResponse = await api.get('/auth/me');
      setUser(meResponse.data);
      
      toast.success('Login realizado com sucesso!');
      navigate('/');
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Credenciais inválidas.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/60 backdrop-blur-md animate-in fade-in duration-300">
      <div className="w-full max-w-md bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-8 rounded-3xl shadow-2xl relative animate-in zoom-in-95 duration-300 transition-colors">
        
        {/* Close Button */}
        <button 
          onClick={() => navigate('/')}
          className="absolute top-6 right-6 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition-colors"
          aria-label="Fechar"
        >
          <X className="w-6 h-6" />
        </button>

        <div className="flex flex-col items-center mb-8">
          <div className="w-16 h-16 bg-primary/10 dark:bg-primary/20 rounded-full flex items-center justify-center mb-4 border border-primary/20 dark:border-primary/30">
            <Ticket className="w-8 h-8 text-primary" />
          </div>
          <h2 className="text-2xl font-bold text-slate-900 dark:text-white">Que bom ter você aqui!</h2>
          <p className="text-slate-500 dark:text-slate-400 text-sm mt-2">Acesse sua conta para continuar</p>
        </div>

        <form onSubmit={handleLogin} className="space-y-4">
          <Input 
            type="email"
            placeholder="Seu e-mail"
            icon={<Mail className="w-4 h-4" />}
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
          <Input 
            type="password"
            placeholder="Sua senha"
            icon={<Lock className="w-4 h-4" />}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
          
          <Button type="submit" className="w-full mt-6" isLoading={loading}>
            Entrar
          </Button>
        </form>
        <p className="mt-8 text-center text-sm font-medium text-slate-600 dark:text-slate-400">
          Não possui uma conta? <Link to="/register" className="text-primary hover:text-primaryHover hover:underline transition-colors">Cadastre-se</Link>
        </p>
      </div>
    </div>
  );
};
