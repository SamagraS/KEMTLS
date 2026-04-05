import { Shield, Settings, BookOpen, User } from "lucide-react";

interface HeaderProps {
  currentMode: 'baseline' | 'pdk' | 'auto';
  onModeChange: (mode: 'baseline' | 'pdk' | 'auto') => void;
  connectionStatus: 'connected' | 'disconnected' | 'connecting';
}

export function Header({ currentMode, onModeChange, connectionStatus }: HeaderProps) {
  return (
    <header className="h-[60px] flex items-center justify-between px-6 border-b border-glass-border bg-bg-primary/80 backdrop-blur-md sticky top-0 z-50">
      <div className="flex items-center gap-8">
        <div className="flex items-center gap-2">
          <Shield className={`w-6 h-6 ${connectionStatus === 'connected' ? 'text-accent-blue drop-shadow-glow-blue' : 'text-text-secondary'}`} />
          <span className="font-display font-bold text-lg text-text-primary">KEMTLS</span>
        </div>
        
        <div className="flex items-center gap-2 bg-glass-bg rounded-lg p-1 border border-glass-border">
          {(['baseline', 'pdk', 'auto'] as const).map(mode => (
            <button
              key={mode}
              onClick={() => onModeChange(mode)}
              className={`
                px-4 py-1.5 rounded-md text-sm font-medium transition-all duration-normal
                ${currentMode === mode 
                  ? 'bg-accent-blue/10 border border-accent-blue text-accent-blue shadow-glow-blue' 
                  : 'bg-transparent border border-transparent text-text-secondary hover:-translate-y-[1px] hover:border-accent-blue/50'
                }
              `}
            >
              {mode.charAt(0).toUpperCase() + mode.slice(1)}
            </button>
          ))}
        </div>
      </div>

      <div className="flex items-center gap-4 text-text-secondary">
        <button className="p-2 hover:text-accent-blue transition-colors rounded-full hover:bg-glass-bg"><Settings className="w-5 h-5"/></button>
        <button className="p-2 hover:text-accent-blue transition-colors rounded-full hover:bg-glass-bg"><BookOpen className="w-5 h-5"/></button>
        <button className="p-2 hover:text-accent-blue transition-colors rounded-full hover:bg-glass-bg"><User className="w-5 h-5"/></button>
      </div>
    </header>
  );
}
