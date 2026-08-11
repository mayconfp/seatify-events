import { useEffect, useState } from 'react';
import { X, DollarSign, Users, Ticket, Activity } from 'lucide-react';
import { api } from '../../api/axios';
import type { EventAnalytics } from '../../types';
import { toast } from 'sonner';

interface EventAnalyticsModalProps {
  eventId: string;
  onClose: () => void;
}

export const EventAnalyticsModal = ({ eventId, onClose }: EventAnalyticsModalProps) => {
  const [analytics, setAnalytics] = useState<EventAnalytics | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchAnalytics = async () => {
      try {
        const response = await api.get<EventAnalytics>(`/events/${eventId}/analytics`);
        setAnalytics(response.data);
      } catch (error: any) {
        toast.error('Erro ao carregar relatório da sessão.');
        onClose();
      } finally {
        setLoading(false);
      }
    };

    fetchAnalytics();
  }, [eventId, onClose]);

  // Bloqueia scroll do body enquanto modal está aberto
  useEffect(() => {
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = 'unset';
    };
  }, []);

  const renderSeatMap = () => {
    if (!analytics) return null;

    const totalSeats = analytics.capacity;
    const occupied = new Set(analytics.occupied_seats);

    const seatSquares = [];
    for (let i = 1; i <= totalSeats; i++) {
      const seatNumber = `A${i}`;
      const isOccupied = occupied.has(seatNumber);
      seatSquares.push(
        <div
          key={seatNumber}
          title={seatNumber}
          className={`w-6 h-6 rounded-md text-[8px] flex items-center justify-center font-bold ${
            isOccupied
              ? 'bg-primary/20 text-primary border border-primary/50'
              : 'bg-zinc-200 dark:bg-zinc-800 text-zinc-400 border border-zinc-300 dark:border-zinc-700'
          }`}
        >
          {i}
        </div>
      );
    }

    return (
      <div className="mt-6 border-t border-zinc-200 dark:border-zinc-800 pt-6">
        <h4 className="text-sm font-bold text-zinc-900 dark:text-zinc-100 mb-4 flex items-center gap-2">
          <Activity className="w-4 h-4 text-primary" />
          Ocupação Visual (Sala)
        </h4>
        <div className="flex flex-wrap gap-1.5 justify-center max-h-60 overflow-y-auto custom-scrollbar p-2 bg-zinc-50 dark:bg-zinc-900/50 rounded-2xl border border-zinc-200 dark:border-zinc-800/80">
          {seatSquares}
        </div>
        <div className="flex items-center justify-center gap-6 mt-4 text-xs font-medium text-zinc-500">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded bg-zinc-200 dark:bg-zinc-800 border border-zinc-300 dark:border-zinc-700" />
            Livre
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded bg-primary/20 border border-primary/50" />
            Ocupado/Reservado
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
      
      <div className="relative w-full max-w-2xl bg-white dark:bg-zinc-950 rounded-3xl border border-zinc-200 dark:border-zinc-800 shadow-2xl overflow-hidden flex flex-col max-h-full animate-in zoom-in-95 duration-200">
        
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-zinc-200 dark:border-zinc-800">
          <div>
            <h3 className="text-xl font-bold text-zinc-900 dark:text-white">Relatório da Sessão</h3>
            {!loading && analytics && (
              <p className="text-sm text-zinc-500 font-medium mt-1">{analytics.title}</p>
            )}
          </div>
          <button
            onClick={onClose}
            className="w-10 h-10 flex items-center justify-center rounded-full bg-zinc-100 dark:bg-zinc-900 hover:bg-zinc-200 dark:hover:bg-zinc-800 text-zinc-500 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto">
          {loading ? (
            <div className="space-y-6 animate-pulse">
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                {[1, 2, 3].map(i => (
                  <div key={i} className="h-28 bg-zinc-100 dark:bg-zinc-900 rounded-2xl" />
                ))}
              </div>
              <div className="h-48 bg-zinc-100 dark:bg-zinc-900 rounded-2xl" />
            </div>
          ) : analytics ? (
            <div className="space-y-6">
              
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                {/* Receita */}
                <div className="bg-emerald-50 dark:bg-emerald-500/10 border border-emerald-200 dark:border-emerald-500/20 p-5 rounded-2xl">
                  <div className="flex items-center gap-2 text-emerald-600 dark:text-emerald-400 mb-2">
                    <DollarSign className="w-5 h-5" />
                    <span className="text-xs font-bold uppercase tracking-wider">Faturamento</span>
                  </div>
                  <div className="text-2xl font-black text-emerald-700 dark:text-emerald-300">
                    {new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(analytics.revenue)}
                  </div>
                </div>

                {/* Vendidos */}
                <div className="bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 p-5 rounded-2xl">
                  <div className="flex items-center gap-2 text-zinc-500 mb-2">
                    <Ticket className="w-5 h-5" />
                    <span className="text-xs font-bold uppercase tracking-wider">Vendidos</span>
                  </div>
                  <div className="text-2xl font-black text-zinc-900 dark:text-white">
                    {analytics.total_sold} <span className="text-sm font-medium text-zinc-500">/ {analytics.capacity}</span>
                  </div>
                </div>

                {/* Livres */}
                <div className="bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 p-5 rounded-2xl">
                  <div className="flex items-center gap-2 text-zinc-500 mb-2">
                    <Users className="w-5 h-5" />
                    <span className="text-xs font-bold uppercase tracking-wider">Livres</span>
                  </div>
                  <div className="text-2xl font-black text-zinc-900 dark:text-white">
                    {analytics.available_seats}
                  </div>
                </div>
              </div>

              {renderSeatMap()}

            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
};
