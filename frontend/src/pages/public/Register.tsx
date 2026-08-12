import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { api } from '../../api/axios';
import { Button } from '../../components/ui/Button';
import { Input } from '../../components/ui/Input';
import { Mail, Lock, User, Ticket, X } from 'lucide-react';
import { toast } from 'sonner';

export const Register = () => {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      await api.post('/auth/register', {
        name,
        email,
        password,
        role: 'CLIENT'
      });
      
      toast.success('Conta criada com sucesso! Faça login.');
      navigate('/login');
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Erro ao criar conta.');
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
          <h2 className="text-2xl font-bold text-slate-900 dark:text-white">Criar Conta</h2>
          <p className="text-slate-500 dark:text-slate-400 text-sm mt-2">Junte-se à plataforma Eventify</p>
        </div>

        <form onSubmit={handleRegister} className="space-y-4">
          <Input 
            type="text"
            placeholder="Seu nome completo"
            icon={<User className="w-4 h-4" />}
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
          />
          <Input 
            type="email"
            placeholder="Seu e-mail"
            icon={<Mail className="w-4 h-4" />}
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
          <div>
            <Input 
              type="password"
              placeholder="Sua senha"
              icon={<Lock className="w-4 h-4" />}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 ml-1">Mínimo de 8 caracteres.</p>
          </div>
          
          <Button type="submit" className="w-full mt-6" isLoading={loading}>
            Cadastrar
          </Button>
        </form>

        <p className="mt-8 text-center text-sm font-medium text-slate-600 dark:text-slate-400">
          Já tem uma conta? <Link to="/login" className="text-primary hover:text-primaryHover hover:underline transition-colors">Entre aqui</Link>
        </p>
      </div>
    </div>
  );
};
