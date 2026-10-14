import React from 'react';
import { createRoot } from 'react-dom/client';
import DarkVeil from './DarkVeil';

const q = new URLSearchParams(location.search);
const num = (k: string, d: number) => (q.has(k) ? parseFloat(q.get(k)!) : d);

createRoot(document.getElementById('veil')!).render(
  <DarkVeil
    color={q.get('color') || '#C5956E'}
    speed={num('speed', 0.5)}
    scale={num('scale', 1)}
    flow={num('flow', 1)}
    warp={num('warp', 0)}
    brightness={num('brightness', 0.6)}
    glow={num('glow', 0.3)}
    grain={num('grain', 0.03)}
    quality={num('quality', 0.5)}
    mouseInteraction={false}
    intro={false}
    dpr={1}
  />
);
