import { useState, useEffect, useRef } from 'react';

/* ═══════════════════════════════════════════
   PROTOCOL ACTIVITY ANIMATION
   Shows ONLY the 2 entities interacting.
   Much bigger, with labels on the connection line (not icons).
   ═══════════════════════════════════════════ */

interface ActivityEvent {
  id: string;
  from: 'client' | 'auth' | 'resource';
  to: 'client' | 'auth' | 'resource';
  label: string;
  detail: string;
  type: 'key' | 'cert' | 'token' | 'data' | 'verify';
  status: 'sending' | 'received' | 'idle';
}

interface ProtocolActivityProps {
  currentStepId: string | null;
  flowState: 'idle' | 'running' | 'done';
}

const ENTITY_META: Record<string, { label: string; icon: string; color: string }> = {
  client:   { label: 'CLIENT',          icon: '💻', color: 'var(--cyan)' },
  auth:     { label: 'AUTH SERVER',      icon: '🔐', color: 'var(--magenta)' },
  resource: { label: 'RESOURCE SERVER',  icon: '🗄️', color: 'var(--lime)' },
};

/* Which 2 entities interact at each step */
function getStepEntities(stepId: string): [string, string] {
  const map: Record<string, [string, string]> = {
    hello:           ['client', 'auth'],
    server:          ['client', 'auth'],
    derive:          ['client', 'auth'],
    finished:        ['client', 'auth'],
    authorize:       ['client', 'auth'],
    account_auth:    ['client', 'auth'],
    consent:         ['client', 'auth'],
    token_exchange:  ['client', 'auth'],
    session_bind:    ['client', 'auth'],
    resource_access: ['client', 'resource'],
  };
  return map[stepId] || ['client', 'auth'];
}

function getActivityEvents(stepId: string): ActivityEvent[] {
  const events: Record<string, ActivityEvent[]> = {
    hello: [
      { id: 'h1', from: 'client', to: 'auth', label: 'ClientHello', detail: 'ML-KEM-768 public key + cipher suites', type: 'key', status: 'idle' },
    ],
    server: [
      { id: 's1', from: 'auth', to: 'client', label: 'ServerHello', detail: 'ML-KEM-768 ciphertext + ML-DSA-65 cert', type: 'cert', status: 'idle' },
    ],
    derive: [
      { id: 'd1', from: 'client', to: 'auth', label: 'Key Derivation', detail: 'HKDF-SHA256 → shared secrets', type: 'key', status: 'idle' },
      { id: 'd2', from: 'auth', to: 'client', label: 'Key Confirmation', detail: 'Derived keys verified', type: 'verify', status: 'idle' },
    ],
    finished: [
      { id: 'f1', from: 'client', to: 'auth', label: 'Finished', detail: 'Handshake MAC verification', type: 'verify', status: 'idle' },
      { id: 'f2', from: 'auth', to: 'client', label: 'Finished', detail: 'Server MAC verification', type: 'verify', status: 'idle' },
    ],
    authorize: [
      { id: 'az1', from: 'client', to: 'auth', label: 'GET /authorize', detail: 'response_type=code&scope=openid&PKCE', type: 'data', status: 'idle' },
      { id: 'az2', from: 'auth', to: 'client', label: 'Redirect', detail: '302 → accounts.google.com', type: 'data', status: 'idle' },
    ],
    account_auth: [
      { id: 'aa1', from: 'client', to: 'auth', label: 'Authenticate', detail: 'User selects account at IdP', type: 'verify', status: 'idle' },
      { id: 'aa2', from: 'auth', to: 'client', label: 'Auth OK', detail: 'Session verified + MFA passed', type: 'verify', status: 'idle' },
    ],
    consent: [
      { id: 'cn1', from: 'client', to: 'auth', label: 'Grant Consent', detail: 'User approves scopes', type: 'data', status: 'idle' },
      { id: 'cn2', from: 'auth', to: 'client', label: 'Auth Code', detail: 'code=a8f3k2x9... + state', type: 'token', status: 'idle' },
    ],
    token_exchange: [
      { id: 't1', from: 'client', to: 'auth', label: 'POST /token', detail: 'auth_code + PKCE verifier', type: 'data', status: 'idle' },
      { id: 't2', from: 'auth', to: 'client', label: 'Token Response', detail: 'PQ-signed ID + Access + Refresh tokens', type: 'token', status: 'idle' },
    ],
    session_bind: [
      { id: 'b1', from: 'client', to: 'auth', label: 'Session Bind', detail: 'cnf.kbh = SHA256(exporter || sid)', type: 'verify', status: 'idle' },
      { id: 'b2', from: 'auth', to: 'client', label: 'Binding Confirmed', detail: 'Session binding registered', type: 'verify', status: 'idle' },
    ],
    resource_access: [
      { id: 'r1', from: 'client', to: 'resource', label: 'GET /userinfo', detail: 'Bearer token + session binding', type: 'data', status: 'idle' },
      { id: 'r2', from: 'resource', to: 'client', label: '200 OK', detail: 'User profile data', type: 'data', status: 'idle' },
    ],
  };
  return events[stepId] || [];
}

