import { useState } from "react";
import { CheckCircle2, XCircle, Info, Copy } from "lucide-react";

interface TokenCardProps {
  type: 'id_token' | 'access_token' | 'refresh_token';
  token: string;
  sessionBinding?: string;
  status: 'valid' | 'expired' | 'invalid';
}

function HolographicTokenCard({ type, token, sessionBinding, status }: TokenCardProps) {
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 });

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const x = (e.clientX - rect.left) / rect.width - 0.5;
    const y = (e.clientY - rect.top) / rect.height - 0.5;
    setMousePos({ x, y });
  };

  const getStatusColor = () => {
    if (status === 'valid') return 'var(--success)';
    if (status === 'expired') return 'var(--warning)';
    return 'var(--error)';
  };

  return (
    <div 
      className={`relative w-[400px] h-[250px] rounded-[20px] p-6 transition-transform duration-200 ease-out preserve-3d group cursor-pointer overflow-hidden backdrop-blur-md border`}
      onMouseMove={handleMouseMove}
      style={{
        transform: `perspective(1000px) rotateX(${mousePos.y * -15}deg) rotateY(${mousePos.x * 15}deg) scale(1.02)`,
        background: `linear-gradient(135deg, rgba(0, 212, 255, 0.15) 0%, rgba(168, 85, 247, 0.15) 50%, rgba(236, 72, 153, 0.15) 100%)`,
        borderColor: getStatusColor(),
        boxShadow: `0 10px 40px ${getStatusColor()}33, inset 0 0 20px rgba(255, 255, 255, 0.05)`
      }}
      onMouseLeave={() => setMousePos({ x: 0, y: 0 })}
    >
      <div className="absolute inset-[-50%] w-[200%] h-[200%] bg-[linear-gradient(45deg,transparent_30%,rgba(255,255,255,0.1)_50%,transparent_70%)] animate-[shimmer_3s_ease-in-out_infinite] pointer-events-none" />
      
      <div className="flex justify-between items-start mb-6 border-b border-glass-border pb-2 z-10 relative">
        <h3 className="font-display font-bold text-lg text-text-primary tracking-wide uppercase">
          {type.replace('_', ' ')}
        </h3>
        <div className="flex items-center gap-2 text-sm font-semibold" style={{ color: getStatusColor() }}>
          {status === 'valid' ? <CheckCircle2 className="w-5 h-5"/> : <XCircle className="w-5 h-5" />}
          <span className="uppercase">{status}</span>
        </div>
      </div>

      <div className="space-y-2 text-sm text-text-secondary z-10 relative">
        <div className="flex justify-between">
          <span>Subject:</span>
          <span className="text-text-primary font-mono">alice@example.com</span>
        </div>
        <div className="flex justify-between">
          <span>Issued:</span>
          <span className="text-text-primary">2 minutes ago</span>
        </div>
        <div className="flex justify-between mb-4">
          <span>Expires:</span>
          <span className="text-text-primary">In 58 minutes</span>
        </div>
      </div>

      <div className="mt-4 p-3 rounded-xl bg-bg-primary/50 border border-glass-border z-10 relative backdrop-blur-sm group-hover:bg-bg-primary/70 transition-colors">
        <div className="text-[10px] font-bold text-text-tertiary mb-1 tracking-wider">BINDING</div>
        <div className="flex justify-between items-center text-xs">
          <span className="text-text-secondary">Session:</span>
          <span className="text-accent-blue font-mono">{sessionBinding || 'abc-123-def'}</span>
        </div>
        <div className="flex justify-between items-center text-xs mt-1">
          <span className="text-text-secondary">Exporter:</span>
          <span className="text-accent-purple font-mono">ZjRhY2MxODM...</span>
        </div>
      </div>
    </div>
  );
}

export function TokenInspector() {
  return (
    <div className="h-full flex flex-col gap-6 items-center pt-8 overflow-y-auto">
      <div className="flex gap-8 justify-center mb-8">
        <HolographicTokenCard 
          type="id_token" 
          token="ey..." 
          status="valid"
        />
        <div className="flex flex-col gap-4 flex-1 max-w-[600px]">
          <div className="bg-bg-tertiary border border-glass-border rounded-xl p-4 overflow-hidden">
            <h4 className="text-xs font-bold text-text-tertiary tracking-wider mb-2">HEADER</h4>
            <pre className="text-xs font-mono text-text-secondary whitespace-pre-wrap"><span className="text-accent-blue">{"{"}</span>
  <span className="text-success">"alg"</span>: <span className="text-accent-purple">"ML-DSA-65"</span>,
  <span className="text-success">"typ"</span>: <span className="text-accent-purple">"JWT"</span>,
  <span className="text-success">"kid"</span>: <span className="text-accent-purple">"server-signing-key"</span>
<span className="text-accent-blue">{"}"}</span></pre>
          </div>
          
          <div className="bg-bg-tertiary border border-glass-border rounded-xl p-4 overflow-hidden relative">
            <h4 className="text-xs font-bold text-text-tertiary tracking-wider mb-2">PAYLOAD</h4>
            <pre className="text-xs font-mono text-text-secondary whitespace-pre-wrap"><span className="text-accent-blue">{"{"}</span>
  <span className="text-success">"iss"</span>: <span className="text-accent-purple">"https://auth.example.com"</span>,
  <span className="text-success">"sub"</span>: <span className="text-accent-purple">"alice@example.com"</span>,
  <span className="text-success">"aud"</span>: <span className="text-accent-purple">"api.example.com"</span>,
  <span className="text-success">"exp"</span>: <span className="text-warning">1704067200</span>,
  <span className="text-success">"cnf"</span>: <span className="text-accent-blue">{"{"}</span>
    <span className="text-success">"kmt"</span>: <span className="text-accent-purple">"kemtls-exporter-v1"</span>,
    <span className="text-success">"kbh"</span>: <span className="text-accent-purple">"ZjRhY2MxODM..."</span>
  <span className="text-accent-blue">{"}"}</span>
<span className="text-accent-blue">{"}"}</span></pre>
          </div>
          
          <div className="bg-bg-tertiary border border-glass-border rounded-xl p-4 overflow-hidden">
            <h4 className="text-xs font-bold text-text-tertiary tracking-wider mb-2">SIGNATURE</h4>
            <div className="text-xs font-mono text-text-secondary bg-bg-secondary p-2 rounded break-all border border-glass-border">
              [ ML-DSA-65 Signature - 3293 bytes ]
            </div>
            <div className="mt-2 flex items-center justify-between text-xs">
              <span className="text-text-tertiary">TOKEN SIZE: 7.8 KB</span>
              <span className="text-success font-semibold flex items-center gap-1"><CheckCircle2 className="w-4 h-4"/> Verification: Valid</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
