import { useEffect, useRef } from 'react';

interface Shape {
  x: number;
  y: number;
  vx: number;
  vy: number;
  size: number;
  type: 'triangle' | 'square' | 'diamond' | 'hexagon';
  rotation: number;
  rotSpeed: number;
  alpha: number;
}

export function GridBackground() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let w = (canvas.width = window.innerWidth);
    let h = (canvas.height = window.innerHeight);

    const shapes: Shape[] = [];
    const SHAPE_COUNT = 90;
    const CONNECTION_DIST = 200;
    const types: Shape['type'][] = ['triangle', 'square', 'diamond', 'hexagon'];

    for (let i = 0; i < SHAPE_COUNT; i++) {
      shapes.push({
        x: Math.random() * w,
        y: Math.random() * h,
        vx: (Math.random() - 0.5) * 0.3,
        vy: (Math.random() - 0.5) * 0.3,
        size: Math.random() * 6 + 3,
        type: types[Math.floor(Math.random() * types.length)],
        rotation: Math.random() * Math.PI * 2,
        rotSpeed: (Math.random() - 0.5) * 0.008,
        alpha: Math.random() * 0.12 + 0.04,
      });
    }

    const mouse = { x: -1000, y: -1000 };
    const onMouse = (e: MouseEvent) => {
      mouse.x = e.clientX;
      mouse.y = e.clientY;
    };
    window.addEventListener('mousemove', onMouse);

    const resize = () => {
      w = canvas.width = window.innerWidth;
      h = canvas.height = window.innerHeight;
    };
    window.addEventListener('resize', resize);

    let raf: number;
    let time = 0;

    function drawShape(ctx: CanvasRenderingContext2D, s: Shape) {
      ctx.save();
      ctx.translate(s.x, s.y);
      ctx.rotate(s.rotation);
      ctx.globalAlpha = s.alpha;

      // Slight reddish tinge to triangles and squares
      if (s.type === 'triangle' || s.type === 'square') {
        ctx.strokeStyle = 'rgba(96, 15, 27, 1)';
      } else {
        ctx.strokeStyle = 'rgba(255, 255, 255, 1)';
      }

      ctx.lineWidth = 0.8;

      switch (s.type) {
        case 'triangle':
          ctx.beginPath();
          ctx.moveTo(0, -s.size);
          ctx.lineTo(s.size * 0.866, s.size * 0.5);
          ctx.lineTo(-s.size * 0.866, s.size * 0.5);
          ctx.closePath();
          ctx.stroke();
          break;
        case 'square':
          ctx.strokeRect(-s.size / 2, -s.size / 2, s.size, s.size);
          break;
        case 'diamond':
          ctx.beginPath();
          ctx.moveTo(0, -s.size);
          ctx.lineTo(s.size * 0.7, 0);
          ctx.lineTo(0, s.size);
          ctx.lineTo(-s.size * 0.7, 0);
          ctx.closePath();
          ctx.stroke();
          break;
        case 'hexagon':
          ctx.beginPath();
          for (let i = 0; i < 6; i++) {
            const angle = (Math.PI / 3) * i - Math.PI / 6;
            const px = Math.cos(angle) * s.size * 0.7;
            const py = Math.sin(angle) * s.size * 0.7;
            if (i === 0) ctx.moveTo(px, py);
            else ctx.lineTo(px, py);
          }
          ctx.closePath();
          ctx.stroke();
          break;
      }

      ctx.globalAlpha = 1;
      ctx.restore();
    }

    const draw = () => {
      ctx.clearRect(0, 0, w, h);
      time += 0.003;

      // Subtle grid — more visible with a random flicker pulsation
      const basePulse = Math.sin(time * 0.8) * 0.02;
      const flicker = Math.random() * 0.03;
      const gridPulse = 0.05 + basePulse + flicker;
      const gridSize = 70;

      ctx.lineWidth = 0.4;
      for (let x = 0; x < w; x += gridSize) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, h);
        ctx.strokeStyle = `rgba(100, 140, 180, ${gridPulse})`;
        ctx.stroke();
      }
      for (let y = 0; y < h; y += gridSize) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(w, y);
        ctx.strokeStyle = `rgba(100, 140, 180, ${gridPulse})`;
        ctx.stroke();
      }

      // Grid intersection dots — very subtle
      ctx.fillStyle = 'rgba(100, 140, 180, 0.06)';
      for (let x = 0; x < w; x += gridSize) {
        for (let y = 0; y < h; y += gridSize) {
          ctx.beginPath();
          ctx.arc(x, y, 0.8, 0, Math.PI * 2);
          ctx.fill();
        }
      }

      // Mouse proximity — subtle grid highlight
      const mgx = Math.round(mouse.x / gridSize) * gridSize;
      const mgy = Math.round(mouse.y / gridSize) * gridSize;
      for (let ox = -2; ox <= 2; ox++) {
        for (let oy = -2; oy <= 2; oy++) {
          const ix = mgx + ox * gridSize;
          const iy = mgy + oy * gridSize;
          const d = Math.sqrt((ix - mouse.x) ** 2 + (iy - mouse.y) ** 2);
          if (d < 200) {
            const a = (1 - d / 200) * 0.15;
            ctx.beginPath();
            ctx.arc(ix, iy, 2, 0, Math.PI * 2);
            ctx.fillStyle = `rgba(140, 180, 220, ${a})`;
            ctx.fill();
          }
        }
      }

      // Update & draw shapes
      for (const s of shapes) {
        s.x += s.vx;
        s.y += s.vy;
        s.rotation += s.rotSpeed;

        // Mouse repulsion — stronger interaction
        const dx = s.x - mouse.x;
        const dy = s.y - mouse.y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < 150) {
          const force = (150 - dist) / 150;
          s.vx += (dx / dist) * force * 0.4;
          s.vy += (dy / dist) * force * 0.4;
        }

        s.vx *= 0.995;
        s.vy *= 0.995;

        // Wrap
        if (s.x < -20) s.x = w + 20;
        if (s.x > w + 20) s.x = -20;
        if (s.y < -20) s.y = h + 20;
        if (s.y > h + 20) s.y = -20;

        drawShape(ctx, s);
      }

      // Connection lines — between shapes
      for (let i = 0; i < shapes.length; i++) {
        for (let j = i + 1; j < shapes.length; j++) {
          const dx = shapes[i].x - shapes[j].x;
          const dy = shapes[i].y - shapes[j].y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < CONNECTION_DIST) {
            const time = performance.now();
            const pulse = Math.sin(time * 0.0015 + shapes[i].x * 0.01 + shapes[j].y * 0.01) * 0.5 + 0.5;
            const baseAlpha = 1 - dist / CONNECTION_DIST;
            const alpha = baseAlpha * (0.02 + pulse * 0.08); // Pulsates between 0.02 and 0.10

            ctx.beginPath();
            ctx.moveTo(shapes[i].x, shapes[i].y);
            ctx.lineTo(shapes[j].x, shapes[j].y);
            ctx.strokeStyle = `rgba(120, 160, 200, ${alpha})`;
            ctx.lineWidth = 0.3 + pulse * 0.3; // Very light pulsation in thickness
            ctx.stroke();
          }
        }
      }

      // Cursor connections — visual interactivity
      for (const s of shapes) {
        const dx = s.x - mouse.x;
        const dy = s.y - mouse.y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < 220) {
          const alpha = (1 - dist / 220) * 0.4;
          ctx.beginPath();
          ctx.moveTo(s.x, s.y);
          ctx.lineTo(mouse.x, mouse.y);
          ctx.strokeStyle = `rgba(92, 168, 212, ${alpha})`;
          ctx.lineWidth = 1;
          ctx.stroke();
        }
      }

      raf = requestAnimationFrame(draw);
    };
    raf = requestAnimationFrame(draw);

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener('mousemove', onMouse);
      window.removeEventListener('resize', resize);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 0,
        pointerEvents: 'none',
      }}
    />
  );
}
