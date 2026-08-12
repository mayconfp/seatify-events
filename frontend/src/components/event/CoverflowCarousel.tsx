import { useState } from 'react';
import { ChevronLeft, ChevronRight, Star, User } from 'lucide-react';
import { Button } from '../ui/Button';
import type { TmdbMovie } from '../../types';

interface CoverflowCarouselProps {
  events: TmdbMovie[];
}

export const CoverflowCarousel = ({ events }: CoverflowCarouselProps) => {
  const [activeIndex, setActiveIndex] = useState(0);

  if (!events || events.length === 0) return null;

  const handleNext = () => {
    setActiveIndex((prev) => (prev + 1) % events.length);
  };

  const handlePrev = () => {
    setActiveIndex((prev) => (prev - 1 + events.length) % events.length);
  };

  const getCardStyles = (index: number) => {
    const total = events.length;
    // Calculate shortest distance in a circular array
    let offset = index - activeIndex;
    if (offset > Math.floor(total / 2)) offset -= total;
    if (offset < -Math.floor(total / 2)) offset += total;

    const absOffset = Math.abs(offset);
    
    // Visibility
    if (absOffset > 2) {
      return {
        display: 'none',
        opacity: 0,
        transform: 'translateX(0) scale(0) rotateY(0deg)',
        zIndex: -1,
      };
    }

    // Transformations
    const sign = Math.sign(offset);
    
    // Responsividade para evitar estouro horizontal e sobreposição excessiva no mobile
    const isMobile = typeof window !== 'undefined' && window.innerWidth < 768;
    const offsetPercentage = isMobile ? 65 : 60; // No mobile afasta mais (65%) para não sobrepor tanto o centro
    
    const translateX = sign * absOffset * offsetPercentage; // percentage
    const rotateY = sign * absOffset * -45; // degrees
    const scale = 1 - absOffset * 0.2;
    const zIndex = 50 - absOffset * 10;
    const opacity = 1 - absOffset * 0.3;

    return {
      transform: `translateX(${translateX}%) scale(${scale}) perspective(1000px) rotateY(${rotateY}deg)`,
      zIndex,
      opacity,
      display: 'block',
    };
  };

  return (
    <div className="relative w-full max-w-6xl mx-auto h-[480px] md:h-[580px] flex items-center justify-center overflow-hidden px-4 mb-16">
      
      {/* Cards Container (2:3 Aspect Ratio para posters de filme) */}
      <div className="relative w-full max-w-[280px] md:max-w-[360px] h-[420px] md:h-[540px] flex items-center justify-center [transform-style:preserve-3d]">
        {events.map((event, index) => {
          const style = getCardStyles(index);
          const isActive = index === activeIndex;

          return (
            <div
              key={event.id}
              className={`absolute top-0 left-0 w-full h-full rounded-2xl md:rounded-3xl shadow-2xl transition-all duration-700 ease-out cursor-pointer overflow-hidden bg-zinc-900 ${isActive ? 'shadow-black/60' : 'shadow-black/20'}`}
              style={style}
              onClick={() => {
                if (!isActive) setActiveIndex(index);
              }}
            >
              {/* Image */}
              {event.poster_path ? (
                <img
                  src={`https://image.tmdb.org/t/p/w780${event.poster_path}`}
                  alt={event.title}
                  className="absolute inset-0 w-full h-full object-cover"
                />
              ) : (
                <div className="absolute inset-0 w-full h-full bg-slate-800 flex items-center justify-center text-slate-500">
                  Sem Imagem
                </div>
              )}
              
              {/* Overlay */}
              <div className="absolute inset-0 bg-gradient-to-t from-zinc-950/90 via-zinc-900/40 to-transparent opacity-95" />

              {/* Content */}
              <div className={`absolute bottom-0 left-0 w-full p-6 md:p-8 text-left flex flex-col justify-end transition-opacity duration-500 ${isActive ? 'opacity-100' : 'opacity-0'}`}>
                {/* Badges: classification + genre */}
                <div className="flex items-center gap-2 mb-3">
                  {event.age_rating && (
                    <span className="px-2 py-0.5 text-[11px] font-black rounded-sm bg-yellow-400 text-zinc-900 uppercase">
                      {event.age_rating}
                    </span>
                  )}
                  {event.genres && event.genres.length > 0 && (
                    <span className="px-2 py-0.5 text-[11px] font-semibold rounded-sm bg-white/20 backdrop-blur-md text-white uppercase border border-white/10">
                      {event.genres[0]}
                    </span>
                  )}
                  <span className="px-2 py-0.5 text-[11px] font-bold rounded-full bg-primary/90 text-white uppercase tracking-wider">
                    Em Alta
                  </span>
                </div>

                <h3 className="text-2xl md:text-3xl font-extrabold text-white mb-2 drop-shadow-md leading-tight line-clamp-2">
                  {event.title}
                </h3>

                {/* Genres list */}
                {event.genres && event.genres.length > 1 && (
                  <p className="text-sm text-zinc-300 mb-3">{event.genres.join(' · ')}</p>
                )}

                <div className="flex flex-wrap items-center gap-4 mb-4 text-sm">
                  {/* Rating */}
                  {event.vote_average && (
                    <div className="flex items-center gap-1.5 text-yellow-400 font-bold">
                      <Star className="w-4 h-4 fill-yellow-400" />
                      <span>{event.vote_average.toFixed(1)}</span>
                      <span className="text-zinc-400 font-normal text-xs">/10</span>
                    </div>
                  )}
                  {/* Director */}
                  {event.director && (
                    <div className="flex items-center gap-1.5 text-zinc-300">
                      <User className="w-3.5 h-3.5 text-zinc-400" />
                      <span className="text-xs">{event.director}</span>
                    </div>
                  )}
                  {/* Release date */}
                  {event.release_date && (
                    <span className="text-zinc-400 text-xs">
                      {new Date(event.release_date).getFullYear()}
                    </span>
                  )}
                </div>

                {/* Cast mini-avatars */}
                {event.cast && event.cast.length > 0 && (
                  <div className="flex items-center gap-2 mb-5">
                    {event.cast.slice(0, 5).map((actor, i) => (
                      <div key={i} className="relative group/actor">
                        {actor.profile_path ? (
                          <img
                            src={`https://image.tmdb.org/t/p/w185${actor.profile_path}`}
                            alt={actor.name}
                            className="w-8 h-8 rounded-full object-cover border-2 border-white/30 shadow"
                          />
                        ) : (
                          <div className="w-8 h-8 rounded-full bg-zinc-700 border-2 border-white/20 flex items-center justify-center text-[10px] text-zinc-400">
                            {actor.name[0]}
                          </div>
                        )}
                      </div>
                    ))}
                    <span className="text-xs text-zinc-400 ml-1">
                      {event.cast.slice(0, 3).map(a => a.name.split(' ')[0]).join(', ')}{event.cast.length > 3 ? '...' : ''}
                    </span>
                  </div>
                )}

                <div className="flex items-center gap-3 w-full">
                  <Button variant="primary" className="flex-1 text-sm h-11 rounded-xl bg-white text-zinc-900 hover:bg-zinc-100 font-bold">
                    Em Breve
                  </Button>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Navigation Buttons */}
      <button 
        onClick={handlePrev}
        className="absolute left-2 md:left-10 z-[60] w-12 h-12 flex items-center justify-center rounded-full bg-black/40 hover:bg-black/60 text-white backdrop-blur-md border border-white/10 transition-all hover:scale-110"
        aria-label="Anterior"
      >
        <ChevronLeft className="w-8 h-8" />
      </button>
      <button 
        onClick={handleNext}
        className="absolute right-2 md:right-10 z-[60] w-12 h-12 flex items-center justify-center rounded-full bg-black/40 hover:bg-black/60 text-white backdrop-blur-md border border-white/10 transition-all hover:scale-110"
        aria-label="Próximo"
      >
        <ChevronRight className="w-8 h-8" />
      </button>

    </div>
  );
};
