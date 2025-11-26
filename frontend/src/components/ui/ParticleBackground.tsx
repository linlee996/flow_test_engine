import React, { useEffect, useRef } from 'react';

export const ParticleBackground: React.FC = () => {
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const mouse = useRef({ x: 0, y: 0 });

    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        if (!ctx) return;

        let animationFrameId: number;
        let t = 0;

        const handleMouseMove = (e: MouseEvent) => {
            mouse.current.x = e.clientX;
            mouse.current.y = e.clientY;
        };

        const resizeCanvas = () => {
            canvas.width = window.innerWidth;
            canvas.height = window.innerHeight;
        };

        const drawGradient = () => {
            t += 0.005;

            const w = canvas.width;
            const h = canvas.height;

            // Clear with light background
            ctx.fillStyle = '#F5F7FA';
            ctx.fillRect(0, 0, w, h);

            // Mouse influence
            const mx = mouse.current.x / w;
            const my = mouse.current.y / h;

            // Blob 1: Pastel Purple
            const x1 = w * 0.3 + Math.sin(t) * w * 0.2 + (mx - 0.5) * 100;
            const y1 = h * 0.4 + Math.cos(t * 0.8) * h * 0.2 + (my - 0.5) * 100;
            const r1 = Math.min(w, h) * 0.6;

            const g1 = ctx.createRadialGradient(x1, y1, 0, x1, y1, r1);
            g1.addColorStop(0, 'rgba(167, 139, 250, 0.2)'); // Violet
            g1.addColorStop(1, 'rgba(167, 139, 250, 0)');

            ctx.fillStyle = g1;
            ctx.fillRect(0, 0, w, h);

            // Blob 2: Pastel Blue
            const x2 = w * 0.7 + Math.cos(t * 1.2) * w * 0.2 - (mx - 0.5) * 100;
            const y2 = h * 0.6 + Math.sin(t * 0.9) * h * 0.2 - (my - 0.5) * 100;
            const r2 = Math.min(w, h) * 0.7;

            const g2 = ctx.createRadialGradient(x2, y2, 0, x2, y2, r2);
            g2.addColorStop(0, 'rgba(96, 165, 250, 0.2)'); // Blue
            g2.addColorStop(1, 'rgba(96, 165, 250, 0)');

            ctx.fillStyle = g2;
            ctx.fillRect(0, 0, w, h);

            // Blob 3: Pastel Pink
            const x3 = w * 0.5 + Math.sin(t * 0.5) * w * 0.3;
            const y3 = h * 0.8 + Math.cos(t * 0.4) * h * 0.2;
            const r3 = Math.min(w, h) * 0.5;

            const g3 = ctx.createRadialGradient(x3, y3, 0, x3, y3, r3);
            g3.addColorStop(0, 'rgba(244, 114, 182, 0.15)'); // Pink
            g3.addColorStop(1, 'rgba(244, 114, 182, 0)');

            ctx.fillStyle = g3;
            ctx.fillRect(0, 0, w, h);

            animationFrameId = requestAnimationFrame(drawGradient);
        };

        window.addEventListener('resize', resizeCanvas);
        window.addEventListener('mousemove', handleMouseMove);
        resizeCanvas();
        drawGradient();

        return () => {
            window.removeEventListener('resize', resizeCanvas);
            window.removeEventListener('mousemove', handleMouseMove);
            cancelAnimationFrame(animationFrameId);
        };
    }, []);

    return (
        <canvas
            ref={canvasRef}
            style={{
                position: 'fixed',
                top: 0,
                left: 0,
                width: '100%',
                height: '100%',
                zIndex: -1,
                pointerEvents: 'none',
            }}
        />
    );
};
