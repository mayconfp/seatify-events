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

  // Group into rows of 12 (approximate for theater look)
  const rows = [];
  for (let i = 0; i < sortedSeats.length; i += 12) {
    rows.push(sortedSeats.slice(i, i + 12));
  }

  return (
    <div className="w-full max-w-4xl mx-auto py-2">
      {/* Container com perspectiva 3D */}
      <div style={{ perspective: '1000px' }} className="relative mb-6">
        {/* Tela Curvada */}
        <div 
          className="w-full max-w-xl mx-auto h-8 bg-slate-200 dark:bg-slate-800/80 rounded-t-[100%] border-b-[4px] border-primary mb-6 flex items-center justify-center shadow-[0_15px_40px_rgba(79,70,229,0.4)] transition-colors duration-300"
          style={{ transform: 'rotateX(50deg)', transformStyle: 'preserve-3d' }}
        >
          <span className="text-slate-500 dark:text-slate-400 font-black text-lg tracking-[0.4em] uppercase" style={{ transform: 'rotateX(-20deg) translateZ(15px)' }}>
            Tela
          </span>
          {/* Brilho da tela */}
          <div className="absolute inset-0 bg-gradient-to-t from-primary/20 to-transparent rounded-t-[100%] pointer-events-none" />
        </div>

        {/* Cadeiras (Arquibancada) */}
        <div 
          className="flex flex-col gap-8 items-center" 
          style={{ transform: 'rotateX(35deg)', transformStyle: 'preserve-3d' }}
        >
          {rows.map((row, rowIndex) => (
            <div 
              key={rowIndex} 
              className="flex gap-4 justify-center"
              style={{ 
                // Efeito de escada mais acentuado subindo no eixo Z e recuando no Y
                transform: `translateZ(${rowIndex * 35}px) translateY(-${rowIndex * 10}px)` 
              }}
            >
              {row.map((seat) => {
                const isSelected = selectedSeats.includes(seat.seat_number);
                const isAvailable = seat.status === 'AVAILABLE';

                return (
                  <button
                    key={seat.id}
                    disabled={!isAvailable}
                    onClick={() => onSeatToggle(seat.seat_number)}
                    className={cn(
                      'w-12 h-14 rounded-t-xl rounded-b-md flex flex-col items-center justify-center transition-all duration-300 ease-out border-t-2 border-x-2 border-b-4',
                      // AVAILABLE
                      isAvailable && !isSelected && 'bg-white dark:bg-slate-800 border-slate-300 border-b-slate-400 dark:border-slate-700 dark:border-b-slate-900 hover:bg-slate-100 dark:hover:bg-slate-700 hover:-translate-y-2 cursor-pointer shadow-[0_5px_15px_rgba(0,0,0,0.1)]',
                      // SELECTED
                      isSelected && 'bg-primary border-primary border-b-indigo-700 text-white shadow-[0_10px_25px_rgba(79,70,229,0.7)] transform -translate-y-3 scale-110 z-10',
                      // PENDING / RESERVED (DISABLED)
                      !isAvailable && 'bg-slate-100 dark:bg-slate-900/50 border-slate-200 border-b-slate-300 dark:border-slate-800 dark:border-b-slate-950 cursor-not-allowed opacity-50'
                    )}
                    title={`Assento ${seat.seat_number} - ${seat.status}`}
                    style={{
                      boxShadow: isSelected ? '0 15px 30px rgba(79,70,229,0.6)' : '0 8px 15px rgba(0,0,0,0.2)'
                    }}
                  >
                    <span className={cn(
                      "text-[11px] font-black leading-none mb-1",
                      isSelected ? "text-white" : (!isAvailable ? "text-slate-500 dark:text-slate-500" : "text-slate-700 dark:text-slate-200")
                    )}>
                      {seat.seat_number}
                    </span>
                    <Armchair className={cn(
                      "w-6 h-6",
                      isSelected ? "text-white" : (!isAvailable ? "text-slate-400 dark:text-slate-600" : "text-slate-400 dark:text-slate-400")
                    )} />
                  </button>
                );
              })}
            </div>
          ))}
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
