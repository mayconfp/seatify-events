import { useState, useEffect } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import { api } from '../../api/axios';
import type { Event } from '../../types';
import { Button } from '../../components/ui/Button';
import { Timer, CreditCard, Loader2 } from 'lucide-react';
import { toast } from 'sonner';

export const Checkout = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const selectedSeats = location.state?.selectedSeats as string[] || [];

  const [event, setEvent] = useState<Event | null>(null);
  const [timeLeft, setTimeLeft] = useState(15 * 60); // 15 minutes in seconds
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);

  useEffect(() => {
    if (selectedSeats.length === 0) {
      toast.error('Nenhum assento selecionado para checkout.');
      navigate(`/events/${id}`);
      return;
    }

    const fetchEvent = async () => {
      try {
        const response = await api.get<Event>(`/events/${id}`);
        setEvent(response.data);
      } catch (error) {
        toast.error('Erro ao carregar dados do evento.');
        navigate('/');
      } finally {
        setLoading(false);
      }
    };
    fetchEvent();
  }, [id, selectedSeats, navigate]);

  useEffect(() => {
    if (timeLeft <= 0) {
      toast.error('Tempo de reserva expirado. Os assentos foram liberados.');
      navigate(`/events/${id}`);
      return;
    }

    const timer = setInterval(() => {
      setTimeLeft(prev => prev - 1);
    }, 1000);

    return () => clearInterval(timer);
  }, [timeLeft, navigate, id]);

  const formatTime = (seconds: number) => {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  const handleSimulatePayment = async (simulateFailure: boolean = false) => {
    setProcessing(true);
    try {
      await api.post('/checkout/simulate', {
        event_id: id,
        seat_numbers: selectedSeats,
        simulate_failure: simulateFailure
      });

      if (simulateFailure) {
        toast.error('Pagamento recusado. Tente novamente.');
      } else {
        toast.success('Pagamento aprovado! Seus ingressos foram gerados.');
        navigate('/tickets');
      }
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Erro ao processar pagamento.');
    } finally {
      setProcessing(false);
    }
  };

  const handleStripeCheckout = async () => {
    setProcessing(true);
    try {
      const response = await api.post('/checkout/create-session', {
        event_id: id,
        seat_numbers: selectedSeats
      });
      // Redirect to Stripe Checkout URL
      window.location.href = response.data.checkout_url;
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Erro ao iniciar sessão do Stripe.');
      setProcessing(false);
    }
  };

  if (loading || !event) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <Loader2 className="w-10 h-10 text-primary animate-spin" />
      </div>
    );
  }

  const subtotal = selectedSeats.length * event.price;

  return (
    <div className="container mx-auto px-4 py-12 max-w-4xl">
      <div className="flex flex-col items-center mb-10">
        <h1 className="text-3xl font-bold text-zinc-900 dark:text-white mb-2">Checkout</h1>
        <div className="flex items-center gap-2 text-red-400 bg-red-400/10 px-4 py-2 rounded-full border border-red-400/20">
          <Timer className="w-5 h-5" />
          <span className="font-mono font-bold text-lg">{formatTime(timeLeft)}</span>
          <span className="text-sm ml-1">para concluir</span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        {/* Resumo do Pedido */}
        <div className="glass-card p-6 rounded-2xl h-fit">
          <h2 className="text-xl font-bold text-zinc-900 dark:text-white mb-6 border-b border-zinc-200 dark:border-zinc-800 pb-4">Resumo do Pedido</h2>

          <div className="flex gap-4 mb-6">
            {event.poster_url && (
              <img
                src={`https://image.tmdb.org/t/p/w200${event.poster_url}`}
                alt={event.title}
                className="w-20 h-28 object-cover rounded-lg"
              />
            )}
            <div>
              <h3 className="font-bold text-lg text-zinc-900 dark:text-white">{event.title}</h3>
              <p className="text-sm text-zinc-500 dark:text-zinc-400">{event.venue_name}</p>
            </div>
          </div>

          <div className="space-y-3 mb-6 border-t border-zinc-200 dark:border-zinc-800 pt-4">
            <div className="flex justify-between text-zinc-600 dark:text-zinc-400">
              <span>Assentos Selecionados ({selectedSeats.length})</span>
              <span className="font-medium text-zinc-900 dark:text-white">{selectedSeats.join(', ')}</span>
            </div>
            <div className="flex justify-between text-zinc-600 dark:text-zinc-400">
              <span>Preço unitário</span>
              <span>R$ {Number(event.price).toFixed(2).replace('.', ',')}</span>
            </div>
          </div>

          <div className="flex justify-between items-end border-t border-zinc-200 dark:border-zinc-800 pt-4">
            <span className="text-zinc-600 dark:text-zinc-400">Total a Pagar</span>
            <span className="text-3xl font-bold text-primary">
              R$ {Number(subtotal).toFixed(2).replace('.', ',')}
            </span>
          </div>
        </div>

        {/* Opções de Pagamento */}
        <div className="space-y-6">
          <div className="glass-card p-6 rounded-2xl">
            <h2 className="text-xl font-bold text-zinc-900 dark:text-white mb-4 flex items-center gap-2">
              <CreditCard className="text-primary" />
              Pagamento
            </h2>

            <div className="space-y-4">
              <Button
                className="w-full h-14 text-lg bg-[#635BFF] hover:bg-[#534be8] shadow-lg shadow-[#635BFF]/20"
                onClick={handleStripeCheckout}
                isLoading={processing}
              >
                Pagar com Stripe
              </Button>

              <div className="relative py-4 flex items-center">
                <div className="flex-grow border-t border-zinc-200 dark:border-zinc-800"></div>
                <span className="flex-shrink-0 mx-4 text-zinc-400 text-sm">Ou modo desenvolvedor</span>
                <div className="flex-grow border-t border-zinc-200 dark:border-zinc-800"></div>
              </div>

              <div className="flex gap-4">
                <Button
                  variant="outline"
                  className="w-full border-green-500/50 text-green-400 hover:bg-green-500/10"
                  onClick={() => handleSimulatePayment(false)}
                  disabled={processing}
                >
                  Simular Sucesso
                </Button>
                <Button
                  variant="outline"
                  className="w-full border-red-500/50 text-red-400 hover:bg-red-500/10"
                  onClick={() => handleSimulatePayment(true)}
                  disabled={processing}
                >
                  Simular Falha
                </Button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