export function ProtocolActivity({ currentStepId, flowState }: ProtocolActivityProps) {
  const [events, setEvents] = useState<ActivityEvent[]>([]);
  const [activeEventIdx, setActiveEventIdx] = useState(-1);
  const [packetProgress, setPacketProgress] = useState(0);
  const rafRef = useRef<number>();
  const startTimeRef = useRef(0);

  useEffect(() => {
    if (flowState === 'done') return;
    if (!currentStepId || flowState === 'idle') {
      setEvents([]);
      setActiveEventIdx(-1);
      return;
    }

    const stepEvents = getActivityEvents(currentStepId);
    setEvents(stepEvents);
    setActiveEventIdx(-1);

    let idx = 0;
    const duration = 500;

    const runEvent = () => {
      if (idx >= stepEvents.length) return;
      setActiveEventIdx(idx);
      setPacketProgress(0);
      startTimeRef.current = performance.now();

      const animate = (now: number) => {
        const elapsed = now - startTimeRef.current;
        const progress = Math.min(elapsed / duration, 1);
        setPacketProgress(progress);

        if (progress < 1) {
          rafRef.current = requestAnimationFrame(animate);
        } else {
          setEvents(prev => prev.map((e, i) => i === idx ? { ...e, status: 'received' } : e));
          idx++;
          if (idx < stepEvents.length) {
            setTimeout(runEvent, 200);
          }
        }
      };

      setEvents(prev => prev.map((e, i) => i === idx ? { ...e, status: 'sending' } : e));
      rafRef.current = requestAnimationFrame(animate);
    };

    const timer = setTimeout(runEvent, 150);

    return () => {
      clearTimeout(timer);
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
  }, [currentStepId, flowState]);

  const wrapperStyle: React.CSSProperties = {
    width: '100%',
    display: 'flex',
    justifyContent: 'center',
    padding: '0 16px 16px',
    flexShrink: 0,
  };

  // Idle state — show all 3 entities
  if (flowState === 'idle') {
    return (
      <div style={wrapperStyle}>
        <div style={{
          padding: '20px 32px',
          borderRadius: '16px',
          background: 'rgba(14, 20, 36, 0.9)',
          border: '1px solid rgba(92, 168, 212, 0.1)',
          backdropFilter: 'blur(16px)',
          display: 'flex',
          alignItems: 'center',
          gap: '24px',
          boxShadow: '0 4px 30px rgba(0,0,0,0.25)',
        }}>
          {['client', 'auth', 'resource'].map(key => {
            const meta = ENTITY_META[key];
            return (
              <div key={key} style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: '8px',
              }}>
                <div style={{
                  width: '64px',
                  height: '64px',
                  borderRadius: '14px',
                  background: 'rgba(22, 31, 53, 0.8)',
                  border: `1.5px solid ${meta.color}`,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '28px',
                  boxShadow: `0 0 12px color-mix(in srgb, ${meta.color} 15%, transparent)`,
                  opacity: 0.7,
                }}>
                  {meta.icon}
                </div>
                <span className="font-display" style={{
                  fontSize: '10px',
                  letterSpacing: '0.15em',
                  color: meta.color,
                  opacity: 0.6,
                }}>
                  {meta.label}
                </span>
              </div>
            );
          })}
          <div style={{
            width: '1px',
            height: '48px',
            background: 'rgba(92, 168, 212, 0.1)',
            margin: '0 6px',
          }} />
          <span className="font-code" style={{
            fontSize: '12px',
            color: 'var(--text-dim)',
          }}>
            AWAITING PROTOCOL
          </span>
        </div>
      </div>
    );
  }



  // Running — show ONLY the 2 interacting entities (the third is not rendered)
  const [entityA, entityB] = currentStepId ? getStepEntities(currentStepId) : ['client', 'auth'];
  const metaA = ENTITY_META[entityA];
  const metaB = ENTITY_META[entityB];
  const activeEvent = events[activeEventIdx];

  return (
    <div style={{ ...wrapperStyle, pointerEvents: 'none', position: 'relative' }}>
      
      {/* Floating Done Badge on the Left */}
      {flowState === 'done' && (
        <div style={{
          position: 'absolute',
          left: '20px',
          top: '50%',
          transform: 'translateY(-50%)',
          padding: '16px 24px',
          borderRadius: '16px',
          background: 'rgba(14, 20, 36, 0.95)',
          border: '1px solid rgba(78, 201, 160, 0.4)',
          backdropFilter: 'blur(16px)',
          boxShadow: '0 0 30px rgba(78, 201, 160, 0.15)',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'flex-start',
          gap: '8px',
          animation: 'slideInLeft 0.5s ease forwards',
          zIndex: 50,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
             <div style={{
               width: '14px',
               height: '14px',
               borderRadius: '50%',
               background: 'var(--lime)',
               boxShadow: '0 0 12px var(--lime)',
               animation: 'pulse-glow 1.5s ease infinite',
             }} />
             <span className="font-display" style={{
               fontSize: '14px',
               letterSpacing: '0.2em',
               color: 'var(--lime)',
               fontWeight: 'bold',
             }}>
               ALL SECURE
             </span>
          </div>
          <div className="font-code" style={{ fontSize: '11px', color: 'var(--lime)', opacity: 0.8 }}>
            End-to-End Quantum Safe
          </div>
        </div>
      )}

      <div style={{
        borderRadius: '16px',
        background: 'rgba(14, 20, 36, 0.94)',
        border: '1px solid rgba(92, 168, 212, 0.12)',
        backdropFilter: 'blur(20px)',
        overflow: 'hidden',
        boxShadow: '0 4px 30px rgba(0, 0, 0, 0.4)',
        width: '100%',
        maxWidth: '750px',
      }}>
        {/* Top accent line */}
        <div style={{
          height: '2px',
          background: `linear-gradient(90deg, transparent, ${metaA.color}, ${metaB.color}, transparent)`,
          opacity: 0.5,
        }} />

        <div style={{ padding: '20px 28px' }}>
          {/* Two entities + connection line between them */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0',
          }}>
            {/* Entity A */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexShrink: 0 }}>
              {/* Event history labels to the left of Entity A */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', alignItems: 'flex-end', minWidth: '90px' }}>
                {events.filter(e => e.status === 'received' && e.from === entityA).map(e => (
                  <div key={e.id} className="font-code" style={{ animation: 'slideInRight 0.3s ease', fontSize: '9px', padding: '2px 6px', borderRadius: '4px', background: 'rgba(78, 201, 160, 0.08)', border: '1px solid rgba(78, 201, 160, 0.15)', color: 'var(--lime)', whiteSpace: 'nowrap' }}>
                    ✓ {e.label}
                  </div>
                ))}
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '8px' }}>
                <div style={{
                  width: '72px', height: '72px', borderRadius: '16px', background: 'rgba(22, 31, 53, 0.8)', border: `2px solid ${metaA.color}`, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '32px', boxShadow: `0 0 16px color-mix(in srgb, ${metaA.color} 20%, transparent)`,
                  animation: activeEvent?.from === entityA && activeEvent?.status === 'sending' ? 'pulse-glow 0.8s ease infinite' : 'none',
                }}>
                  {metaA.icon}
                </div>
                <span className="font-display" style={{ fontSize: '10px', letterSpacing: '0.18em', fontWeight: 600, color: metaA.color }}>
                  {metaA.label}
                </span>

                {/* Completed Cert/Key types below icon */}
                <div style={{ display: 'flex', gap: '4px', minHeight: '14px', flexWrap: 'wrap', justifyContent: 'center', maxWidth: '80px' }}>
                  {events.filter(e => e.status === 'received' && e.from === entityA).map(e => (
                    <span key={e.id} className="font-display" style={{ animation: 'slideUp 0.3s ease', fontSize: '8px', color: 'var(--cyan)', padding: '1px 4px', background: 'rgba(92,168,212,0.1)', border: '1px solid rgba(92,168,212,0.2)', borderRadius: '3px' }}>
                      {e.type.toUpperCase()}
                    </span>
                  ))}
                </div>
              </div>
            </div>

            {/* Connection lane — message label on the line, not over icons */}
            <div style={{
              flex: 1,
              position: 'relative',
              minWidth: '120px',
              padding: '0 16px',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
            }}>
              {/* The line */}
              <div style={{
                width: '100%',
                height: '2px',
                background: 'rgba(92, 168, 212, 0.12)',
                position: 'relative',
              }}>
                {/* Packet dot traveling on the line */}
                {activeEvent && activeEvent.status === 'sending' && (() => {
                  const isReverse = activeEvent.to === entityA;
                  const pct = isReverse ? (1 - packetProgress) * 100 : packetProgress * 100;
                  const packetColor = {
                    key: 'var(--cyan)',
                    cert: 'var(--magenta)',
                    token: 'var(--amber)',
                    data: 'var(--electric)',
                    verify: 'var(--lime)',
                  }[activeEvent.type];

                  return (
                    <>
                      {/* Trail behind packet */}
                      <div style={{
                        position: 'absolute',
                        top: '-1px',
                        height: '4px',
                        left: isReverse ? `${pct}%` : '0',
                        width: isReverse ? `${100 - pct}%` : `${pct}%`,
                        background: `linear-gradient(${isReverse ? '270deg' : '90deg'}, transparent, ${packetColor})`,
                        opacity: 0.4,
                        transition: 'width 0.05s linear',
                      }} />
                      {/* Packet dot */}
                      <div style={{
                        position: 'absolute',
                        top: '50%',
                        left: `${pct}%`,
                        transform: 'translate(-50%, -50%)',
                        width: '10px',
                        height: '10px',
                        borderRadius: '50%',
                        background: packetColor,
                        boxShadow: `0 0 8px ${packetColor}`,
                      }} />
                    </>
                  );
                })()}
              </div>

              {/* Label ON the line (above) — not on the icon */}
              {activeEvent && (
                <div style={{
                  position: 'absolute',
                  top: '-20px',
                  left: '50%',
                  transform: 'translateX(-50%)',
                  whiteSpace: 'nowrap',
                }}>
                  <span className="font-code" style={{
                    fontSize: '11px',
                    fontWeight: 600,
                    color: 'var(--text-bright)',
                    letterSpacing: '0.05em',
                    textShadow: '0 0 8px rgba(92,168,212,0.3)',
                  }}>
                    {activeEvent.label}
                  </span>
                </div>
              )}
            </div>

            {/* Entity B */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexShrink: 0 }}>
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '8px' }}>
                <div style={{
                  width: '72px', height: '72px', borderRadius: '16px', background: 'rgba(22, 31, 53, 0.8)', border: `2px solid ${metaB.color}`, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '32px', boxShadow: `0 0 16px color-mix(in srgb, ${metaB.color} 20%, transparent)`,
                  animation: activeEvent?.from === entityB && activeEvent?.status === 'sending' ? 'pulse-glow 0.8s ease infinite' : 'none',
                }}>
                  {metaB.icon}
                </div>
                <span className="font-display" style={{ fontSize: '10px', letterSpacing: '0.18em', fontWeight: 600, color: metaB.color }}>
                  {metaB.label}
                </span>

                {/* Completed Cert/Key types below icon */}
                <div style={{ display: 'flex', gap: '4px', minHeight: '14px', flexWrap: 'wrap', justifyContent: 'center', maxWidth: '80px' }}>
                  {events.filter(e => e.status === 'received' && e.from === entityB).map(e => (
                    <span key={e.id} className="font-display" style={{ animation: 'slideUp 0.3s ease', fontSize: '8px', color: 'var(--cyan)', padding: '1px 4px', background: 'rgba(92,168,212,0.1)', border: '1px solid rgba(92,168,212,0.2)', borderRadius: '3px' }}>
                      {e.type.toUpperCase()}
                    </span>
                  ))}
                </div>
              </div>

              {/* Event history labels to the right of Entity B */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', alignItems: 'flex-start', minWidth: '90px' }}>
                {events.filter(e => e.status === 'received' && e.from === entityB).map(e => (
                  <div key={e.id} className="font-code" style={{ animation: 'slideInLeft 0.3s ease', fontSize: '9px', padding: '2px 6px', borderRadius: '4px', background: 'rgba(78, 201, 160, 0.08)', border: '1px solid rgba(78, 201, 160, 0.15)', color: 'var(--lime)', whiteSpace: 'nowrap' }}>
                    ✓ {e.label}
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Event History Scrollable Bar */}
          {events.filter(e => e.status !== 'idle').length > 0 && (
            <div style={{
              display: 'flex',
              flexDirection: 'column',
              gap: '6px',
              padding: '10px 14px',
              borderRadius: '10px',
              marginTop: '14px',
              background: 'rgba(22, 31, 53, 0.5)',
              border: '1px solid rgba(92, 168, 212, 0.08)',
              maxHeight: '120px',
              overflowY: 'auto',
            }}>
              {events.filter(e => e.status !== 'idle').map(ev => (
                <div key={ev.id} style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: ev.from === entityA ? 'flex-start' : 'flex-end',
                }}>
                  <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '10px',
                    padding: '6px 12px',
                    borderRadius: '8px',
                    background: 'rgba(14, 20, 36, 0.6)',
                    border: '1px solid rgba(92, 168, 212, 0.1)',
                  }}>
                    <div className="font-display" style={{
                      fontSize: '10px',
                      letterSpacing: '0.12em',
                      padding: '3px 8px',
                      borderRadius: '4px',
                      background: 'rgba(92, 168, 212, 0.08)',
                      color: 'var(--cyan)',
                      fontWeight: 600,
                    }}>
                      {ev.type.toUpperCase()}
                    </div>

                    <div className="font-code" style={{ fontSize: '11px', color: 'var(--text-mid)' }}>
                      {ENTITY_META[ev.from].label}
                      <span style={{ color: 'var(--text-bright)', margin: '0 6px' }}>→</span>
                      {ENTITY_META[ev.to].label}
                    </div>

                    <div style={{ width: '1px', height: '12px', background: 'rgba(92, 168, 212, 0.2)' }} />

                    <div className="font-code" style={{ fontSize: '11px', color: 'var(--text-bright)' }}>
                      {ev.detail}
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '5px', marginLeft: '6px' }}>
                      <div style={{
                        width: '6px',
                        height: '6px',
                        borderRadius: '50%',
                        background: ev.status === 'received' ? 'var(--lime)' : 'var(--amber)',
                        boxShadow: `0 0 6px ${ev.status === 'received' ? 'var(--lime)' : 'var(--amber)'}`,
                      }} />
                      <span className="font-code" style={{
                        fontSize: '9px',
                        fontWeight: 600,
                        color: ev.status === 'received' ? 'var(--lime)' : 'var(--amber)',
                      }}>
                        {ev.status === 'received' ? 'OK' : 'TX'}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

        </div>
      </div>
    </div>
  );
}
