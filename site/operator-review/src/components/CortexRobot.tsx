/** CSS-only CORTEX robot ported from
 * https://asifhussain60.github.io/CORTEX/ (Asif's framework).
 * Used as "Built by CORTEX" branding badge — bottom-left corner.
 */
export function CortexRobot() {
  return (
    <button
      onClick={() =>
        window.open('https://asifhussain60.github.io/CORTEX/', '_blank', 'noopener,noreferrer')
      }
      aria-label="Built by CORTEX"
      className="fixed bottom-6 left-6 z-80 w-[78px] h-[86px] bg-transparent border-none p-0 cursor-pointer group"
    >
      <div className="relative flex flex-col items-center transition-transform duration-300 group-hover:-translate-y-1 group-active:translate-y-0 group-active:scale-95">
        <div
          className="relative w-12 h-8 flex items-center justify-center gap-1.5"
          style={{
            background: 'linear-gradient(160deg, #1e1b4b 0%, #312e81 60%, #1a1040 100%)',
            border: '1.5px solid rgba(123,97,255,0.55)',
            borderRadius: '10px 10px 7px 7px',
            boxShadow: '0 0 16px rgba(123,97,255,0.3), inset 0 1px 0 rgba(255,255,255,0.08)',
          }}
        >
          {/* antenna stem */}
          <span
            className="absolute"
            style={{
              top: '-10px', left: '50%', transform: 'translateX(-50%)',
              width: '3px', height: '10px',
              background: 'linear-gradient(to top, rgba(123,97,255,0.7), rgba(167,139,250,0.95))',
              borderRadius: '2px',
            }}
          />
          {/* pulsing dot */}
          <span
            className="absolute animate-cortex-pulse"
            style={{
              top: '-15px', left: '50%', transform: 'translateX(-50%)',
              width: '8px', height: '8px', borderRadius: '50%',
              background: 'radial-gradient(circle, var(--accent-purple-soft) 30%, var(--accent-purple) 100%)',
              boxShadow: '0 0 10px rgba(167,139,250,0.95)',
            }}
          />
          <span
            className="rounded-full animate-eye-blink shrink-0"
            style={{
              width: '10px', height: '10px',
              background: 'radial-gradient(circle at 35% 35%, var(--accent-cyan), #06b6d4 60%, #0e7490)',
              boxShadow: '0 0 7px rgba(0,212,255,0.8), 0 0 14px rgba(0,212,255,0.35)',
            }}
          />
          <span
            className="rounded-full animate-eye-blink shrink-0"
            style={{
              width: '10px', height: '10px',
              background: 'radial-gradient(circle at 35% 35%, var(--accent-cyan), #06b6d4 60%, #0e7490)',
              boxShadow: '0 0 7px rgba(0,212,255,0.8), 0 0 14px rgba(0,212,255,0.35)',
              animationDelay: '0.12s',
            }}
          />
          <span
            className="absolute overflow-hidden"
            style={{
              bottom: '6px', left: '50%', transform: 'translateX(-50%)',
              width: '28px', height: '4px', borderRadius: '2px',
              background: 'rgba(123,97,255,0.2)',
              border: '1px solid rgba(123,97,255,0.35)',
            }}
          >
            <span
              className="absolute"
              style={{
                left: '-100%', top: 0, width: '60%', height: '100%',
                background: 'linear-gradient(90deg, transparent, rgba(0,212,255,0.8), transparent)',
                animation: 'scan 2.4s linear infinite',
              }}
            />
          </span>
        </div>
        <div
          className="w-14 h-8 flex items-center justify-center"
          style={{
            background: 'linear-gradient(160deg, #1e1b4b 0%, #1a1040 100%)',
            border: '1.5px solid rgba(123,97,255,0.5)',
            borderTop: 'none',
            borderRadius: '0 0 12px 12px',
            boxShadow: '0 6px 20px rgba(0,0,0,0.5), inset 0 0 0 1px rgba(123,97,255,0.08)',
          }}
        >
          <span
            className="font-display font-bold text-white text-[0.6rem] tracking-tighter"
            style={{
              width: '18px', height: '18px', borderRadius: '4px',
              background: 'linear-gradient(135deg, var(--accent-purple) 0%, var(--accent-cyan) 100%)',
              boxShadow: '0 0 8px rgba(123,97,255,0.5)',
              display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
              animation: 'cortex-pulse 1.8s ease-in-out infinite',
            }}
          >
            CX
          </span>
        </div>
        <span
          className="absolute"
          style={{
            bottom: '-8px', left: '50%', transform: 'translateX(-50%)',
            width: '52px', height: '12px', borderRadius: '50%',
            background: 'radial-gradient(ellipse, rgba(123,97,255,0.55) 0%, transparent 70%)',
            filter: 'blur(4px)',
          }}
        />

        {/* Tooltip */}
        <span
          className="absolute opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none whitespace-nowrap"
          style={{
            left: '100%', bottom: '50%', transform: 'translate(0.85rem, 50%)',
            background: 'var(--surface-elevated)',
            border: '1px solid var(--border-default)',
            borderRadius: '10px',
            padding: '0.55rem 0.85rem',
            fontSize: '0.72rem',
            color: 'var(--text-secondary)',
            boxShadow: '0 8px 24px rgba(0,0,0,0.45)',
            backdropFilter: 'blur(20px)',
          }}
        >
          Built by <strong className="text-accent-cyan font-semibold">CORTEX</strong>
        </span>
      </div>
    </button>
  )
}
