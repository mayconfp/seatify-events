import type { Seat } from '../../types';
import { cn } from '../../utils/cn';
import { Armchair } from 'lucide-react';

interface SeatMapProps {
  seats: Seat[];
  selectedSeats: string[];
  onSeatToggle: (seatNumber: string) => void;
}

export const SeatMap = ({ seats, selectedSeats, onSeatToggle }: SeatMapProps) => {
  // Sort seats: A1, A2, A3... A10
  const sortedSeats = [...seats].sort((a, b) => {
    const numA = parseInt(a.seat_number.replace(/\D/g, '')) || 0;
    const numB = parseInt(b.seat_number.replace(/\D/g, '')) || 0;
    const alphaA = a.seat_number.replace(/\d/g, '');
    const alphaB = b.seat_number.replace(/\d/g, '');
    if (alphaA === alphaB) return numA - numB;
    return alphaA.localeCompare(alphaB);
  });

  // Remove JS grouping to let CSS Grid handle responsive reflow naturally.

  return (
    <div className="w-full max-w-4xl mx-auto py-2">
      <div className="relative mb-6">
        {/* Tela Curvada (2D) */}
        <div className="relative w-full max-w-xl mx-auto h-12 bg-slate-200 dark:bg-slate-800/80 rounded-t-[100px] border-b-[4px] border-primary mb-12 flex items-center justify-center shadow-[0_15px_40px_rgba(79,70,229,0.2)] transition-colors duration-300 overflow-hidden">
          <span className="text-slate-500 dark:text-slate-400 font-black text-lg tracking-[0.4em] uppercase relative z-10">
            Tela
          </span>
          {/* Brilho da tela */}
          <div className="absolute inset-0 bg-gradient-to-t from-primary/20 to-transparent pointer-events-none" />
        </div>

        {/* Container sem scroll forçado, permitindo reflow do Grid */}
        <div className="w-full pb-8 px-2 md:px-4">
          {/* Cadeiras (Grid CSS Responsivo) */}
          <div className="grid grid-cols-6 sm:grid-cols-8 md:grid-cols-12 gap-3 md:gap-4 justify-items-center mx-auto max-w-fit">
            {sortedSeats.map((seat) => {
              const isSelected = selectedSeats.includes(seat.seat_number);
              const isAvailable = seat.status === 'AVAILABLE';

              return (
                <button
                  key={seat.id}
                  disabled={!isAvailable}
                  onClick={() => onSeatToggle(seat.seat_number)}
                  className={cn(
                    'w-10 h-12 md:w-12 md:h-14 rounded-t-xl rounded-b-md flex flex-col items-center justify-center transition-all duration-300 ease-out border-t-2 border-x-2 border-b-4 flex-shrink-0',
                    // AVAILABLE
                    isAvailable && !isSelected && 'bg-white dark:bg-slate-800 border-slate-300 border-b-slate-400 dark:border-slate-700 dark:border-b-slate-900 hover:bg-slate-100 dark:hover:bg-slate-700 hover:-translate-y-1 cursor-pointer shadow-[0_4px_10px_rgba(0,0,0,0.05)]',
                    // SELECTED
                    isSelected && 'bg-primary border-primary border-b-indigo-700 text-white shadow-[0_8px_20px_rgba(79,70,229,0.5)] transform -translate-y-1 scale-105 z-10',
                    // PENDING / RESERVED (DISABLED)
                    !isAvailable && 'bg-slate-100 dark:bg-slate-900/50 border-slate-200 border-b-slate-300 dark:border-slate-800 dark:border-b-slate-950 cursor-not-allowed opacity-50'
                  )}
                  title={`Assento ${seat.seat_number} - ${seat.status}`}
                >
                  <span className={cn(
                    "text-[10px] md:text-[11px] font-black leading-none mb-1",
                    isSelected ? "text-white" : (!isAvailable ? "text-slate-500 dark:text-slate-500" : "text-slate-700 dark:text-slate-200")
                  )}>
                    {seat.seat_number}
                  </span>
                  <Armchair className={cn(
                    "w-5 h-5 md:w-6 md:h-6",
                    isSelected ? "text-white" : (!isAvailable ? "text-slate-400 dark:text-slate-600" : "text-slate-400 dark:text-slate-400")
                  )} />
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* Legenda */}
      <div className="flex items-center justify-center gap-6 mt-16 text-sm font-medium text-slate-600 dark:text-slate-400">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 shadow-sm" />
          <span>Disponível</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded bg-primary border border-primary shadow-[0_0_10px_rgba(79,70,229,0.5)]" />
          <span>Selecionado</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded bg-slate-100 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-800 opacity-50" />
          <span>Ocupado</span>
        </div>
      </div>
    </div>
  );
};
