import { Anchor } from 'lucide-react';

export default function Header() {
  return (
    <header className="gradient-header text-white px-3 py-2 md:px-6 md:py-4 flex items-center">
      <div className="flex items-center gap-2 md:gap-3">
        <div className="w-8 h-8 md:w-10 md:h-10 rounded-lg bg-white/15 backdrop-blur flex items-center justify-center">
          <Anchor className="w-5 h-5 md:w-6 md:h-6" />
        </div>
        <div>
          <h1 className="text-base md:text-lg font-bold tracking-tight leading-tight">
            Cargill Ocean Transportation
          </h1>
          <p className="text-sky-200 text-[10px] md:text-xs font-medium hidden sm:block">
            Voyage Optimization Platform
          </p>
        </div>
      </div>
    </header>
  );
}
