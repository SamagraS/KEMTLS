import { ShieldCheck, ShieldAlert } from "lucide-react";

export function SessionBindingDemo() {
  return (
    <div className="h-full flex flex-col items-center pt-8 overflow-y-auto w-full max-w-4xl mx-auto">
      <h2 className="text-xl font-display font-medium text-text-primary mb-12 tracking-wider">SESSION BINDING DEMONSTRATION</h2>
      
      <div className="grid grid-cols-2 gap-12 w-full mb-12">
        {/* Original Session */}
        <div className="flex flex-col">
          <div className="bg-bg-tertiary border border-glass-border p-6 rounded-2xl relative mb-8 shadow-glow-blue opacity-50 hover:opacity-100 transition-opacity">
            <h3 className="text-sm font-bold text-text-primary tracking-wider mb-4 flex items-center gap-2">
              <ShieldCheck className="w-5 h-5 text-success" />
              ORIGINAL SESSION
            </h3>
            <div className="space-y-3 font-mono text-sm">
              <div className="flex justify-between border-b border-glass-border pb-2">
                <span className="text-text-secondary">Session ID:</span>
                <span className="text-accent-blue">abc-123-def</span>
              </div>
              <div className="flex justify-between border-b border-glass-border pb-2">
                <span className="text-text-secondary">Binding:</span>
                <span className="text-accent-purple">ZjRhY2MxODM...</span>
              </div>
              <div className="flex justify-between">
                <span className="text-text-secondary">Status:</span>
                <span className="text-success flex items-center gap-1">Active</span>
              </div>
            </div>
          </div>
          
          <div className="flex flex-col items-center animate-[pulse_3s_ease-in-out_infinite]">
            <div className="h-16 w-1 bg-gradient-to-b from-success to-transparent relative">
              <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-4 h-4 bg-success rounded-full shadow-[0_0_10px_var(--success)]" />
            </div>
            <div className="bg-success/20 border border-success/50 text-success px-6 py-2 rounded-xl text-sm font-semibold mt-2">
              ✓ SUCCESS - Binding matches session
            </div>
          </div>
        </div>

        {/* Replay Session */}
        <div className="flex flex-col">
          <div className="bg-bg-tertiary border border-glass-border p-6 rounded-2xl relative mb-8 shadow-[0_0_30px_var(--error)_inset] opacity-50 hover:opacity-100 transition-opacity">
            <h3 className="text-sm font-bold text-text-primary tracking-wider mb-4 flex items-center gap-2">
              <ShieldAlert className="w-5 h-5 text-warning" />
              NEW SESSION (Replay)
            </h3>
            <div className="space-y-3 font-mono text-sm">
              <div className="flex justify-between border-b border-glass-border pb-2">
                <span className="text-text-secondary">Session ID:</span>
                <span className="text-warning">xyz-789-ghi</span>
              </div>
              <div className="flex justify-between border-b border-glass-border pb-2">
                <span className="text-text-secondary">Binding:</span>
                <span className="text-error">YWJjZGVmZ2hp...</span>
              </div>
              <div className="flex justify-between">
                <span className="text-text-secondary">Status:</span>
                <span className="text-warning flex items-center gap-1">Different</span>
              </div>
            </div>
          </div>
          
          <div className="flex flex-col items-center">
            <div className="h-16 w-1 bg-gradient-to-b from-error to-transparent relative truncate overflow-hidden">
              <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-4 h-4 bg-error rounded-full shadow-[0_0_10px_var(--error)]" />
            </div>
            <div className="bg-error/20 border border-error/50 text-error px-6 py-2 rounded-xl text-sm font-semibold mt-2 animate-bounce">
              ❌ BLOCKED - Binding mismatch detected!
            </div>
          </div>
        </div>
      </div>

      <div className="w-full bg-glass-bg border border-glass-border p-6 rounded-xl relative overflow-hidden backdrop-blur-md">
        <div className="absolute top-0 left-0 w-1 h-full bg-accent-blue" />
        <h4 className="font-bold text-sm tracking-wider text-text-primary mb-3">Why this matters:</h4>
        <ul className="list-disc list-inside space-y-2 text-sm text-text-secondary">
          <li>Prevents token theft and replay attacks</li>
          <li>Token is only valid on the original KEMTLS session it was issued over</li>
          <li>The exporter-derived binding is cryptographically unique per session</li>
        </ul>
      </div>
    </div>
  );
}
