/**
 * NarrativeScroll.tsx
 *
 * Full-viewport Apple-style cinematic scroll controller.
 * Powered by GSAP ScrollTrigger. Each pipeline phase becomes
 * a pinned chapter that locks the viewport while its content
 * animates in, then releases to the next.
 *
 * Content is injected via `phases` prop pulled from
 * architecture-snapshot.json — the same data source as the
 * Architecture > Pipeline view, so the two surfaces are
 * always in sync.
 */

import { useEffect, useRef } from 'react';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';

gsap.registerPlugin(ScrollTrigger);

// ── Visual SVG definitions — one per phase ───────────────────────

function VisualReadBook() {
  return (
    <svg viewBox="0 0 340 240" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <style>{`
          @keyframes rb-scan{0%,100%{transform:translateY(0)}50%{transform:translateY(128px)}}
          @keyframes rb-fade{0%{opacity:0;transform:translateX(-5px)}100%{opacity:1;transform:translateX(0)}}
          .rb-beam{animation:rb-scan 3.2s ease-in-out infinite}
          .rb-l1{animation:rb-fade .4s .4s both}.rb-l2{animation:rb-fade .4s .8s both}
          .rb-l3{animation:rb-fade .4s 1.2s both}.rb-l4{animation:rb-fade .4s 1.6s both}
          .rb-l5{animation:rb-fade .4s 2.0s both}.rb-l6{animation:rb-fade .4s 2.4s both}
          .rb-l7{animation:rb-fade .4s 2.8s both}
        `}</style>
      </defs>
      {/* Book spine + pages */}
      <rect x="18" y="28" width="10" height="168" rx="2" fill="rgba(201,151,58,0.2)" stroke="rgba(201,151,58,0.4)" strokeWidth="1"/>
      <rect x="28" y="28" width="118" height="168" rx="2" fill="rgba(240,236,227,0.04)" stroke="rgba(240,236,227,0.2)" strokeWidth="1.5"/>
      {/* Arabic-style right-aligned text lines */}
      {[52,68,84,100,116,132,148,164,180].map((y,i)=>(
        <line key={i} x1={132-i*2} y1={y} x2="136" y2={y} stroke="rgba(240,236,227,0.16)" strokeWidth="1.6" strokeLinecap="round"/>
      ))}
      <text x="82" y="213" textAnchor="middle" fill="rgba(240,236,227,0.2)" fontSize="8" fontFamily="Inter,sans-serif" letterSpacing="2">SOURCE</text>
      {/* Scanner beam sweeping down */}
      <g className="rb-beam">
        <rect x="28" y="28" width="118" height="7" rx="1" fill="rgba(201,151,58,0.08)"/>
        <rect x="28" y="33" width="118" height="2" fill="rgba(201,151,58,0.85)" style={{filter:'blur(1px)'}}/>
        <rect x="28" y="33" width="118" height="1" fill="rgba(255,220,140,0.9)"/>
      </g>
      {/* Arrow */}
      <path d="M 158 112 L 192 112" stroke="rgba(201,151,58,0.55)" strokeWidth="2" strokeLinecap="round"/>
      <polygon points="190,107 200,112 190,117" fill="rgba(201,151,58,0.55)"/>
      {/* Digital output — right panel */}
      <rect x="202" y="28" width="120" height="168" rx="3" fill="rgba(26,92,138,0.07)" stroke="rgba(106,180,240,0.22)" strokeWidth="1.5"/>
      <text x="216" y="46" fill="rgba(106,180,240,0.5)" fontSize="8" fontFamily="Inter,sans-serif" letterSpacing="2">DIGITAL TEXT</text>
      {[{y:60,w:90,c:'rb-l1'},{y:76,w:74,c:'rb-l2'},{y:92,w:98,c:'rb-l3'},{y:108,w:66,c:'rb-l4'},{y:124,w:85,c:'rb-l5'},{y:140,w:72,c:'rb-l6'},{y:156,w:56,c:'rb-l7'}].map((r,i)=>(
        <line key={i} x1="216" y1={r.y} x2={216+r.w} y2={r.y} className={r.c} stroke="rgba(106,180,240,0.55)" strokeWidth="1.8" strokeLinecap="round"/>
      ))}
      {/* Cursor blink */}
      <rect x="216" y="170" width="8" height="10" rx="1" fill="rgba(106,180,240,0.6)">
        <animate attributeName="opacity" values="1;0;1" dur="1.1s" repeatCount="indefinite"/>
      </rect>
    </svg>
  );
}

function VisualPolishText() {
  return (
    <svg viewBox="0 0 340 240" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <style>{`
          @keyframes pt-strike{0%{stroke-dashoffset:60}100%{stroke-dashoffset:0}}
          @keyframes pt-appear{0%{opacity:0;transform:translateY(6px)}100%{opacity:1;transform:translateY(0)}}
          @keyframes pt-pulse{0%,100%{opacity:0.5}50%{opacity:1}}
          .pt-err1{animation:pt-strike 0.5s 0.3s both;stroke-dasharray:60;stroke-dashoffset:60}
          .pt-err2{animation:pt-strike 0.5s 0.7s both;stroke-dasharray:50;stroke-dashoffset:50}
          .pt-err3{animation:pt-strike 0.5s 1.1s both;stroke-dasharray:45;stroke-dashoffset:45}
          .pt-clean{animation:pt-appear 0.5s 1.5s both}
          .pt-badge{animation:pt-pulse 2s 1.5s infinite}
        `}</style>
      </defs>
      {/* BEFORE panel — garbled text */}
      <rect x="14" y="22" width="136" height="186" rx="4" fill="rgba(168,50,50,0.07)" stroke="rgba(168,50,50,0.28)" strokeWidth="1.5"/>
      <text x="82" y="40" textAnchor="middle" fill="rgba(220,80,80,0.6)" fontSize="8" fontFamily="Inter,sans-serif" letterSpacing="2">BEFORE</text>
      {/* Garbled lines — uneven lengths mimicking OCR noise */}
      {[56,73,90,107,124,141,158,175].map((y,i)=>(
        <line key={i} x1={136-i*4} y1={y} x2="130" y2={y} stroke="rgba(240,236,227,0.2)" strokeWidth="1.8" strokeLinecap="round"/>
      ))}
      {/* Red strike-through error marks on 3 lines */}
      <line x1="26" y1="90" x2="86" y2="90" className="pt-err1" stroke="rgba(220,80,80,0.7)" strokeWidth="1.5" strokeLinecap="round"/>
      <line x1="26" y1="124" x2="72" y2="124" className="pt-err2" stroke="rgba(220,80,80,0.7)" strokeWidth="1.5" strokeLinecap="round"/>
      <line x1="26" y1="158" x2="80" y2="158" className="pt-err3" stroke="rgba(220,80,80,0.7)" strokeWidth="1.5" strokeLinecap="round"/>
      {/* Red dots on error positions */}
      {[[55,88],[88,88],[60,122],[55,156],[72,156]].map(([x,y],i)=>(
        <circle key={i} cx={x} cy={y} r="2.5" fill="rgba(220,80,80,0.55)"/>
      ))}
      {/* Center arrow */}
      <path d="M 162 112 L 180 112" stroke="rgba(201,151,58,0.6)" strokeWidth="2" strokeLinecap="round"/>
      <polygon points="178,107 188,112 178,117" fill="rgba(201,151,58,0.6)"/>
      {/* AFTER panel — clean text */}
      <g className="pt-clean">
        <rect x="192" y="22" width="136" height="186" rx="4" fill="rgba(74,124,74,0.07)" stroke="rgba(74,124,74,0.3)" strokeWidth="1.5"/>
        <text x="260" y="40" textAnchor="middle" fill="rgba(126,207,126,0.6)" fontSize="8" fontFamily="Inter,sans-serif" letterSpacing="2">AFTER</text>
        {[56,73,90,107,124,141,158,175].map((y,i)=>(
          <line key={i} x1={314-i*3} y1={y} x2="308" y2={y} stroke="rgba(240,236,227,0.35)" strokeWidth="1.8" strokeLinecap="round"/>
        ))}
        {/* Clean badge */}
        <rect x="206" y="192" width="108" height="14" rx="7" className="pt-badge" fill="rgba(74,124,74,0.15)" stroke="rgba(74,124,74,0.4)" strokeWidth="1"/>
        <text x="260" y="202" textAnchor="middle" fill="rgba(126,207,126,0.75)" fontSize="7.5" fontFamily="Inter,sans-serif" letterSpacing="1">CORRECTED ✓</text>
      </g>
    </svg>
  );
}

