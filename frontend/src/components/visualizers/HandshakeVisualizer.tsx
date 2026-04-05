import { useState, useEffect } from "react";
import { Server, MonitorSmartphone, Shield, CheckCircle } from "lucide-react";

interface HandshakeVisualizerProps {
  mode: 'baseline' | 'pdk' | 'auto';
  autoPlay: boolean;
  speed: number;
  showDetails: boolean;
}

export function HandshakeVisualizer({ mode, autoPlay, speed, showDetails }: HandshakeVisualizerProps) {
  const [step, setStep] = useState(0);

  useEffect(() => {
    if (!autoPlay) return;
    const timer = setInterval(() => {
      setStep(s => (s >= 5 ? 0 : s + 1));
    }, 1500 / speed);
    return () => clearInterval(timer);
  }, [autoPlay, speed]);

  return (
    <div className="w-full h-full flex flex-col pt-8">
      <div className="flex-1 relative flex items-center justify-between px-24">
        
        {/* Client Node */}
        <div className="relative text-center z-10">
          <div className={`w-24 h-24 rounded-2xl flex items-center justify-center border-2 mb-4 bg-bg-secondary transition-all duration-slower
            ${step >= 0 ? 'border-accent-blue shadow-glow-blue' : 'border-glass-border'}
            ${step === 4 || step === 5 ? 'border-success shadow-glow-green' : ''}
          `}>
            <MonitorSmartphone className={`w-10 h-10 ${step >= 0 ? 'text-accent-blue' : 'text-text-secondary'}`} />
          </div>
          <div className="font-display font-medium text-text-primary text-lg tracking-wide">CLIENT</div>
        </div>

        {/* Connection Line */}
        <div className="absolute inset-x-24 top-1/2 -translate-y-1/2 h-1 bg-glass-border z-0" />
        
        {/* Encrypted Tunnel Active State */}
        {step >= 5 && (
          <div className="absolute inset-x-24 top-1/2 -translate-y-[2px] h-1 bg-accent-blue shadow-glow-blue z-0 animate-pulse" />
        )}

        {/* Server Node */}
        <div className="relative text-center z-10">
          <div className={`w-24 h-24 rounded-2xl flex items-center justify-center border-2 mb-4 bg-bg-secondary transition-all duration-slower
            ${step >= 0 ? 'border-accent-purple shadow-glow-purple' : 'border-glass-border'}
            ${step === 4 || step === 5 ? 'border-success shadow-glow-green' : ''}
          `}>
            <Server className={`w-10 h-10 ${step >= 0 ? 'text-accent-purple' : 'text-text-secondary'}`} />
          </div>
          <div className="font-display font-medium text-text-primary text-lg tracking-wide">AUTH SERVER</div>
        </div>

        {/* Packets */}
        {step === 1 && (
          <div className="absolute top-1/2 -translate-y-1/2 left-48 animate-[packetMoveRight_1.5s_ease-in-out_forwards]">
            <div className="w-4 h-4 rounded-full bg-accent-blue shadow-glow-blue" />
            <div className="absolute top-6 left-1/2 -translate-x-1/2 text-xs font-mono whitespace-nowrap text-text-secondary">ClientHello</div>
          </div>
        )}
        
        {step === 2 && (
          <div className="absolute top-1/2 -translate-y-1/2 right-48 animate-[packetMoveLeft_1.5s_ease-in-out_forwards]">
            <div className="w-5 h-5 rounded-sm bg-accent-purple shadow-glow-purple transform rotate-45" />
            <div className="absolute top-8 left-1/2 -translate-x-1/2 text-xs font-mono whitespace-nowrap text-text-secondary flex flex-col items-center">
              <div>ServerHello</div>
              <div className="text-[10px] text-accent-purple">+ {mode === 'pdk' ? 'PDK ID' : 'Cert'}</div>
            </div>
          </div>
        )}

        {step === 3 && (
          <div className="absolute top-1/2 -translate-y-1/2 left-48 animate-[packetMoveRight_1.5s_ease-in-out_forwards]">
            <div className="flex gap-1">
              <div className="w-3 h-3 rounded-full bg-accent-blue shadow-glow-blue" />
              <div className="w-3 h-3 rounded-full bg-accent-blue shadow-glow-blue" />
            </div>
            <div className="absolute top-6 left-1/2 -translate-x-1/2 text-xs font-mono whitespace-nowrap text-text-secondary flex flex-col items-center">
              <div>ClientKeyExchange</div>
              <div className="text-[10px] text-accent-cyan">ct_eph + ct_lt</div>
            </div>
          </div>
        )}

        {step === 4 && (
          <>
            <div className="absolute top-1/2 -translate-y-1/2 right-48 animate-[packetMoveLeft_1.5s_ease-in-out_forwards]">
              <div className="w-4 h-4 rounded-full bg-success shadow-glow-green" />
            </div>
            <div className="absolute top-1/2 -translate-y-1/2 left-48 animate-[packetMoveRight_1.5s_ease-in-out_forwards]">
              <div className="w-4 h-4 rounded-full bg-success shadow-glow-green" />
              <div className="absolute top-6 left-1/2 -translate-x-1/2 text-xs font-mono whitespace-nowrap text-text-secondary">Finished</div>
            </div>
          </>
        )}

      </div>
      
      {/* Timeline Scrubber */}
      <div className="mt-8 px-8">
        <div className="flex justify-between items-center mb-2">
          {["Idle", "ClientHello", "ServerHello", "KeyExchange", "Finished", "Session Established"].map((label, i) => (
            <button 
              key={i} 
              onClick={() => setStep(i)}
              className={`text-xs font-mono transition-colors ${step === i ? 'text-accent-blue font-bold' : 'text-text-tertiary hover:text-text-secondary'}`}
            >
              {label}
            </button>
          ))}
        </div>
        <div className="h-1 bg-glass-border rounded-full relative overflow-hidden">
          <div 
            className="absolute top-0 left-0 bottom-0 bg-accent-blue transition-all duration-300"
            style={{ width: `${(step / 5) * 100}%` }}
          />
        </div>
      </div>

      {step >= 5 && (
         <div className="mt-12 mx-auto text-center animate-in slide-in-from-bottom-4 fade-in">
           <div className="inline-flex items-center gap-2 px-6 py-2 rounded-full border border-success/30 bg-success/10 text-success text-sm font-semibold mb-2">
             <CheckCircle className="w-4 h-4" /> KEMTLS Handshake Complete
           </div>
           <div className="text-sm font-mono text-text-secondary">Session ID: <span className="text-accent-blue">abc-123-def</span> | Mode: <span className="uppercase">{mode}</span></div>
         </div>
      )}
    </div>
  );
}
