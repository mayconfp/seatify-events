import { useState, useEffect } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { api } from '../../api/axios';
import { Button } from '../../components/ui/Button';
import { CheckCircle2, Loader2, Ticket } from 'lucide-react';

// Numero de tentativas e intervalo entre elas ao aguardar o webhook do
// Stripe processar o pagamento e emitir o(s) ingresso(s) de forma assincrona.
// Estendido para 30s (15 tentativas x 2s) para acomodar atrasos de rede
// ou enfileiramento no processador de pagamento.
const POLL_ATTEMPTS = 15;
const POLL_INTERVAL_MS = 2000;

export const CheckoutSuccess = () => {
  const [searchParams] = useSearchParams();
  const sessionId = searchParams.get('session_id');
  const [ticketsReady, setTicketsReady] = useState(false);
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    let attempt = 0;
    let cancelled = false;

    const pollTickets = async () => {
      while (attempt < POLL_ATTEMPTS && !cancelled) {
        try {
          const response = await api.get<unknown[]>('/tickets/me');
          if (response.data.length > 0) {
            setTicketsReady(true);
            break;
          }
        } catch {
          // Ignora falhas de polling; tenta novamente ate esgotar as tentativas.
        }
        attempt += 1;
        await new Promise((resolve) => setTimeout(resolve, POLL_INTERVAL_MS));
      }
      if (!cancelled) setChecking(false);
    };

    pollTickets();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="container mx-auto px-4 py-20 max-w-lg text-center">
      <div className="glass-card rounded-2xl p-10">
        <CheckCircle2 className="w-16 h-16 text-green-500 mx-auto mb-6" />
        <h1 className="text-2xl font-bold text-zinc-900 dark:text-white mb-2">
          Pagamento aprovado!
        </h1>
        <p className="text-zinc-600 dark:text-zinc-400 mb-8">
          {checking
            ? 'Estamos confirmando seu pagamento e emitindo seu ingresso...'
            : ticketsReady
              ? 'Seu ingresso ja esta disponivel em Meus Ingressos.'
              : 'O pagamento foi confirmado. Seu ingresso pode levar alguns instantes para aparecer.'}
        </p>

        {sessionId && (
          <p className="text-xs text-zinc-400 dark:text-zinc-500 mb-6 break-all">
            Sessao: {sessionId}
          </p>
        )}

        {checking ? (
          <Loader2 className="w-8 h-8 text-primary animate-spin mx-auto mb-6" />
        ) : (
          <Link to="/tickets">
            <Button size="lg" className="w-full">
              <Ticket className="w-5 h-5 mr-2" />
              Ver Meus Ingressos
            </Button>
          </Link>
        )}
      </div>
    </div>
  );
};