function VisualLearnNames() {
  return (
    <svg viewBox="0 0 340 240" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <style>{`
          @keyframes ln-rise{0%{opacity:0;transform:translateY(14px)}100%{opacity:1;transform:translateY(0)}}
          @keyframes ln-draw{0%{stroke-dashoffset:60}100%{stroke-dashoffset:0}}
          @keyframes ln-glow{0%,100%{opacity:0.5}50%{opacity:1}}
          .ln-card1{animation:ln-rise .5s .3s both}.ln-card2{animation:ln-rise .5s .9s both}.ln-card3{animation:ln-rise .5s 1.5s both}
          .ln-line1{animation:ln-draw .4s .5s both;stroke-dasharray:60;stroke-dashoffset:60}
          .ln-line2{animation:ln-draw .4s 1.1s both;stroke-dasharray:60;stroke-dashoffset:60}
          .ln-line3{animation:ln-draw .4s 1.7s both;stroke-dasharray:60;stroke-dashoffset:60}
          .ln-hl{animation:ln-glow 2s 0.2s infinite}
        `}</style>
      </defs>
      {/* Source text passage */}
      <rect x="14" y="28" width="162" height="180" rx="4" fill="rgba(240,236,227,0.04)" stroke="rgba(240,236,227,0.18)" strokeWidth="1.5"/>
      <text x="95" y="46" textAnchor="middle" fill="rgba(240,236,227,0.25)" fontSize="8" fontFamily="Inter,sans-serif" letterSpacing="2">TEXT PASSAGE</text>
      {/* Body lines */}
      {[60,74,88,102,116,130,144,158,172,186].map((y,i)=>(
        <line key={i} x1={162-i*2} y1={y} x2="158" y2={y} stroke="rgba(240,236,227,0.14)" strokeWidth="1.5" strokeLinecap="round"/>
      ))}
      {/* Highlighted names — gold glow */}
      <rect x="22" y="84" width="64" height="10" rx="2" className="ln-hl" fill="rgba(201,151,58,0.22)" stroke="rgba(201,151,58,0.5)" strokeWidth="1"/>
      <rect x="22" y="128" width="52" height="10" rx="2" className="ln-hl" fill="rgba(201,151,58,0.22)" stroke="rgba(201,151,58,0.5)" strokeWidth="1" style={{animationDelay:'0.6s'}}/>
      <rect x="22" y="172" width="72" height="10" rx="2" className="ln-hl" fill="rgba(201,151,58,0.22)" stroke="rgba(201,151,58,0.5)" strokeWidth="1" style={{animationDelay:'1.2s'}}/>
      {/* Connector lines to phonetic cards */}
      <line x1="86" y1="84" x2="188" y2="70" className="ln-line1" stroke="rgba(201,151,58,0.3)" strokeWidth="1" strokeDasharray="3 2"/>
      <line x1="74" y1="128" x2="188" y2="120" className="ln-line2" stroke="rgba(201,151,58,0.3)" strokeWidth="1" strokeDasharray="3 2"/>
      <line x1="94" y1="172" x2="188" y2="170" className="ln-line3" stroke="rgba(201,151,58,0.3)" strokeWidth="1" strokeDasharray="3 2"/>
      {/* Phonetic annotation cards — right side */}
      <g className="ln-card1">
        <rect x="188" y="52" width="138" height="36" rx="4" fill="rgba(201,151,58,0.1)" stroke="rgba(201,151,58,0.4)" strokeWidth="1.2"/>
        <text x="202" y="66" fill="rgba(201,151,58,0.9)" fontSize="11" fontFamily="Inter,sans-serif">الغزالي</text>
        <text x="202" y="80" fill="rgba(201,151,58,0.55)" fontSize="8" fontFamily="Inter,sans-serif" letterSpacing="0.5">al-GHA-za-lee</text>
      </g>
      <g className="ln-card2">
        <rect x="188" y="102" width="138" height="36" rx="4" fill="rgba(201,151,58,0.1)" stroke="rgba(201,151,58,0.4)" strokeWidth="1.2"/>
        <text x="202" y="116" fill="rgba(201,151,58,0.9)" fontSize="11" fontFamily="Inter,sans-serif">بغداد</text>
        <text x="202" y="130" fill="rgba(201,151,58,0.55)" fontSize="8" fontFamily="Inter,sans-serif" letterSpacing="0.5">bag-DAAD</text>
      </g>
      <g className="ln-card3">
        <rect x="188" y="152" width="138" height="36" rx="4" fill="rgba(201,151,58,0.1)" stroke="rgba(201,151,58,0.4)" strokeWidth="1.2"/>
        <text x="202" y="166" fill="rgba(201,151,58,0.9)" fontSize="11" fontFamily="Inter,sans-serif">إحياء العلوم</text>
        <text x="202" y="180" fill="rgba(201,151,58,0.55)" fontSize="8" fontFamily="Inter,sans-serif" letterSpacing="0.5">ih-YAA al-u-LOOM</text>
      </g>
    </svg>
  );
}

function VisualPlanEpisodes() {
  return (
    <svg viewBox="0 0 340 240" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <style>{`
          @keyframes pe-draw{0%{stroke-dashoffset:80}100%{stroke-dashoffset:0}}
          @keyframes pe-pop{0%{opacity:0;transform:scale(0.85)}100%{opacity:1;transform:scale(1)}}
          .pe-ep1{animation:pe-pop .4s .6s both}.pe-ep2{animation:pe-pop .4s 1.0s both}
          .pe-ep3{animation:pe-pop .4s 1.4s both}.pe-ep4{animation:pe-pop .4s 1.8s both}
          .pe-ln1{animation:pe-draw .5s .6s both;stroke-dasharray:80;stroke-dashoffset:80}
          .pe-ln2{animation:pe-draw .5s 1.0s both;stroke-dasharray:80;stroke-dashoffset:80}
          .pe-ln3{animation:pe-draw .5s 1.4s both;stroke-dasharray:80;stroke-dashoffset:80}
          .pe-ln4{animation:pe-draw .5s 1.8s both;stroke-dasharray:80;stroke-dashoffset:80}
        `}</style>
      </defs>
      {/* Chapter list — left */}
      <text x="22" y="32" fill="rgba(240,236,227,0.3)" fontSize="8" fontFamily="Inter,sans-serif" letterSpacing="2">CHAPTERS</text>
      {[
        {y:44,h:36,label:'الفصل الأول',sub:'Ch 1'},
        {y:88,h:28,label:'الفصل الثاني',sub:'Ch 2'},
        {y:124,h:48,label:'الفصل الثالث',sub:'Ch 3'},
        {y:180,h:24,label:'الفصل الرابع',sub:'Ch 4'},
      ].map((ch,i)=>(
        <g key={i}>
          <rect x="14" y={ch.y} width="132" height={ch.h} rx="3" fill="rgba(240,236,227,0.05)" stroke="rgba(240,236,227,0.18)" strokeWidth="1.2"/>
          <text x="26" y={ch.y+14} fill="rgba(240,236,227,0.55)" fontSize="9" fontFamily="Inter,sans-serif">{ch.label}</text>
          <text x="26" y={ch.y+26} fill="rgba(240,236,227,0.25)" fontSize="7" fontFamily="Inter,sans-serif" letterSpacing="1">{ch.sub}</text>
        </g>
      ))}
      {/* Bracket */}
      <line x1="150" y1="44" x2="160" y2="44" stroke="rgba(201,151,58,0.35)" strokeWidth="1"/>
      <line x1="160" y1="44" x2="160" y2="203" stroke="rgba(201,151,58,0.35)" strokeWidth="1"/>
      <line x1="150" y1="203" x2="160" y2="203" stroke="rgba(201,151,58,0.35)" strokeWidth="1"/>
      {/* Connector lines to episodes */}
      <line x1="160" y1="62" x2="178" y2="62" className="pe-ln1" stroke="rgba(201,151,58,0.4)" strokeWidth="1" strokeDasharray="4 2"/>
      <line x1="160" y1="102" x2="178" y2="102" className="pe-ln2" stroke="rgba(201,151,58,0.4)" strokeWidth="1" strokeDasharray="4 2"/>
      <line x1="160" y1="148" x2="178" y2="148" className="pe-ln3" stroke="rgba(201,151,58,0.4)" strokeWidth="1" strokeDasharray="4 2"/>
      <line x1="160" y1="192" x2="178" y2="192" className="pe-ln4" stroke="rgba(201,151,58,0.4)" strokeWidth="1" strokeDasharray="4 2"/>
      {/* Episode cards — right */}
      <text x="188" y="32" fill="rgba(201,151,58,0.4)" fontSize="8" fontFamily="Inter,sans-serif" letterSpacing="2">EPISODES</text>
      {[
        {y:44,label:'Ep 1',sub:'The Opening Letter',cls:'pe-ep1'},
        {y:84,label:'Ep 2',sub:'Knowledge & Action',cls:'pe-ep2'},
        {y:124,label:'Ep 3',sub:'The Inner Journey',cls:'pe-ep3'},
        {y:164,label:'Ep 4',sub:'The Final Counsel',cls:'pe-ep4'},
      ].map((ep,i)=>(
        <g key={i} className={ep.cls}>
          <rect x="178" y={ep.y} width="148" height="32" rx="4" fill="rgba(201,151,58,0.09)" stroke="rgba(201,151,58,0.38)" strokeWidth="1.3"/>
          <text x="192" y={ep.y+14} fill="rgba(201,151,58,0.75)" fontSize="9" fontFamily="Inter,sans-serif" fontWeight="600">{ep.label}</text>
          <text x="192" y={ep.y+26} fill="rgba(201,151,58,0.4)" fontSize="7.5" fontFamily="Inter,sans-serif">{ep.sub}</text>
        </g>
      ))}
    </svg>
  );
}

