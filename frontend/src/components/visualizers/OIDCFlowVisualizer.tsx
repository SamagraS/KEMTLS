import { User, Server, Database, ArrowRight } from "lucide-react";
import React from "react";

export function OIDCFlowVisualizer() {
  return (
    <div className="h-full flex flex-col items-center justify-center p-8 overflow-y-auto w-full min-w-max">
      
      <div className="flex gap-20 mb-12">
        <Node icon={User} label="CLIENT" />
        <Node icon={Server} label="AUTH SERVER" color="border-accent-purple" />
        <Node icon={Database} label="RESOURCE SERVER" color="border-accent-green" />
      </div>

      <div className="flex flex-col gap-6 w-full max-w-4xl relative">
        <div className="absolute top-0 bottom-0 left-[88px] w-px bg-glass-border -z-10" />
        <div className="absolute top-0 bottom-0 left-[416px] w-px bg-glass-border -z-10" />
        <div className="absolute top-0 bottom-0 left-[744px] w-px bg-glass-border -z-10" />

        <Step 
          number={1}
          title="Authorization Request"
          source={0}
          target={1}
          code="GET /authorize\n+ PKCE"
        />

        <Step 
          number={2}
          title="User Authentication"
          source={1}
          target={1}
          message="Login ✓"
        />

        <Step 
          number={3}
          title="Authorization Code"
          source={1}
          target={0}
          message="code=abc12345"
          reverse
        />

        <Step 
          number={4}
          title="Token Exchange"
          source={0}
          target={1}
          code="POST /token\n+ pkce_verifier"
        />

        <Step 
          number={5}
          title="Tokens Issued"
          source={1}
          target={0}
          message="ID + Access + Refresh"
          reverse
        />

        <Step 
          number={6}
          title="Resource Access"
          source={0}
          target={2}
          code="GET /userinfo\n+ Bearer Token"
          extraInfo="Verify Token ✓\nVerify Session Binding ✓"
        />
        
        <Step 
          number={7}
          title="Resource Response"
          source={2}
          target={0}
          message="[UserInfo JSON]"
          reverse
        />
      </div>

    </div>
  );
}

function Node({ icon: Icon, label, color = "border-accent-blue" }: { icon: React.ElementType, label: string, color?: string }) {
  return (
    <div className="flex flex-col items-center gap-4 w-32">
      <div className={`w-16 h-16 rounded-2xl flex items-center justify-center border-2 bg-bg-secondary ${color} shadow-glow-blue`}>
        <Icon className="w-8 h-8 text-text-primary" />
      </div>
      <span className="font-display font-bold tracking-widest text-text-primary text-xs">{label}</span>
    </div>
  );
}

interface StepProps {
  number: number;
  title: string;
  source: number;
  target: number;
  code?: string;
  message?: string;
  extraInfo?: string;
  reverse?: boolean;
}

function Step({ number, title, source, target, code, message, extraInfo, reverse }: StepProps) {
  const colWidth = 328; 
  const startSpace = 88;
  const leftPos = startSpace + (Math.min(source, target) * colWidth);
  const width = Math.abs(target - source) * colWidth || 200;

  return (
    <div className="relative flex items-center group w-full mb-4">
      <div className="w-8 h-8 rounded-full bg-bg-primary border border-glass-border flex items-center justify-center text-xs font-bold text-text-secondary mr-4 z-10 shrink-0 shadow-glow-blue group-hover:border-accent-blue transition-colors">
        {number}
      </div>
      
      <div className="flex-1 text-sm font-semibold text-text-primary w-48 shrink-0 relative mr-4">
        {title}
      </div>

      <div className="relative h-12 flex-1 mt-6" style={{ width: width }}>
        {source !== target && (
          <div 
            className="absolute top-1/2 -translate-y-1/2 h-[2px] bg-accent-blue/50 group-hover:bg-accent-blue w-full flex items-center transition-colors"
            style={{ 
              left: `${leftPos - 220}px`, 
              width: `${width}px`,
              flexDirection: reverse ? 'row-reverse' : 'row'
            }}
          >
            <div className="h-full bg-accent-blue w-full animate-data-flow" />
            <ArrowRight className={`w-4 h-4 text-accent-blue absolute ${reverse ? '-left-1 rotate-180' : '-right-1'} -translate-y-1/2 top-1/2`} />
          </div>
        )}

        <div className="absolute -top-10 flex flex-col gap-1 items-center" style={{ left: `${leftPos - 220 + (width/2)}px`, transform: 'translateX(-50%)' }}>
          {code && (
            <div className="bg-bg-tertiary border border-glass-border px-3 py-1 rounded text-xs font-mono text-text-secondary whitespace-pre text-center">
              {code}
            </div>
          )}
          {message && (
            <div className={`px-2 py-0.5 rounded text-xs font-semibold ${reverse ? 'text-success bg-success/10 border border-success/30' : 'text-text-primary'}`}>
              {message}
            </div>
          )}
        </div>
        
        {extraInfo && (
           <div className="absolute top-4 flex flex-col gap-1 items-end" style={{ left: `${leftPos - 220 + width}px` }}>
             <div className="bg-success/10 border border-success/30 px-3 py-1 rounded text-xs font-mono text-success whitespace-pre text-right drop-shadow-glow-green">
               {extraInfo}
             </div>
           </div>
        )}
      </div>
    </div>
  );
}
