import { useState, useEffect } from 'react';
import { api } from '../../api/axios';
import type { Ticket as TicketType } from '../../types';
import { TicketCard } from '../../components/event/TicketCard';
import { Loader2, Ticket } from 'lucide-react';
import { toast } from 'sonner';
import { Link, useNavigate } from 'react-router-dom';
import { Button } from '../../components/ui/Button';
import { useAuthStore } from '../../store/authStore';

export const MyTickets = () => {
  const [tickets, setTickets] = useState<TicketType[]>([]);
  const [loading, setLoading] = useState(true);
  const { user } = useAuthStore();
  const navigate = useNavigate();

  useEffect(() => {
    if (!user) {
      navigate('/login');
      return;
    }

    const fetchTickets = async () => {
      try {
        const response = await api.get<TicketType[]>('/tickets/me');
        setTickets(response.data);
      } catch (error: any) {
        if (error.response?.status !== 401) {
          toast.error('Não foi possível carregar seus ingressos.');
        }
      } finally {
        setLoading(false);
      }
    };
    fetchTickets();
  }, [user, navigate]);

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <Loader2 className="w-10 h-10 text-primary animate-spin" />
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-12">
      <div className="flex items-center gap-3 mb-10 transition-colors duration-300">
        <Ticket className="w-8 h-8 text-primary" />
        <h1 className="text-3xl font-bold text-slate-900 dark:text-white">Meus Ingressos</h1>
      </div>

      {tickets.length === 0 ? (
        <div className="glass-card rounded-2xl p-12 text-center max-w-2xl mx-auto mt-10 transition-colors duration-300">
          <Ticket className="w-16 h-16 text-slate-400 dark:text-slate-600 mx-auto mb-6" />
          <h2 className="text-2xl font-bold text-slate-900 dark:text-white mb-4">Você ainda não tem ingressos</h2>
          <p className="text-slate-600 dark:text-slate-400 mb-8">
            Explore nossos eventos e garanta seu lugar nas melhores experiências.
          </p>
          <Link to="/">
            <Button size="lg">Explorar Eventos</Button>
          </Link>
        </div>
      ) : (
        <div className="space-y-8">
          {tickets.map(ticket => (
            <TicketCard key={ticket.id} ticket={ticket} />
          ))}
        </div>
      )}
    </div>
  );
};