function VisualEnrich() {
  return (
    <svg viewBox="0 0 340 240" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <style>{`
          @keyframes en-float{0%{opacity:0;transform:translateX(-10px)}100%{opacity:1;transform:translateX(0)}}
          @keyframes en-floatr{0%{opacity:0;transform:translateX(10px)}100%{opacity:1;transform:translateX(0)}}
          @keyframes en-pulse{0%,100%{opacity:0.6}50%{opacity:1}}
          .en-c1{animation:en-float .5s .3s both}.en-c2{animation:en-floatr .5s .9s both}
          .en-c3{animation:en-float .5s 1.5s both}.en-c4{animation:en-floatr .5s 2.1s both}
          .en-dot{animation:en-pulse 1.8s infinite}
        `}</style>
      </defs>
      {/* Central document */}
      <rect x="114" y="22" width="112" height="192" rx="4" fill="rgba(240,236,227,0.04)" stroke="rgba(240,236,227,0.22)" strokeWidth="1.5"/>
      {[40,56,72,88,104,120,136,152,168,184].map((y,i)=>(
        <line key={i} x1={208-i*2} y1={y} x2="204" y2={y} stroke="rgba(240,236,227,0.13)" strokeWidth="1.5" strokeLinecap="round"/>
      ))}
      <text x="170" y="222" textAnchor="middle" fill="rgba(240,236,227,0.2)" fontSize="7.5" fontFamily="Inter,sans-serif" letterSpacing="2">SOURCE</text>
      {/* Annotation cards — left */}
      <g className="en-c1">
        <rect x="8" y="32" width="98" height="44" rx="5" fill="rgba(26,92,138,0.1)" stroke="rgba(106,180,240,0.35)" strokeWidth="1.2"/>
        <text x="57" y="48" textAnchor="middle" fill="rgba(106,180,240,0.55)" fontSize="7.5" fontFamily="Inter,sans-serif" letterSpacing="1">HISTORICAL</text>
        <text x="57" y="62" textAnchor="middle" fill="rgba(106,180,240,0.55)" fontSize="7.5" fontFamily="Inter,sans-serif" letterSpacing="1">CONTEXT</text>
        <line x1="106" y1="54" x2="114" y2="54" stroke="rgba(106,180,240,0.2)" strokeWidth="1" strokeDasharray="3 2"/>
        <circle cx="106" cy="54" r="2" className="en-dot" fill="rgba(106,180,240,0.6)"/>
      </g>
      <g className="en-c3">
        <rect x="8" y="138" width="98" height="44" rx="5" fill="rgba(139,69,19,0.1)" stroke="rgba(201,151,58,0.35)" strokeWidth="1.2"/>
        <text x="57" y="154" textAnchor="middle" fill="rgba(201,151,58,0.55)" fontSize="7.5" fontFamily="Inter,sans-serif" letterSpacing="1">KEY TERM</text>
        <text x="57" y="168" textAnchor="middle" fill="rgba(201,151,58,0.45)" fontSize="8" fontFamily="Inter,sans-serif">التوكل</text>
        <line x1="106" y1="160" x2="114" y2="128" stroke="rgba(201,151,58,0.2)" strokeWidth="1" strokeDasharray="3 2"/>
        <circle cx="106" cy="160" r="2" className="en-dot" fill="rgba(201,151,58,0.6)" style={{animationDelay:'0.8s'}}/>
      </g>
      {/* Annotation cards — right */}
      <g className="en-c2">
        <rect x="234" y="32" width="98" height="44" rx="5" fill="rgba(74,124,74,0.1)" stroke="rgba(74,124,74,0.35)" strokeWidth="1.2"/>
        <text x="283" y="48" textAnchor="middle" fill="rgba(126,207,126,0.55)" fontSize="7.5" fontFamily="Inter,sans-serif" letterSpacing="1">QURAN</text>
        <text x="283" y="62" textAnchor="middle" fill="rgba(126,207,126,0.55)" fontSize="7.5" fontFamily="Inter,sans-serif" letterSpacing="1">REFERENCE</text>
        <line x1="234" y1="54" x2="226" y2="54" stroke="rgba(74,124,74,0.2)" strokeWidth="1" strokeDasharray="3 2"/>
        <circle cx="234" cy="54" r="2" className="en-dot" fill="rgba(74,124,74,0.6)" style={{animationDelay:'0.4s'}}/>
      </g>
      <g className="en-c4">
        <rect x="234" y="138" width="98" height="44" rx="5" fill="rgba(168,50,50,0.08)" stroke="rgba(220,80,80,0.3)" strokeWidth="1.2"/>
        <text x="283" y="154" textAnchor="middle" fill="rgba(220,80,80,0.55)" fontSize="7.5" fontFamily="Inter,sans-serif" letterSpacing="1">SCHOLAR</text>
        <text x="283" y="168" textAnchor="middle" fill="rgba(220,80,80,0.55)" fontSize="7.5" fontFamily="Inter,sans-serif" letterSpacing="1">NOTE</text>
        <line x1="234" y1="160" x2="226" y2="128" stroke="rgba(220,80,80,0.2)" strokeWidth="1" strokeDasharray="3 2"/>
        <circle cx="234" cy="160" r="2" className="en-dot" fill="rgba(220,80,80,0.6)" style={{animationDelay:'1.2s'}}/>
      </g>
    </svg>
  );
}

function VisualOutsideKnowledge() {
  return (
    <svg viewBox="0 0 340 240" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <style>{`
          @keyframes ok-check{0%{stroke-dashoffset:20}100%{stroke-dashoffset:0}}
          @keyframes ok-slide{0%{opacity:0;transform:translateX(12px)}100%{opacity:1;transform:translateX(0)}}
          @keyframes ok-pulse{0%,100%{opacity:0.4}50%{opacity:0.9}}
          .ok-v1{animation:ok-slide .4s .2s both}.ok-v2{animation:ok-slide .4s .7s both}.ok-v3{animation:ok-slide .4s 1.2s both}
          .ok-ck1{animation:ok-check .3s .6s both;stroke-dasharray:20;stroke-dashoffset:20}
          .ok-ck2{animation:ok-check .3s 1.1s both;stroke-dasharray:20;stroke-dashoffset:20}
          .ok-ck3{animation:ok-check .3s 1.6s both;stroke-dasharray:20;stroke-dashoffset:20}
          .ok-hl{animation:ok-pulse 2s infinite}
        `}</style>
      </defs>
      {/* Document — left panel */}
      <rect x="14" y="22" width="152" height="194" rx="4" fill="rgba(240,236,227,0.04)" stroke="rgba(240,236,227,0.2)" strokeWidth="1.5"/>
      <text x="90" y="40" textAnchor="middle" fill="rgba(240,236,227,0.25)" fontSize="8" fontFamily="Inter,sans-serif" letterSpacing="2">EPISODE TEXT</text>
      {/* Text lines with 3 citation-marked spans */}
      {[56,72,88,104,120,136,152,168,184].map((y,i)=>(
        <line key={i} x1={152-i*3} y1={y} x2="148" y2={y} stroke="rgba(240,236,227,0.12)" strokeWidth="1.5" strokeLinecap="round"/>
      ))}
      {/* Gold citation highlights */}
      <rect x="22" y="82" width="72" height="10" rx="2" className="ok-hl" fill="rgba(201,151,58,0.18)" stroke="rgba(201,151,58,0.45)" strokeWidth="1"/>
      <text x="26" y="91" fill="rgba(201,151,58,0.65)" fontSize="7" fontFamily="Inter,sans-serif">[1] Quran 39:9</text>
      <rect x="22" y="130" width="78" height="10" rx="2" className="ok-hl" fill="rgba(201,151,58,0.18)" stroke="rgba(201,151,58,0.45)" strokeWidth="1" style={{animationDelay:'0.5s'}}/>
      <text x="26" y="139" fill="rgba(201,151,58,0.65)" fontSize="7" fontFamily="Inter,sans-serif">[2] Bukhari 79</text>
      <rect x="22" y="176" width="84" height="10" rx="2" className="ok-hl" fill="rgba(201,151,58,0.18)" stroke="rgba(201,151,58,0.45)" strokeWidth="1" style={{animationDelay:'1.0s'}}/>
      <text x="26" y="185" fill="rgba(201,151,58,0.65)" fontSize="7" fontFamily="Inter,sans-serif">[3] al-Nawawi</text>
      {/* Arrow */}
      <path d="M 172 112 L 188 112" stroke="rgba(201,151,58,0.55)" strokeWidth="2" strokeLinecap="round"/>
      <polygon points="186,107 196,112 186,117" fill="rgba(201,151,58,0.55)"/>
      {/* Verified source cards — right */}
      {[
        {y:46,label:'Quran 39:9',sub:'وَقُل رَّبِّ زِدْنِي عِلْمًا',color:'rgba(74,124,74,',tc:'rgba(126,207,126,',cls:'ok-v1',cck:'ok-ck1'},
        {y:106,label:'Bukhari No. 79',sub:'Hadith on knowledge',color:'rgba(26,92,138,',tc:'rgba(106,180,240,',cls:'ok-v2',cck:'ok-ck2'},
        {y:166,label:'al-Nawawi',sub:'Riyad al-Salihin',color:'rgba(201,151,58,',tc:'rgba(201,151,58,',cls:'ok-v3',cck:'ok-ck3'},
      ].map((c,i)=>(
        <g key={i} className={c.cls}>
          <rect x="200" y={c.y} width="126" height="50" rx="5" fill={`${c.color}0.09)`} stroke={`${c.color}0.35)`} strokeWidth="1.2"/>
          <text x="214" y={c.y+16} fill={`${c.tc}0.75)`} fontSize="8.5" fontFamily="Inter,sans-serif" fontWeight="600">{c.label}</text>
          <text x="214" y={c.y+30} fill={`${c.tc}0.45)`} fontSize="8" fontFamily="Inter,sans-serif">{c.sub}</text>
          {/* Check badge */}
          <circle cx="310" cy={c.y+40} r="10" fill={`${c.color}0.15)`} stroke={`${c.color}0.5)`} strokeWidth="1.2"/>
          <polyline points={`304,${c.y+40} 308,${c.y+44} 316,${c.y+36}`} className={c.cck}
            fill="none" stroke={`${c.tc}0.9)`} strokeWidth="1.8" strokeLinecap="round"/>
        </g>
      ))}
    </svg>
  );
}

