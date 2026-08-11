import { Link } from 'react-router-dom';
import { Button } from '../../components/ui/Button';
import { XCircle } from 'lucide-react';

export const CheckoutCancel = () => {
  return (
    <div className="container mx-auto px-4 py-20 max-w-lg text-center">
      <div className="glass-card rounded-2xl p-10">
        <XCircle className="w-16 h-16 text-red-500 mx-auto mb-6" />
        <h1 className="text-2xl font-bold text-zinc-900 dark:text-white mb-2">
          Pagamento cancelado
        </h1>
        <p className="text-zinc-600 dark:text-zinc-400 mb-8">
          Voce cancelou o pagamento. Seus assentos podem ter sido liberados apos
          o periodo de reserva expirar.
        </p>
        <Link to="/">
          <Button size="lg" className="w-full">
            Voltar para Eventos
          </Button>
        </Link>
      </div>
    </div>
  );
};
