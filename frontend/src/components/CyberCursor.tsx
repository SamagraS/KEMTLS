import { useEffect, useRef } from 'react';

/* ═══════════════════════════════════════════
   TRAIL CURSOR
   Smooth cursor with a fading trail effect
   ═══════════════════════════════════════════ */
export function CyberCursor() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const posRef = useRef({ x: -100, y: -100 });
  const trailRef = useRef<Array<{ x: number; y: number; alpha: number }>>([]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const resize = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    };
    resize();
    window.addEventListener('resize', resize);

    let lastX = -100;
    let lastY = -100;

    const onMove = (e: MouseEvent) => {
      posRef.current = { x: e.clientX, y: e.clientY };

      // Only add trail point if moved enough distance
      const dx = e.clientX - lastX;
      const dy = e.clientY - lastY;
      if (dx * dx + dy * dy > 9) {
        trailRef.current.push({ x: e.clientX, y: e.clientY, alpha: 1 });
        lastX = e.clientX;
        lastY = e.clientY;
      }

      // Cap trail length
      if (trailRef.current.length > 50) {
        trailRef.current = trailRef.current.slice(-50);
      }
    };

    window.addEventListener('mousemove', onMove);

    let raf: number;
    const animate = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      const trail = trailRef.current;

      // Fade trail points
      for (let i = trail.length - 1; i >= 0; i--) {
        trail[i].alpha -= 0.025;
        if (trail[i].alpha <= 0) {
          trail.splice(i, 1);
        }
      }

      // Draw trail as smooth gradient line
      if (trail.length > 2) {
        for (let i = 1; i < trail.length; i++) {
          const prev = trail[i - 1];
          const curr = trail[i];
          const alpha = curr.alpha * 0.6;
          const width = curr.alpha * 4.5;

          ctx.beginPath();
          ctx.moveTo(prev.x, prev.y);
          ctx.lineTo(curr.x, curr.y);
          ctx.strokeStyle = `rgba(100, 220, 255, ${alpha})`;
          ctx.lineWidth = width;
          ctx.lineCap = 'round';
          ctx.stroke();
        }
      }

      // Draw small dot at cursor position
      const { x, y } = posRef.current;
      if (x > 0 && y > 0) {
        ctx.beginPath();
        ctx.arc(x, y, 5, 0, Math.PI * 2);
        ctx.fillStyle = 'rgba(180, 240, 255, 0.9)';
        ctx.fill();

        // Prominent outer glow
        ctx.beginPath();
        ctx.arc(x, y, 16, 0, Math.PI * 2);
        const grad = ctx.createRadialGradient(x, y, 0, x, y, 16);
        grad.addColorStop(0, 'rgba(100, 220, 255, 0.3)');
        grad.addColorStop(1, 'transparent');
        ctx.fillStyle = grad;
        ctx.fill();
      }

      raf = requestAnimationFrame(animate);
    };
    raf = requestAnimationFrame(animate);

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('resize', resize);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 99998,
        pointerEvents: 'none',
      }}
    />
  );
}