function VisualCutPieces() {
  return (
    <svg viewBox="0 0 340 240" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <style>{`
          @keyframes cp-cut{0%{transform:translateY(-20px);opacity:0}60%{transform:translateY(0);opacity:1}100%{transform:translateY(0);opacity:1}}
          @keyframes cp-drop{0%{opacity:0;transform:translateY(-8px)}100%{opacity:1;transform:translateY(0)}}
          @keyframes cp-dash{0%{stroke-dashoffset:200}100%{stroke-dashoffset:0}}
          .cp-blade1{animation:cp-cut .4s .3s both}.cp-blade2{animation:cp-cut .4s .8s both}.cp-blade3{animation:cp-cut .4s 1.3s both}
          .cp-pk1{animation:cp-drop .4s .7s both}.cp-pk2{animation:cp-drop .4s 1.2s both}.cp-pk3{animation:cp-drop .4s 1.7s both}.cp-pk4{animation:cp-drop .4s 2.2s both}
          .cp-cut1{animation:cp-dash .5s .3s both;stroke-dasharray:200;stroke-dashoffset:200}
          .cp-cut2{animation:cp-dash .5s .8s both;stroke-dasharray:200;stroke-dashoffset:200}
          .cp-cut3{animation:cp-dash .5s 1.3s both;stroke-dasharray:200;stroke-dashoffset:200}
        `}</style>
      </defs>
      {/* Full scroll — the complete book text */}
      <rect x="14" y="28" width="312" height="58" rx="4" fill="rgba(240,236,227,0.04)" stroke="rgba(240,236,227,0.2)" strokeWidth="1.5"/>
      <text x="170" y="44" textAnchor="middle" fill="rgba(240,236,227,0.25)" fontSize="8" fontFamily="Inter,sans-serif" letterSpacing="2">أيها الولد — FULL TEXT</text>
      {[52,64,76].map((y,i)=>(
        <line key={i} x1="28" y1={y} x2="302" y2={y} stroke="rgba(240,236,227,0.1)" strokeWidth="1.2" strokeLinecap="round"/>
      ))}
      {/* Cut lines — vertical dashed */}
      <line x1="100" y1="20" x2="100" y2="98" className="cp-cut1" stroke="rgba(201,151,58,0.6)" strokeWidth="1.5" strokeDasharray="4 3"/>
      <line x1="190" y1="20" x2="190" y2="98" className="cp-cut2" stroke="rgba(201,151,58,0.6)" strokeWidth="1.5" strokeDasharray="4 3"/>
      <line x1="265" y1="20" x2="265" y2="98" className="cp-cut3" stroke="rgba(201,151,58,0.6)" strokeWidth="1.5" strokeDasharray="4 3"/>
      {/* Blade icons */}
      <g className="cp-blade1">
        <polygon points="96,16 100,24 104,16" fill="rgba(201,151,58,0.7)"/>
        <rect x="98" y="12" width="4" height="6" rx="1" fill="rgba(201,151,58,0.4)"/>
      </g>
      <g className="cp-blade2">
        <polygon points="186,16 190,24 194,16" fill="rgba(201,151,58,0.7)"/>
        <rect x="188" y="12" width="4" height="6" rx="1" fill="rgba(201,151,58,0.4)"/>
      </g>
      <g className="cp-blade3">
        <polygon points="261,16 265,24 269,16" fill="rgba(201,151,58,0.7)"/>
        <rect x="263" y="12" width="4" height="6" rx="1" fill="rgba(201,151,58,0.4)"/>
      </g>
      {/* Result — 4 episode packets below */}
      {[
        {x:14,w:80,label:'Ep 1',sub:'Opening',cls:'cp-pk1'},
        {x:102,w:82,label:'Ep 2',sub:'Knowledge',cls:'cp-pk2'},
        {x:192,w:68,label:'Ep 3',sub:'Practice',cls:'cp-pk3'},
        {x:268,w:58,label:'Ep 4',sub:'Close',cls:'cp-pk4'},
      ].map((p,i)=>(
        <g key={i} className={p.cls}>
          <line x1={p.x+p.w/2} y1="98" x2={p.x+p.w/2} y2="112" stroke="rgba(201,151,58,0.25)" strokeWidth="1"/>
          <rect x={p.x+2} y="112" width={p.w-4} height="64" rx="4" fill="rgba(201,151,58,0.09)" stroke="rgba(201,151,58,0.38)" strokeWidth="1.3"/>
          <text x={p.x+p.w/2} y="138" textAnchor="middle" fill="rgba(201,151,58,0.8)" fontSize="10" fontFamily="Inter,sans-serif" fontWeight="600">{p.label}</text>
          <text x={p.x+p.w/2} y="154" textAnchor="middle" fill="rgba(201,151,58,0.4)" fontSize="7.5" fontFamily="Inter,sans-serif">{p.sub}</text>
          {/* Stack lines */}
          <line x1={p.x+8} y1="168" x2={p.x+p.w-12} y2="168" stroke="rgba(240,236,227,0.1)" strokeWidth="1" strokeLinecap="round"/>
          <line x1={p.x+8} y1="174" x2={p.x+p.w-16} y2="174" stroke="rgba(240,236,227,0.08)" strokeWidth="1" strokeLinecap="round"/>
        </g>
      ))}
    </svg>
  );
}

function VisualNarratorFraming() {
  return (
    <svg viewBox="0 0 340 240" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <style>{`
          @keyframes nf-appear{0%{opacity:0;transform:translateY(5px)}100%{opacity:1;transform:translateY(0)}}
          @keyframes nf-pulse{0%,100%{r:18;opacity:0.5}50%{r:24;opacity:0.15}}
          @keyframes nf-talk{0%,100%{opacity:0;transform:scale(0.8)}20%,80%{opacity:1;transform:scale(1)}}
          .nf-line1{animation:nf-appear .35s .4s both}.nf-line2{animation:nf-appear .35s .7s both}
          .nf-line3{animation:nf-appear .35s 1.0s both}.nf-line4{animation:nf-appear .35s 1.3s both}
          .nf-bubble1{animation:nf-talk 2.4s 1.8s infinite}.nf-bubble2{animation:nf-talk 2.4s 2.6s infinite}
        `}</style>
      </defs>
      {/* Episode content card — left */}
      <rect x="14" y="22" width="110" height="152" rx="4" fill="rgba(240,236,227,0.04)" stroke="rgba(240,236,227,0.18)" strokeWidth="1.5"/>
      <text x="69" y="40" textAnchor="middle" fill="rgba(240,236,227,0.25)" fontSize="7.5" fontFamily="Inter,sans-serif" letterSpacing="2">EPISODE</text>
      {[54,68,82,96,110,124,138,154].map((y,i)=>(
        <line key={i} x1={106-i*2} y1={y} x2="102" y2={y} stroke="rgba(240,236,227,0.12)" strokeWidth="1.4" strokeLinecap="round"/>
      ))}
      {/* Arrow → */}
      <path d="M 130 98 L 150 98" stroke="rgba(201,151,58,0.5)" strokeWidth="2" strokeLinecap="round"/>
      <polygon points="148,93 158,98 148,103" fill="rgba(201,151,58,0.5)"/>
      {/* Briefing card — center */}
      <rect x="162" y="22" width="120" height="152" rx="4" fill="rgba(26,92,138,0.08)" stroke="rgba(106,180,240,0.28)" strokeWidth="1.5"/>
      <text x="222" y="40" textAnchor="middle" fill="rgba(106,180,240,0.5)" fontSize="7.5" fontFamily="Inter,sans-serif" letterSpacing="2">HOST BRIEFING</text>
      <g className="nf-line1"><line x1="176" y1="56" x2="266" y2="56" stroke="rgba(106,180,240,0.4)" strokeWidth="1.5" strokeLinecap="round"/></g>
      <g className="nf-line2"><line x1="176" y1="70" x2="252" y2="70" stroke="rgba(106,180,240,0.3)" strokeWidth="1.3" strokeLinecap="round"/></g>
      <g className="nf-line3"><line x1="176" y1="84" x2="260" y2="84" stroke="rgba(106,180,240,0.3)" strokeWidth="1.3" strokeLinecap="round"/></g>
      <g className="nf-line4"><line x1="176" y1="98" x2="244" y2="98" stroke="rgba(106,180,240,0.25)" strokeWidth="1.2" strokeLinecap="round"/></g>
      {[112,126,140].map((y,i)=>(
        <line key={i} x1="176" y1={y} x2={248-i*8} y2={y} stroke="rgba(106,180,240,0.15)" strokeWidth="1.1" strokeLinecap="round"/>
      ))}
      {/* Arrow ↓ to hosts */}
      <line x1="222" y1="176" x2="222" y2="192" stroke="rgba(106,180,240,0.35)" strokeWidth="1.5" strokeDasharray="3 2"/>
      <polygon points="218,190 222,197 226,190" fill="rgba(106,180,240,0.35)"/>
      {/* Host A — gold mic */}
      <circle cx="100" cy="218" r="14" fill="rgba(201,151,58,0.1)" stroke="rgba(201,151,58,0.45)" strokeWidth="1.5"/>
      <rect x="95" y="209" width="10" height="14" rx="5" fill="rgba(201,151,58,0.3)"/>
      <path d="M 90 221 Q 90 232 100 232 Q 110 232 110 221" fill="none" stroke="rgba(201,151,58,0.4)" strokeWidth="1.2"/>
      <text x="100" y="240" textAnchor="middle" fill="rgba(201,151,58,0.5)" fontSize="7" fontFamily="Inter,sans-serif">Host A</text>
      {/* Speech bubble A */}
      <g className="nf-bubble1">
        <rect x="116" y="205" width="42" height="16" rx="8" fill="rgba(201,151,58,0.15)" stroke="rgba(201,151,58,0.4)" strokeWidth="1"/>
        <text x="137" y="216" textAnchor="middle" fill="rgba(201,151,58,0.7)" fontSize="7" fontFamily="Inter,sans-serif">...</text>
      </g>
      {/* Host B — blue mic */}
      <circle cx="286" cy="218" r="14" fill="rgba(106,180,240,0.1)" stroke="rgba(106,180,240,0.45)" strokeWidth="1.5"/>
      <rect x="281" y="209" width="10" height="14" rx="5" fill="rgba(106,180,240,0.3)"/>
      <path d="M 276 221 Q 276 232 286 232 Q 296 232 296 221" fill="none" stroke="rgba(106,180,240,0.4)" strokeWidth="1.2"/>
      <text x="286" y="240" textAnchor="middle" fill="rgba(106,180,240,0.5)" fontSize="7" fontFamily="Inter,sans-serif">Host B</text>
      {/* Speech bubble B */}
      <g className="nf-bubble2">
        <rect x="182" y="205" width="42" height="16" rx="8" fill="rgba(106,180,240,0.15)" stroke="rgba(106,180,240,0.4)" strokeWidth="1"/>
        <text x="203" y="216" textAnchor="middle" fill="rgba(106,180,240,0.7)" fontSize="7" fontFamily="Inter,sans-serif">...</text>
      </g>
    </svg>
  );
}

