import { useState } from 'react';
import type { Ticket as TicketType } from '../../types';
import { api } from '../../api/axios';
import { QRCodeSVG } from 'qrcode.react';
import { format } from 'date-fns';
import { ptBR } from 'date-fns/locale';
import { Share2, MapPin, Calendar, CheckCircle2, AlertCircle } from 'lucide-react';
import { Button } from '../ui/Button';
import { toast } from 'sonner';

export const TicketCard = ({ ticket }: { ticket: TicketType }) => {
  const [isRefunding, setIsRefunding] = useState(false);
  const [showConfirmModal, setShowConfirmModal] = useState(false);
  const [localStatus, setLocalStatus] = useState(ticket.status);
  const event = ticket.event;
  const seat = ticket.seat;

  const handleShare = () => {
    const shareUrl = `${window.location.origin}/tickets/shared/${ticket.share_link_hash}`;
    navigator.clipboard.writeText(shareUrl);
    toast.success('Link copiado com sucesso!', {
      description: 'Agora você pode enviar este ingresso para seu amigo.'
    });
  };

  if (!event) return null;

  const isValid = localStatus === 'VALID';
  const isUsed = localStatus === 'USED';
  
  // Regra de 2 horas
  const isRefundable = isValid && (new Date(event.event_date).getTime() - new Date().getTime() > 2 * 60 * 60 * 1000);

  const handleRefundClick = () => {
    setShowConfirmModal(true);
  };

  const confirmRefund = async () => {
    setShowConfirmModal(false);
    setIsRefunding(true);
    try {
      await api.post(`/tickets/${ticket.id}/refund`);
      toast.success('Solicitação enviada!', {
        description: 'O estorno cairá na sua fatura e o ingresso será cancelado em instantes.'
      });
      setLocalStatus('CANCELLED');
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Erro ao solicitar reembolso');
    } finally {
      setIsRefunding(false);
    }
  };

  return (
    <div className="flex flex-col md:flex-row w-full max-w-3xl mx-auto bg-white dark:bg-slate-900 rounded-xl overflow-hidden shadow-2xl relative transition-colors duration-300">
      {/* Ticket Body */}
      <div className="flex-1 p-6 md:p-8 flex flex-col justify-between relative border-r-2 border-dashed border-slate-200 dark:border-slate-800">
        <div className="absolute -top-4 -right-4 w-8 h-8 bg-slate-50 dark:bg-background rounded-full transition-colors duration-300" />
        <div className="absolute -bottom-4 -right-4 w-8 h-8 bg-slate-50 dark:bg-background rounded-full transition-colors duration-300" />

        <div>
          <div className="flex items-center justify-between mb-6">
            <div className="inline-flex items-center px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300">
              Ingresso VIP
            </div>

            <div className="flex items-center gap-2">
              {isValid ? (
                <span className="flex items-center gap-1 text-green-400 text-sm font-semibold">
                  <CheckCircle2 className="w-4 h-4" /> Válido
                </span>
              ) : isUsed ? (
                <span className="flex items-center gap-1 text-yellow-500 text-sm font-semibold">
                  <AlertCircle className="w-4 h-4" /> Utilizado
                </span>
              ) : (
                <span className="flex items-center gap-1 text-red-600 dark:text-red-400 text-sm font-semibold">
                  <AlertCircle className="w-4 h-4" /> Cancelado
                </span>
              )}
            </div>
          </div>

          <h2 className="text-3xl font-bold text-slate-900 dark:text-white mb-2 leading-tight">{event.title}</h2>

          <div className="space-y-4 mt-8">
            <div className="flex items-start gap-3 text-slate-600 dark:text-slate-300">
              <Calendar className="w-5 h-5 text-primary shrink-0 mt-0.5" />
              <div>
                <p className="text-sm font-medium">{format(new Date(event.event_date), "EEEE, dd 'de' MMMM", { locale: ptBR })}</p>
                <p className="text-xs text-slate-500 dark:text-slate-400">às {format(new Date(event.event_date), "HH:mm")}</p>
              </div>
            </div>

            <div className="flex items-start gap-3 text-slate-600 dark:text-slate-300">
              <MapPin className="w-5 h-5 text-primary shrink-0 mt-0.5" />
              <div>
                <p className="font-medium text-slate-900 dark:text-slate-200">{event.venue_name}</p>
              </div>
            </div>
          </div>
        </div>

        <div className="mt-8 pt-6 border-t border-slate-200 dark:border-slate-800 flex items-center justify-between">
          <div>
            <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">Assento</p>
            <p className="text-2xl font-black text-primary truncate max-w-[200px]">{ticket.seat_number}</p>
          </div>
          <div className="text-right flex flex-col items-end gap-2">
            <div>
              <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">Preço</p>
              <p className="text-lg font-bold text-slate-900 dark:text-slate-100">R$ {Number(event.price || 0).toFixed(2).replace('.', ',')}</p>
            </div>
            {isRefundable && (
              <Button 
                variant="outline" 
                size="sm" 
                className="text-red-500 border-red-200 hover:bg-red-50 dark:hover:bg-red-950/30 text-xs py-1 h-7"
                onClick={handleRefundClick}
                disabled={isRefunding}
              >
                {isRefunding ? 'Processando...' : 'Solicitar Reembolso'}
              </Button>
            )}
          </div>
        </div>
      </div>

      {/* Custom Confirm Modal */}
      {showConfirmModal && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="w-full max-w-sm bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-6 rounded-2xl shadow-2xl relative animate-in zoom-in-95 duration-200">
            <div className="flex items-center gap-3 mb-4 text-red-500">
              <AlertCircle className="w-6 h-6 shrink-0" />
              <h3 className="text-lg font-bold text-slate-900 dark:text-white">Confirmação de Reembolso</h3>
            </div>
            <p className="text-sm text-slate-600 dark:text-slate-300 mb-6">
              Tem certeza que deseja solicitar o reembolso? O valor será estornado na sua fatura e este ingresso será <strong>invalidado</strong> assim que o banco confirmar.
            </p>
            <div className="flex gap-3 justify-end">
              <Button 
                variant="outline" 
                onClick={() => setShowConfirmModal(false)}
                className="border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800"
              >
                Cancelar
              </Button>
              <Button 
                onClick={confirmRefund}
                className="bg-red-500 hover:bg-red-600 text-white border-0 shadow-lg shadow-red-500/20"
              >
                Sim, Reembolsar
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Ticket Stub (QR Code side) */}
      <div className="w-full md:w-64 bg-slate-800 p-6 md:p-8 flex flex-col items-center justify-center relative">
        <p className="text-xs text-slate-400 uppercase tracking-widest mb-4">Entrada</p>

        <div className={`p-3 bg-white rounded-xl mb-4 ${!isValid ? 'opacity-50 grayscale' : ''}`}>
          <QRCodeSVG
            value={ticket.qr_code_token}
            size={140}
            level="H"
          />
        </div>

        <div className="text-center mb-4">
          <p className="text-[10px] text-slate-400 uppercase tracking-widest mb-1">Código (Manual)</p>
          <p className="text-sm font-mono font-bold text-slate-200 tracking-wider bg-slate-900/50 px-3 py-1 rounded-md border border-slate-700">
            {ticket.share_link_hash}
          </p>
        </div>

        {seat && (
          <div className="text-center mb-6">
            <p className="text-xs text-slate-400 uppercase tracking-wider mb-1">Assento</p>
            <p className="text-3xl font-black text-primary">{seat.seat_number}</p>
          </div>
        )}

        <Button
          variant="outline"
          size="sm"
          className="w-full gap-2 border-slate-600 text-slate-300 hover:text-white hover:bg-slate-700 bg-transparent"
          onClick={handleShare}
        >
          <Share2 className="w-4 h-4" />
          Compartilhar
        </Button>
      </div>
    </div>
  );
};
