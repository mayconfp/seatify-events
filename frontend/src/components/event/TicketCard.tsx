import type { Ticket as TicketType } from '../../types';
import { QRCodeSVG } from 'qrcode.react';
import { format } from 'date-fns';
import { ptBR } from 'date-fns/locale';
import { Share2, MapPin, Calendar, CheckCircle2, AlertCircle } from 'lucide-react';
import { Button } from '../ui/Button';
import { toast } from 'sonner';

export const TicketCard = ({ ticket }: { ticket: TicketType }) => {
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

  const isValid = ticket.status === 'VALID';
  const isUsed = ticket.status === 'USED';

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
            <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">Comprador</p>
            <p className="text-sm font-medium text-slate-700 dark:text-slate-300 truncate max-w-[200px]">{ticket.client_id}</p>
          </div>
          <div className="text-right">
            <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">Preço</p>
            <p className="text-lg font-bold text-slate-900 dark:text-slate-100">R$ {Number(event.price || 0).toFixed(2).replace('.', ',')}</p>
          </div>
        </div>
      </div>

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