function VisualSlides() {
  return (
    <svg viewBox="0 0 340 240" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <style>{`
          @keyframes sl-pop{0%{opacity:0;transform:scale(0.9)}100%{opacity:1;transform:scale(1)}}
          .sl-s1{animation:sl-pop .4s .1s both}.sl-s2{animation:sl-pop .4s .5s both}
          .sl-s3{animation:sl-pop .4s .9s both}.sl-s4{animation:sl-pop .4s 1.3s both}
        `}</style>
      </defs>
      {/* 2×2 slide grid */}
      {/* Slide 1 — Hierarchy diagram (top-left) */}
      <g className="sl-s1">
        <rect x="14" y="18" width="152" height="96" rx="4" fill="rgba(26,92,138,0.08)" stroke="rgba(106,180,240,0.28)" strokeWidth="1.3"/>
        <text x="90" y="34" textAnchor="middle" fill="rgba(106,180,240,0.5)" fontSize="7.5" fontFamily="Inter,sans-serif" letterSpacing="1">HIERARCHY</text>
        {/* Tree diagram */}
        <rect x="74" y="42" width="32" height="14" rx="3" fill="rgba(106,180,240,0.15)" stroke="rgba(106,180,240,0.3)" strokeWidth="1"/>
        <text x="90" y="52" textAnchor="middle" fill="rgba(106,180,240,0.7)" fontSize="7" fontFamily="Inter,sans-serif">Root</text>
        <line x1="90" y1="56" x2="56" y2="68" stroke="rgba(106,180,240,0.25)" strokeWidth="1"/>
        <line x1="90" y1="56" x2="90" y2="68" stroke="rgba(106,180,240,0.25)" strokeWidth="1"/>
        <line x1="90" y1="56" x2="124" y2="68" stroke="rgba(106,180,240,0.25)" strokeWidth="1"/>
        {[[40,68,22],[74,68,22],[108,68,22]].map(([x,y,w],i)=>(
          <rect key={i} x={x} y={y} width={w} height="10" rx="2" fill="rgba(106,180,240,0.1)" stroke="rgba(106,180,240,0.2)" strokeWidth="0.8"/>
        ))}
        <text x="90" y="96" textAnchor="middle" fill="rgba(106,180,240,0.3)" fontSize="7" fontFamily="Inter,sans-serif" letterSpacing="1">SLIDE 1</text>
      </g>
      {/* Slide 2 — Quote card (top-right) */}
      <g className="sl-s2">
        <rect x="174" y="18" width="152" height="96" rx="4" fill="rgba(201,151,58,0.07)" stroke="rgba(201,151,58,0.28)" strokeWidth="1.3"/>
        <text x="250" y="34" textAnchor="middle" fill="rgba(201,151,58,0.5)" fontSize="7.5" fontFamily="Inter,sans-serif" letterSpacing="1">QUOTE</text>
        <text x="187" y="56" fill="rgba(201,151,58,0.7)" fontSize="22" fontFamily="Georgia,serif">"</text>
        <line x1="210" y1="54" x2="304" y2="54" stroke="rgba(201,151,58,0.25)" strokeWidth="1.2" strokeLinecap="round"/>
        <line x1="210" y1="64" x2="292" y2="64" stroke="rgba(201,151,58,0.2)" strokeWidth="1.1" strokeLinecap="round"/>
        <line x1="210" y1="74" x2="298" y2="74" stroke="rgba(201,151,58,0.2)" strokeWidth="1.1" strokeLinecap="round"/>
        <line x1="240" y1="84" x2="310" y2="84" stroke="rgba(201,151,58,0.15)" strokeWidth="1" strokeLinecap="round"/>
        <text x="250" y="96" textAnchor="middle" fill="rgba(201,151,58,0.3)" fontSize="7" fontFamily="Inter,sans-serif" letterSpacing="1">SLIDE 2</text>
      </g>
      {/* Slide 3 — Timeline (bottom-left) */}
      <g className="sl-s3">
        <rect x="14" y="126" width="152" height="96" rx="4" fill="rgba(74,124,74,0.07)" stroke="rgba(74,124,74,0.28)" strokeWidth="1.3"/>
        <text x="90" y="142" textAnchor="middle" fill="rgba(126,207,126,0.5)" fontSize="7.5" fontFamily="Inter,sans-serif" letterSpacing="1">TIMELINE</text>
        <line x1="28" y1="176" x2="148" y2="176" stroke="rgba(126,207,126,0.3)" strokeWidth="1.5" strokeLinecap="round"/>
        {[28,62,96,130].map((x,i)=>(
          <g key={i}>
            <circle cx={x} cy="176" r="4" fill="rgba(74,124,74,0.2)" stroke="rgba(126,207,126,0.5)" strokeWidth="1"/>
            <line x1={x} y1="165" x2={x} y2="172" stroke="rgba(126,207,126,0.25)" strokeWidth="1"/>
            <rect x={x-14} y="152" width="28" height="12" rx="2" fill="rgba(74,124,74,0.15)" stroke="rgba(74,124,74,0.25)" strokeWidth="0.8"/>
          </g>
        ))}
        <text x="90" y="212" textAnchor="middle" fill="rgba(74,124,74,0.3)" fontSize="7" fontFamily="Inter,sans-serif" letterSpacing="1">SLIDE 3</text>
      </g>
      {/* Slide 4 — Comparison table (bottom-right) */}
      <g className="sl-s4">
        <rect x="174" y="126" width="152" height="96" rx="4" fill="rgba(139,69,19,0.07)" stroke="rgba(201,151,58,0.22)" strokeWidth="1.3"/>
        <text x="250" y="142" textAnchor="middle" fill="rgba(201,151,58,0.4)" fontSize="7.5" fontFamily="Inter,sans-serif" letterSpacing="1">COMPARISON</text>
        {/* Table grid */}
        {[154,170,186,202].map((y,i)=>(
          <line key={i} x1="188" y1={y} x2="314" y2={y} stroke="rgba(201,151,58,0.15)" strokeWidth="0.8"/>
        ))}
        <line x1="250" y1="152" x2="250" y2="206" stroke="rgba(201,151,58,0.15)" strokeWidth="0.8"/>
        <text x="220" y="164" textAnchor="middle" fill="rgba(201,151,58,0.45)" fontSize="7" fontFamily="Inter,sans-serif">Before</text>
        <text x="282" y="164" textAnchor="middle" fill="rgba(201,151,58,0.45)" fontSize="7" fontFamily="Inter,sans-serif">After</text>
        {[176,192].map((y,i)=>(
          <g key={i}>
            <line x1="192" y1={y} x2="244" y2={y} stroke="rgba(240,236,227,0.1)" strokeWidth="1"/>
            <line x1="256" y1={y} x2="308" y2={y} stroke="rgba(240,236,227,0.1)" strokeWidth="1"/>
          </g>
        ))}
        <text x="250" y="212" textAnchor="middle" fill="rgba(201,151,58,0.3)" fontSize="7" fontFamily="Inter,sans-serif" letterSpacing="1">SLIDE 4</text>
      </g>
    </svg>
  );
}

