import React from 'react';
import { cn } from '../../utils/cn';
import { Loader2 } from 'lucide-react';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger';
  size?: 'sm' | 'md' | 'lg' | 'icon';
  isLoading?: boolean;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'primary', size = 'md', isLoading, children, disabled, ...props }, ref) => {

    const variants = {
      primary: 'bg-primary text-white hover:bg-primaryHover shadow-lg shadow-primary/25',
      secondary: 'bg-slate-200 dark:bg-slate-800 text-slate-900 dark:text-slate-100 hover:bg-slate-300 dark:hover:bg-slate-700',
      outline: 'border-2 border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800',
      ghost: 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 hover:text-slate-900 dark:hover:text-slate-100',
      danger: 'bg-red-600/90 text-white hover:bg-red-500 shadow-lg shadow-red-500/20',
    };

    const sizes = {
      sm: 'h-8 px-3 text-sm',
      md: 'h-10 px-4 py-2',
      lg: 'h-12 px-8 text-lg font-medium',
      icon: 'h-10 w-10 flex items-center justify-center p-0',
    };

    return (
      <button
        ref={ref}
        disabled={disabled || isLoading}
        className={cn(
          'inline-flex items-center justify-center rounded-md font-medium transition-all duration-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50 disabled:pointer-events-none disabled:opacity-50',
          variants[variant],
          sizes[size],
          className
        )}
        {...props}
      >
        {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
        {children}
      </button>
    );
  }
);
Button.displayName = 'Button';