function VisualAudit() {
  return (
    <svg viewBox="0 0 340 240" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <style>{`
          @keyframes au-check{0%{stroke-dashoffset:22}100%{stroke-dashoffset:0}}
          @keyframes au-amber{0%,60%{fill:rgba(220,160,30,0.25);stroke:rgba(220,160,30,0.55)}100%{fill:rgba(74,124,74,0.2);stroke:rgba(74,124,74,0.55)}}
          @keyframes au-amberx{0%,60%{opacity:1}100%{opacity:0}}
          @keyframes au-ambertick{0%,60%{opacity:0;stroke-dashoffset:22}100%{opacity:1;stroke-dashoffset:0}}
          @keyframes au-loop{0%{stroke-dashoffset:480}100%{stroke-dashoffset:0}}
          @keyframes au-count{0%{opacity:0}100%{opacity:1}}
          .au-ck{animation:au-check .3s both;stroke-dasharray:22;stroke-dashoffset:22}
          .au-ck1{animation-delay:.2s}.au-ck2{animation-delay:.55s}.au-ck3{animation-delay:.9s}
          .au-warn{animation:au-amber 1.2s 1.8s both}
          .au-warnx{animation:au-amberx 1.2s 1.8s both}
          .au-warntick{animation:au-ambertick 0.35s 2.8s both;stroke-dasharray:22;stroke-dashoffset:22}
          .au-loop{animation:au-loop 2s 0.1s both;stroke-dasharray:480;stroke-dashoffset:480}
          .au-pass{animation:au-count .4s 3.2s both;opacity:0}
        `}</style>
      </defs>
      {/* Checklist — left */}
      <text x="22" y="32" fill="rgba(240,236,227,0.3)" fontSize="8" fontFamily="Inter,sans-serif" letterSpacing="2">QUALITY CHECKS</text>
      {[
        {y:48,label:'Citation accuracy',cls:'au-ck au-ck1',green:true},
        {y:82,label:'Narrative integrity',cls:'au-ck au-ck2',green:true},
        {y:116,label:'Coverage complete',cls:'au-ck au-ck3',green:true},
        {y:150,label:'Enrichment depth',amber:true},
        {y:184,label:'Audio alignment',amber:true},
      ].map((item,i)=>(
        <g key={i}>
          <rect x="14" y={item.y} width="170" height="26" rx="4"
            className={item.amber ? 'au-warn' : ''}
            fill={item.green ? 'rgba(74,124,74,0.1)' : 'rgba(220,160,30,0.1)'}
            stroke={item.green ? 'rgba(74,124,74,0.3)' : 'rgba(220,160,30,0.35)'}
            strokeWidth="1.2"/>
          <text x="36" y={item.y+17} fill="rgba(240,236,227,0.55)" fontSize="8.5" fontFamily="Inter,sans-serif">{item.label}</text>
          {/* Check circle */}
          <circle cx={item.amber ? 190 : 190} cy={item.y+13} r="9"
            className={item.amber ? 'au-warn' : ''}
            fill={item.green ? 'rgba(74,124,74,0.2)' : 'rgba(220,160,30,0.2)'}
            stroke={item.green ? 'rgba(74,124,74,0.55)' : 'rgba(220,160,30,0.55)'}
            strokeWidth="1.2"/>
          {item.green && (
            <polyline points={`184,${item.y+13} 188,${item.y+17} 196,${item.y+9}`}
              className={`au-ck ${item.y===48 ? 'au-ck1' : item.y===82 ? 'au-ck2' : 'au-ck3'}`}
              fill="none" stroke="rgba(126,207,126,0.9)" strokeWidth="1.8" strokeLinecap="round"/>
          )}
          {item.amber && (
            <>
              <text x="190" y={item.y+17} textAnchor="middle" className="au-warnx"
                fill="rgba(220,160,30,0.85)" fontSize="10" fontFamily="Inter,sans-serif">!</text>
              <polyline points={`184,${item.y+13} 188,${item.y+17} 196,${item.y+9}`}
                className="au-warntick"
                fill="none" stroke="rgba(126,207,126,0.9)" strokeWidth="1.8" strokeLinecap="round"
                style={{opacity:0}}/>
            </>
          )}
        </g>
      ))}
      {/* Loop arrow — right side */}
      <text x="248" y="32" textAnchor="middle" fill="rgba(240,236,227,0.2)" fontSize="8" fontFamily="Inter,sans-serif" letterSpacing="2">LOOP</text>
      <circle cx="260" cy="130" r="52" fill="none" stroke="rgba(201,151,58,0.08)" strokeWidth="1" strokeDasharray="3 4"/>
      <path d="M 260 78 A 52 52 0 1 0 259 85" className="au-loop"
        fill="none" stroke="rgba(201,151,58,0.4)" strokeWidth="2"/>
      <polygon points="255,82 261,75 267,83" fill="rgba(201,151,58,0.55)"/>
      <text x="260" y="122" textAnchor="middle" fill="rgba(201,151,58,0.6)" fontSize="10" fontFamily="Inter,sans-serif">up to</text>
      <text x="260" y="138" textAnchor="middle" fill="rgba(201,151,58,0.9)" fontSize="22" fontFamily="Inter,sans-serif" fontWeight="700">15×</text>
      <g className="au-pass">
        <rect x="222" y="186" width="76" height="20" rx="10" fill="rgba(74,124,74,0.15)" stroke="rgba(74,124,74,0.5)" strokeWidth="1.2"/>
        <text x="260" y="199" textAnchor="middle" fill="rgba(126,207,126,0.85)" fontSize="8" fontFamily="Inter,sans-serif" letterSpacing="1">PASSED ✓</text>
      </g>
    </svg>
  );
}

function VisualShip() {
  return (
    <svg viewBox="0 0 340 240" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <style>{`
          @keyframes sh-fade{0%{opacity:1}100%{opacity:0.25}}
          @keyframes sh-slide{0%{opacity:0;transform:translateX(16px)}100%{opacity:1;transform:translateX(0)}}
          @keyframes sh-seal{0%{opacity:0;transform:scale(0) rotate(-30deg)}100%{opacity:1;transform:scale(1) rotate(0)}}
          @keyframes sh-ep{0%{opacity:0;transform:translateY(-4px)}100%{opacity:1;transform:translateY(0)}}
          .sh-draft{animation:sh-fade .8s .5s both}
          .sh-card{animation:sh-slide .5s .8s both}
          .sh-seal{animation:sh-seal .55s 1.4s both;transform-origin:279px 78px}
          .sh-ep1{animation:sh-ep .3s 1.5s both}.sh-ep2{animation:sh-ep .3s 1.8s both}
          .sh-ep3{animation:sh-ep .3s 2.1s both}.sh-ep4{animation:sh-ep .3s 2.4s both}
        `}</style>
      </defs>
      {/* DRAFT stack — left, fading */}
      <g className="sh-draft">
        {[6,3,0].map((offset,i)=>(
          <rect key={i} x={18+offset} y={22-offset} width="120" height="168" rx="4"
            fill="rgba(240,236,227,0.03)" stroke="rgba(240,236,227,0.12)" strokeWidth="1.2"/>
        ))}
        {/* DRAFT watermark diagonal */}
        <text x="78" y="120" textAnchor="middle" fill="rgba(220,80,80,0.2)" fontSize="28"
          fontFamily="Inter,sans-serif" fontWeight="700"
          transform="rotate(-30, 78, 120)">DRAFT</text>
        <text x="78" y="218" textAnchor="middle" fill="rgba(240,236,227,0.2)" fontSize="8" fontFamily="Inter,sans-serif" letterSpacing="2">IN WORKSHOP</text>
      </g>
      {/* Arrow */}
      <path d="M 152 112 L 172 112" stroke="rgba(201,151,58,0.55)" strokeWidth="2" strokeLinecap="round"/>
      <polygon points="170,107 180,112 170,117" fill="rgba(201,151,58,0.55)"/>
      {/* Published catalog card — right */}
      <g className="sh-card">
        <rect x="186" y="22" width="140" height="196" rx="5" fill="rgba(201,151,58,0.08)" stroke="rgba(201,151,58,0.4)" strokeWidth="1.5"/>
        {/* Book title */}
        <text x="256" y="46" textAnchor="middle" fill="rgba(201,151,58,0.85)" fontSize="10.5" fontFamily="Inter,sans-serif" fontWeight="600">Ayyuhal Walad</text>
        <text x="256" y="60" textAnchor="middle" fill="rgba(201,151,58,0.6)" fontSize="10" fontFamily="Inter,sans-serif">أيها الولد</text>
        <line x1="200" y1="68" x2="312" y2="68" stroke="rgba(201,151,58,0.25)" strokeWidth="1"/>
        {/* 4 episode rows */}
        {[
          {label:'Ep 1 — The Opening Letter',cls:'sh-ep1'},
          {label:'Ep 2 — Knowledge & Action',cls:'sh-ep2'},
          {label:'Ep 3 — The Inner Journey',cls:'sh-ep3'},
          {label:'Ep 4 — The Final Counsel',cls:'sh-ep4'},
        ].map((ep,i)=>(
          <g key={i} className={ep.cls}>
            <line x1="200" y1={88+i*28} x2="312" y2={88+i*28} stroke="rgba(240,236,227,0.06)" strokeWidth="0.8"/>
            <circle cx="208" cy={100+i*28} r="3.5" fill="rgba(201,151,58,0.3)"/>
            <text x="218" y={104+i*28} fill="rgba(240,236,227,0.6)" fontSize="7.5" fontFamily="Inter,sans-serif">{ep.label}</text>
          </g>
        ))}
        <text x="256" y="210" textAnchor="middle" fill="rgba(201,151,58,0.3)" fontSize="7.5" fontFamily="Inter,sans-serif" letterSpacing="2">PUBLISHED</text>
      </g>
      {/* Gold VERIFIED seal */}
      <g className="sh-seal">
        <circle cx="279" cy="78" r="22" fill="rgba(201,151,58,0.15)" stroke="rgba(201,151,58,0.7)" strokeWidth="1.8"/>
        <circle cx="279" cy="78" r="16" fill="none" stroke="rgba(201,151,58,0.35)" strokeWidth="1" strokeDasharray="3 2"/>
        <text x="279" y="74" textAnchor="middle" fill="rgba(201,151,58,0.9)" fontSize="6.5" fontFamily="Inter,sans-serif" fontWeight="700" letterSpacing="0.5">VERI</text>
        <text x="279" y="84" textAnchor="middle" fill="rgba(201,151,58,0.9)" fontSize="6.5" fontFamily="Inter,sans-serif" fontWeight="700" letterSpacing="0.5">FIED</text>
        <text x="279" y="68" textAnchor="middle" fill="rgba(201,151,58,0.7)" fontSize="9">✦</text>
      </g>
    </svg>
  );
}

// SVG components are used for all phases — no static images.
const PHASE_IMAGES: Record<string, string> = {};

// Map phase IDs to visual components
const PHASE_VISUALS: Record<string, () => React.JSX.Element> = {
  P0:  VisualReadBook,
  P1:  VisualPolishText,
  P2:  VisualLearnNames,
  P3:  VisualPlanEpisodes,
  P4:  VisualEnrich,
  P5:  VisualOutsideKnowledge,
  P6:  VisualCutPieces,
  P7:  VisualNarratorFraming,
  P8:  VisualSlides,
  P9:  VisualAudit,
  P10: VisualShip,
};

// Expanded narrative copy — factual, universal, impressive
const PHASE_NARRATIVE: Record<string, { headline: string; body: string }> = {
  P0: {
    headline: 'Every word. Every page. Every layout signal.',
    body: 'The factory feeds your source material — PDF, DOCX, audio transcript, database export, web archive — through enterprise-grade document intelligence. In ten minutes it reads thousands of pages with full layout awareness: headings, footnotes, tables, multi-column text, right-to-left scripts. What comes out is a clean, structure-aware text ready for every step that follows.',
  },
  P1: {
    headline: 'From raw extraction to clean, readable prose.',
    body: 'Optical character recognition produces noise. Scanning introduces errors. Line breaks split sentences mid-thought. This station runs a careful editorial pass — correcting misreads, normalizing formatting, restoring sentence integrity. The result reads as the author wrote it, not as the scanner captured it.',
  },
  P2: {
    headline: 'Two hundred names. Zero mispronunciations.',
    body: 'Every person, place, institution, and technical term is identified and given a pronunciation guide written for human narrators and AI speech engines alike. The phonetic glossary travels with the content as a sidecar — always accessible, always up to date. Listeners hear every name exactly as it should sound.',
  },
  P3: {
    headline: 'A book\'s chapters are never the right size for a podcast.',
    body: 'A 40-page chapter might be three great episodes. A six-page chapter might need to merge with its neighbour. This station reads the source structure and re-draws the episode boundaries — balancing duration, thematic unity, and narrative momentum. The blueprint is saved so every subsequent step works from the same episode map.',
  },
  P4: {
    headline: 'The notes the narrator needs — attached where they matter.',
    body: 'Supporting context is layered directly into each episode: who the figures are, why this moment matters, what came before and after. Notes are added without altering the source. The episode emerges richer — grounded, not overloaded — ready to be heard by someone who knows nothing about the subject.',
  },
  P5: {
    headline: 'The factory reads the wider field so the episode doesn\'t have to.',
    body: 'Carefully sourced material from outside the source document — cross-references, historical context, verified citations, modern scholarship — is added only where it genuinely deepens an episode. Every injected item is sourced and traceable. Nothing is invented. The episode becomes its own reliable reference.',
  },
  P6: {
    headline: 'Each episode gets its own self-contained bundle.',
    body: 'The enriched content is precision-sliced into independent upload bundles, one per episode. Each bundle contains everything the generation engine needs to produce a great conversation — source text, glossary, context notes — packaged so it can be uploaded, reviewed, and regenerated in isolation without touching any other episode.',
  },
  P7: {
    headline: 'Two hosts. One conversation. Every episode briefed.',
    body: 'A carefully authored briefing is written for each episode — telling the two AI hosts what the episode is about, what to emphasize, what register to adopt, what to leave out. This is the craft layer: the difference between a generated summary and a compelling conversation that sounds like two experts who have actually read the material.',
  },
  P8: {
    headline: 'Visuals that complement the audio. Never duplicate it.',
    body: 'Each episode receives a custom slide deck — diagrams that restate a structure, illustrations that make an abstract idea concrete, charts that surface a pattern in the data. Slides are authored against a strict ruleset: no re-narrating what the audio says, no generic stock imagery, no decorative padding. Every slide earns its place.',
  },
  P9: {
    headline: 'The factory reviews its own work. Up to fifteen times.',
    body: 'An automated reviewer reads every bundle, every framing, every slide deck and applies a comprehensive quality framework — citation accuracy, narrative integrity, coverage completeness, audio-visual alignment. Problems are flagged, fixed, and re-reviewed. The loop continues until the episode passes or a human call is needed. Nothing ships with known flaws.',
  },
  P10: {
    headline: 'Verified. Polished. Shipped to the catalog.',
    body: 'Once every episode in the series passes the quality gate, the complete series moves from the workshop into the public catalog. The production branch is merged. The catalog entry appears. The series is ready to upload to your podcast platform, your NotebookLM workspace, or your private archive.',
  },
};

// ── Types ─────────────────────────────────────────────────────────

interface Phase {
  id: string;
  name: string;
  kind: string;
  plain: string;
  duration_minutes: number;
}

interface Props {
  phases: Phase[];
  shippedCount: number;
  episodeCount: number;
}

// ── Component ─────────────────────────────────────────────────────

export default function NarrativeScroll({ phases, shippedCount, episodeCount }: Props) {
  const rootRef   = useRef<HTMLDivElement>(null);
  const pillRef   = useRef<HTMLDivElement>(null);
  const pillTextRef = useRef<HTMLSpanElement>(null);
  const progressRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (typeof window === 'undefined') return;

    const isMobile = window.innerWidth <= 768;
    const root = rootRef.current;
    if (!root) return;

    // Progress bar
    ScrollTrigger.create({
      start: 'top top',
      end: 'bottom bottom',
      onUpdate: (self) => {
        if (progressRef.current) {
          progressRef.current.style.width = `${self.progress * 100}%`;
        }
      },
    });

    // ── Hero entrance animations ────────────────────────────────
    const heroTl = gsap.timeline({
      scrollTrigger: { trigger: '.narrative-hero', start: 'top 90%' },
    });
    heroTl
      .to('.narrative-hero-logo',    { opacity: 1, scale: 1,  duration: 1.1, ease: 'power3.out' })
      .to('.narrative-hero-eyebrow', { opacity: 1, y: 0, duration: 0.7, ease: 'power2.out' }, '-=0.5')
      .to('.narrative-hero-title',   { opacity: 1, y: 0, duration: 0.8, ease: 'power2.out' }, '-=0.4')
      .to('.narrative-hero-lede',    { opacity: 1, y: 0, duration: 0.7, ease: 'power2.out' }, '-=0.4')
      .to('.narrative-hero-stats',   { opacity: 1, y: 0, duration: 0.6, ease: 'power2.out' }, '-=0.3')
      .to('.narrative-hero-cta',     { opacity: 1, y: 0, duration: 0.6, ease: 'power2.out' }, '-=0.3')
      .to('.narrative-scroll-invite',{ opacity: 1, duration: 0.8, ease: 'power2.out' }, '-=0.1');

    // ── Chapter pinned animations (desktop only) ────────────────
    if (!isMobile) {
      const chapters = root.querySelectorAll<HTMLElement>('.narrative-chapter');
      chapters.forEach((chapter, index) => {
        const station  = chapter.querySelector<HTMLElement>('.narrative-chapter-station');
        const title    = chapter.querySelector<HTMLElement>('.narrative-chapter-title');
        const body     = chapter.querySelector<HTMLElement>('.narrative-chapter-body');
        const badge    = chapter.querySelector<HTMLElement>('.n-kind-badge');
        const visual   = chapter.querySelector<HTMLElement>('.narrative-chapter-visual');
        const isEven   = index % 2 === 1;

        // Pin each chapter
        ScrollTrigger.create({
          trigger: chapter,
          start: 'top top',
          end: `+=${window.innerHeight * 1.2}`,
          pin: true,
          pinSpacing: true,
          onEnter: () => {
            if (pillRef.current) pillRef.current.classList.add('visible');
            if (pillTextRef.current) {
              pillTextRef.current.textContent = `${index + 1} / ${phases.length}`;
            }
          },
        });

        // Content entrance timeline
        const tl = gsap.timeline({
          scrollTrigger: {
            trigger: chapter,
            start: 'top 60%',
            toggleActions: 'play none none reverse',
          },
        });

        if (station)  tl.to(station,  { opacity: 1, y: 0, duration: 0.55, ease: 'power2.out' });
        if (title)    tl.to(title,    { opacity: 1, y: 0, duration: 0.65, ease: 'power2.out' }, '-=0.25');
        if (body)     tl.to(body,     { opacity: 1, y: 0, duration: 0.6,  ease: 'power2.out' }, '-=0.3');
        if (badge)    tl.to(badge,    { opacity: 1, y: 0, duration: 0.5,  ease: 'power2.out' }, '-=0.3');
        if (visual)   tl.to(visual,   {
          opacity: 1,
          x: 0,
          scale: 1,
          duration: 0.75,
          ease: 'power3.out',
        }, '-=0.6');

        // Parallax zoom — image scales from 1.12 → 1.0 while chapter is pinned
        const img = chapter.querySelector<HTMLElement>('.n-visual-img');
        if (img) {
          gsap.fromTo(img,
            { scale: 1.12 },
            {
              scale: 1,
              ease: 'none',
              scrollTrigger: {
                trigger: chapter,
                start: 'top top',
                end: `+=${window.innerHeight * 1.2}`,
                scrub: 2,
              },
            }
          );
        }
      });
    }

    // ── Outro animations ────────────────────────────────────────
    const outroTl = gsap.timeline({
      scrollTrigger: { trigger: '.narrative-outro', start: 'top 70%' },
    });
    outroTl
      .to('.narrative-outro-eyebrow', { opacity: 1, y: 0, duration: 0.6, ease: 'power2.out' })
      .to('.narrative-outro-title',   { opacity: 1, y: 0, duration: 0.7, ease: 'power2.out' }, '-=0.3')
      .to('.narrative-outro-sub',     { opacity: 1, y: 0, duration: 0.6, ease: 'power2.out' }, '-=0.3')
      .to('.narrative-outro-actions', { opacity: 1, y: 0, duration: 0.5, ease: 'power2.out' }, '-=0.2')
      .to('.narrative-quality-row',   { opacity: 1, y: 0, duration: 0.6, ease: 'power2.out' }, '-=0.1');

    return () => {
      ScrollTrigger.getAll().forEach(t => t.kill());
    };
  }, [phases]);

  const kindLabel = (kind: string) => {
    if (kind === 'agentic')    return 'AI-powered';
    if (kind === 'hybrid')     return 'AI + script';
    if (kind === 'mechanical') return 'Automated';
    return kind;
  };

  const kindClass = (kind: string) => {
    if (kind === 'agentic')    return 'n-kind-agentic';
    if (kind === 'hybrid')     return 'n-kind-hybrid';
    if (kind === 'mechanical') return 'n-kind-mechanical';
    return '';
  };

  return (
    <div ref={rootRef} className="narrative-root">

      {/* Scroll progress bar */}
      <div ref={progressRef} className="narrative-progress-bar" />

      {/* Chapter counter pill */}
      <div ref={pillRef} className="narrative-chapter-pill">
        Station <span ref={pillTextRef}>1 / {phases.length}</span>
      </div>

      {/* ── HERO ─────────────────────────────────────────────── */}
      <section className="narrative-hero">
        <ParticleField />

        {/* Logo placeholder — swap out when real logo arrives */}
        <div className="narrative-hero-logo">
          <div className="logo-placeholder-ring">
            <svg className="logo-placeholder-inner-svg" viewBox="0 0 120 120"
                 xmlns="http://www.w3.org/2000/svg">
              {/* Factory silhouette */}
              <rect x="20" y="65" width="80" height="45" rx="2"
                fill="none" stroke="rgba(201,151,58,0.7)" strokeWidth="1.5"/>
              {/* Smokestacks */}
              <rect x="35" y="45" width="12" height="22" rx="1"
                fill="none" stroke="rgba(201,151,58,0.6)" strokeWidth="1.2"/>
              <rect x="55" y="38" width="12" height="29" rx="1"
                fill="none" stroke="rgba(201,151,58,0.7)" strokeWidth="1.2"/>
              <rect x="75" y="48" width="12" height="19" rx="1"
                fill="none" stroke="rgba(201,151,58,0.5)" strokeWidth="1.2"/>
              {/* Sound waves from stacks */}
              {[0,1,2].map(i => (
                <path key={i}
                  d={`M ${41 + i * 20} ${40 - i * 3 - 6} Q ${41 + i * 20} ${30 - i * 3 - 6} ${43 + i * 20} ${26 - i * 3 - 6}`}
                  fill="none" stroke="rgba(201,151,58,0.35)" strokeWidth="1"
                  strokeLinecap="round" strokeDasharray="3 2"/>
              ))}
              {/* Conveyor belt at base */}
              <ellipse cx="100" cy="110" rx="8" ry="4"
                fill="none" stroke="rgba(201,151,58,0.4)" strokeWidth="1"/>
              <ellipse cx="20" cy="110" rx="8" ry="4"
                fill="none" stroke="rgba(201,151,58,0.4)" strokeWidth="1"/>
              <line x1="20" y1="106" x2="100" y2="106"
                stroke="rgba(201,151,58,0.3)" strokeWidth="1"/>
              <line x1="20" y1="114" x2="100" y2="114"
                stroke="rgba(201,151,58,0.3)" strokeWidth="1"/>
              {/* Source objects on belt */}
              <rect x="28" y="104" width="8" height="6" rx="1"
                fill="rgba(201,151,58,0.3)"/>
              <circle cx="52" cy="107" r="3"
                fill="rgba(201,151,58,0.25)"/>
              <rect x="64" y="104" width="10" height="6" rx="1"
                fill="rgba(201,151,58,0.2)"/>
            </svg>
          </div>
        </div>

        <span className="narrative-hero-eyebrow">Podcast Factory</span>

        <h1 className="narrative-hero-title">
          From Content<br />
          <em>To Conversation.</em>
        </h1>

        <p className="narrative-hero-lede">
          Any source material — books, research papers, audio, transcripts,
          data, recordings — goes in. A beautifully produced, verified
          podcast series comes out.
        </p>

        <div className="narrative-hero-stats">
          <div className="n-stat">
            <span className="n-stat-value">{phases.length}</span>
            <span className="n-stat-label">Production stations</span>
          </div>
          <div className="n-stat">
            <span className="n-stat-value">{shippedCount}</span>
            <span className="n-stat-label">Series published</span>
          </div>
          <div className="n-stat">
            <span className="n-stat-value">{episodeCount}</span>
            <span className="n-stat-label">Episodes</span>
          </div>
        </div>

        <div className="narrative-hero-cta">
          <a href="/library" className="narrative-cta-primary">Browse the catalog →</a>
          <a href="#station-1" className="narrative-cta-secondary">Tour the factory ↓</a>
        </div>

        <div className="narrative-scroll-invite">
          <span>Scroll to tour the factory</span>
          <div className="scroll-chevron" />
        </div>
      </section>

      {/* ── PIPELINE CHAPTERS ────────────────────────────────── */}
      <div className="narrative-chapters-wrapper" id="station-1">
        {phases.map((phase, index) => {
          const VisualComponent = PHASE_VISUALS[phase.id];
          const narrative = PHASE_NARRATIVE[phase.id];
          return (
            <section key={phase.id} className={`narrative-chapter${index % 2 === 1 ? ' narrative-chapter--reversed' : ''}`}>
              <div className="narrative-chapter-inner">

                <div className="narrative-chapter-text">
                  <div className="narrative-chapter-station">
                    <div className="n-station-number">{index + 1}</div>
                    <div className="n-station-meta">
                      <span className="n-station-id">Station {phase.id}</span>
                      <span className="n-station-duration">{phase.duration_minutes} min avg</span>
                    </div>
                  </div>

                  <h2 className="narrative-chapter-title">
                    {narrative?.headline ?? phase.name}
                  </h2>

                  <p className="narrative-chapter-body">
                    {narrative?.body ?? phase.plain}
                  </p>

                  <span className={`n-kind-badge ${kindClass(phase.kind)}`}>
                    {kindLabel(phase.kind)}
                  </span>
                </div>

                <div className="narrative-chapter-visual">
                  <div className="n-visual-frame">
                    <span className="n-frame-corner n-frame-tl" />
                    <span className="n-frame-corner n-frame-tr" />
                    <span className="n-frame-corner n-frame-bl" />
                    <span className="n-frame-corner n-frame-br" />
                    {PHASE_IMAGES[phase.id]
                      ? <img src={PHASE_IMAGES[phase.id]} alt="" className="n-visual-img" />
                      : VisualComponent ? <VisualComponent /> : null
                    }
                  </div>
                </div>

              </div>
            </section>
          );
        })}
      </div>

      {/* ── OUTRO ────────────────────────────────────────────── */}
      <section className="narrative-outro">
        <span className="narrative-outro-eyebrow">The result</span>
        <h2 className="narrative-outro-title">
          From raw source material to a catalog entry.<br />
          In one automated run.
        </h2>
        <p className="narrative-outro-sub">
          Every series that leaves this factory has been read, structured,
          enriched, authored, visualized, and reviewed. The audience hears
          the finished work. They never see the factory.
        </p>
        <div className="narrative-outro-actions">
          <a href="/library" className="narrative-cta-primary">Open the catalog →</a>
          <a href="/architecture" className="narrative-cta-secondary">Architecture detail ↗</a>
        </div>

        <div className="narrative-quality-row">
          <div className="n-quality-item">
            <span className="n-quality-value">15</span>
            <span className="n-quality-label">Quality checks per book</span>
          </div>
          <div className="n-quality-item">
            <span className="n-quality-value">11</span>
            <span className="n-quality-label">Production stations</span>
          </div>
          <div className="n-quality-item">
            <span className="n-quality-value">0</span>
            <span className="n-quality-label">Manual steps in the pipeline</span>
          </div>
          <div className="n-quality-item">
            <span className="n-quality-value">∞</span>
            <span className="n-quality-label">Source formats accepted</span>
          </div>
        </div>
      </section>

    </div>
  );
}

// ── Particle field — Arabic/symbolic characters drifting up ──────

function ParticleField() {
  // Symbols drawn from multiple traditions and content types
  const symbols = [
    '∞', '◆', '∴', '⟐', '✦', '⌘', '⊕', '◈', '⧫', '✧',
    '⟡', '⊞', '◉', '⟣', '✣', '⊛', '◌', '⟢', '✤', '⊜',
  ];

  const particles = Array.from({ length: 22 }, (_, i) => ({
    symbol: symbols[i % symbols.length],
    left:   `${(i * 4.5 + 2) % 98}%`,
    delay:  `${(i * 1.3) % 14}s`,
    duration: `${14 + (i % 8) * 2}s`,
    size:   `${14 + (i % 5) * 5}px`,
  }));

  return (
    <div className="narrative-hero-particles" aria-hidden="true">
      {particles.map((p, i) => (
        <span key={i} className="n-particle" style={{
          left: p.left,
          fontSize: p.size,
          animationDelay: p.delay,
          animationDuration: p.duration,
        }}>{p.symbol}</span>
      ))}
    </div>
  );
}
