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

import { useEffect, useRef, type ReactNode } from 'react';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';

gsap.registerPlugin(ScrollTrigger);

function NarrativeSvg({
  titleId,
  descId,
  title,
  desc,
  children,
}: {
  titleId: string;
  descId: string;
  title: string;
  desc: string;
  children: ReactNode;
}) {
  return (
    <svg
      viewBox="0 0 340 240"
      xmlns="http://www.w3.org/2000/svg"
      role="img"
      aria-labelledby={`${titleId} ${descId}`}
    >
      <title id={titleId}>{title}</title>
      <desc id={descId}>{desc}</desc>
      {children}
    </svg>
  );
}

// ── Visual SVG definitions — one per phase ───────────────────────


// ── Visual SVG definitions — one per phase ───────────────────────
// Bold illustration style: solid panel fills, thick borders, large white labels.

function VisualReadBook() {
  return (
    <NarrativeSvg titleId="n-read-book-title" descId="n-read-book-desc" title="Read and scan source book" desc="A source document is scanned and converted into structured text.">
      <defs><style>{`
        @keyframes rb-sweep{0%,100%{transform:translateY(0)}50%{transform:translateY(140px)}}
        @keyframes rb-in{from{opacity:0}to{opacity:1}}
        .rb-beam{animation:rb-sweep 3s ease-in-out infinite}
        .rb-l1{animation:rb-in .3s .3s both}.rb-l2{animation:rb-in .3s .6s both}
        .rb-l3{animation:rb-in .3s .9s both}.rb-l4{animation:rb-in .3s 1.2s both}
        .rb-l5{animation:rb-in .3s 1.5s both}
      `}</style></defs>

      {/* Source document — gold */}
      <rect x="12" y="20" width="134" height="190" rx="7" fill="#1c1400" stroke="#c9973a" strokeWidth="2.5"/>
      <rect x="12" y="20" width="134" height="32" rx="7" fill="#c9973a" opacity="0.3"/>
      <text x="79" y="41" textAnchor="middle" fill="white" fontSize="13" fontWeight="700" fontFamily="Inter,sans-serif">PDF / DOCX</text>
      {[62,76,90,104,118,132,146,160,174,188].map((y,i)=>(
        <rect key={i} x="24" y={y} width={96-i*3} height="8" rx="3" fill="white" opacity="0.2"/>
      ))}

      {/* Scanner beam */}
      <g className="rb-beam">
        <rect x="12" y="20" width="134" height="16" rx="4" fill="#ffd700" opacity="0.07"/>
        <rect x="12" y="32" width="134" height="4.5" rx="2" fill="#ffd700" opacity="0.95"/>
      </g>

      {/* Arrow */}
      <path d="M 158 115 L 174 115" stroke="#c9973a" strokeWidth="3.5" strokeLinecap="round"/>
      <polygon points="172,107 188,115 172,123" fill="#c9973a"/>

      {/* Structured text output — blue */}
      <rect x="190" y="20" width="138" height="190" rx="7" fill="#061422" stroke="#5aabf0" strokeWidth="2.5"/>
      <rect x="190" y="20" width="138" height="32" rx="7" fill="#5aabf0" opacity="0.3"/>
      <text x="259" y="41" textAnchor="middle" fill="white" fontSize="11" fontWeight="700" fontFamily="Inter,sans-serif">STRUCTURED TEXT</text>
      <g className="rb-l1">
        <rect x="200" y="62" width="32" height="14" rx="4" fill="#5aabf0"/>
        <text x="216" y="73" textAnchor="middle" fill="white" fontSize="9" fontWeight="700" fontFamily="Inter,sans-serif">H1</text>
        <rect x="238" y="65" width="80" height="8" rx="3" fill="white" opacity="0.55"/>
      </g>
      <g className="rb-l2">
        <rect x="200" y="84" width="32" height="14" rx="4" fill="#5aabf0" opacity="0.55"/>
        <text x="216" y="95" textAnchor="middle" fill="white" fontSize="9" fontWeight="700" fontFamily="Inter,sans-serif">H2</text>
        <rect x="238" y="87" width="66" height="8" rx="3" fill="white" opacity="0.38"/>
      </g>
      <g className="rb-l3">
        <rect x="200" y="105" width="116" height="8" rx="3" fill="white" opacity="0.3"/>
        <rect x="200" y="118" width="96" height="8" rx="3" fill="white" opacity="0.24"/>
      </g>
      <g className="rb-l4">
        <rect x="200" y="134" width="32" height="14" rx="4" fill="#5aabf0" opacity="0.55"/>
        <text x="216" y="145" textAnchor="middle" fill="white" fontSize="9" fontWeight="700" fontFamily="Inter,sans-serif">H2</text>
        <rect x="238" y="137" width="72" height="8" rx="3" fill="white" opacity="0.38"/>
      </g>
      <g className="rb-l5">
        <rect x="200" y="155" width="110" height="8" rx="3" fill="white" opacity="0.24"/>
        <rect x="200" y="168" width="88" height="8" rx="3" fill="white" opacity="0.2"/>
        <rect x="200" y="181" width="100" height="8" rx="3" fill="white" opacity="0.18"/>
      </g>
    </NarrativeSvg>
  );
}

function VisualPolishText() {
  return (
    <NarrativeSvg titleId="n-polish-title" descId="n-polish-desc" title="Polish and correct text" desc="Problem lines are corrected and approved into a clean version.">
      <defs><style>{`
        @keyframes pt-in{from{opacity:0;transform:translateX(12px)}to{opacity:1;transform:translateX(0)}}
        @keyframes pt-badge{from{opacity:0;transform:scale(.7)}to{opacity:1;transform:scale(1)}}
        .pt-after{animation:pt-in .5s .8s both}
        .pt-badge{animation:pt-badge .4s 1.5s both}
      `}</style></defs>

      {/* BEFORE panel — red */}
      <rect x="10" y="20" width="146" height="196" rx="7" fill="#200808" stroke="#f05555" strokeWidth="2.5"/>
      <rect x="10" y="20" width="146" height="32" rx="7" fill="#f05555" opacity="0.32"/>
      <text x="83" y="41" textAnchor="middle" fill="white" fontSize="14" fontWeight="700" fontFamily="Inter,sans-serif">BEFORE</text>
      {[62,78,94,110,126,142,158,174,190].map((y,i)=>(
        <rect key={i} x="22" y={y} width={110-i*4} height="8" rx="3" fill="white" opacity="0.17"/>
      ))}
      {/* Error marks */}
      {[78,118,158].map((y,i)=>(
        <g key={i}>
          <rect x="22" y={y} width={80-i*8} height="8" rx="3" fill="#f05555" opacity="0.28"/>
          <line x1="22" y1={y+4} x2={96-i*8} y2={y+4} stroke="#f05555" strokeWidth="2.5" strokeLinecap="round"/>
          <circle cx={104-i*8} cy={y+4} r="8" fill="#f05555" opacity="0.9"/>
          <text x={104-i*8} y={y+8} textAnchor="middle" fill="white" fontSize="10" fontWeight="700" fontFamily="Inter,sans-serif">✕</text>
        </g>
      ))}

      {/* Arrow */}
      <path d="M 164 118 L 180 118" stroke="#c9973a" strokeWidth="3.5" strokeLinecap="round"/>
      <polygon points="178,110 194,118 178,126" fill="#c9973a"/>

      {/* AFTER panel — green */}
      <g className="pt-after">
        <rect x="184" y="20" width="146" height="196" rx="7" fill="#061a0c" stroke="#5ac87a" strokeWidth="2.5"/>
        <rect x="184" y="20" width="146" height="32" rx="7" fill="#5ac87a" opacity="0.3"/>
        <text x="257" y="41" textAnchor="middle" fill="white" fontSize="14" fontWeight="700" fontFamily="Inter,sans-serif">AFTER</text>
        {[62,78,94,110,126,142,158,174,190].map((y,i)=>(
          <rect key={i} x="196" y={y} width={120-i*4} height="8" rx="3" fill="white" opacity="0.32"/>
        ))}
        <g className="pt-badge">
          <rect x="200" y="198" width="114" height="22" rx="11" fill="#5ac87a"/>
          <text x="257" y="213" textAnchor="middle" fill="white" fontSize="12" fontWeight="700" fontFamily="Inter,sans-serif">✓ CORRECTED</text>
        </g>
      </g>
    </NarrativeSvg>
  );
}

function VisualLearnNames() {
  return (
    <NarrativeSvg titleId="n-names-title" descId="n-names-desc" title="Learn names and terms" desc="Highlighted Arabic names are paired with phonetic guides.">
      <defs><style>{`
        @keyframes ln-glow{0%,100%{opacity:.7}50%{opacity:1}}
        @keyframes ln-card{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:translateY(0)}}
        .ln-hl{animation:ln-glow 2.2s infinite}
        .ln-c1{animation:ln-card .4s .3s both}
        .ln-c2{animation:ln-card .4s .8s both}
        .ln-c3{animation:ln-card .4s 1.3s both}
      `}</style></defs>

      {/* Text passage */}
      <rect x="10" y="18" width="148" height="202" rx="7" fill="#1c1400" stroke="#c9973a" strokeWidth="2"/>
      <rect x="10" y="18" width="148" height="30" rx="7" fill="#c9973a" opacity="0.27"/>
      <text x="84" y="37" textAnchor="middle" fill="white" fontSize="12" fontWeight="700" fontFamily="Inter,sans-serif">TEXT PASSAGE</text>
      {[56,70,84,98,112,126,140,154,168,182,196].map((y,i)=>(
        <rect key={i} x="20" y={y} width={116-i*2} height="7" rx="3" fill="white" opacity="0.18"/>
      ))}

      {/* Name highlights */}
      {[
        {y:82,  w:68, text:'الغزالي'},
        {y:124, w:52, text:'بغداد'},
        {y:166, w:76, text:'إحياء العلوم'},
      ].map((n,i)=>(
        <g key={i} className="ln-hl">
          <rect x="20" y={n.y-1} width={n.w} height="15" rx="4" fill="#c9973a" opacity="0.42"/>
          <text x={20+n.w/2} y={n.y+11} textAnchor="middle" fill="#ffd700" fontSize="12" fontWeight="700" fontFamily="Inter,sans-serif">{n.text}</text>
        </g>
      ))}

      {/* Connector lines */}
      {[89,131,173].map((y,i)=>(
        <line key={i} x1="158" y1={y} x2="172" y2={y} stroke="#c9973a" strokeWidth="1.8" strokeDasharray="4 3" opacity="0.75"/>
      ))}

      {/* Phonetic cards */}
      {[
        {y:46,  ar:'الغزالي',      lat:'al-GHA-za-lee',      cls:'ln-c1'},
        {y:104, ar:'بغداد',        lat:'bag-DAAD',           cls:'ln-c2'},
        {y:160, ar:'إحياء العلوم', lat:'ih-YAA al-u-LOOM', cls:'ln-c3'},
      ].map((c,i)=>(
        <g key={i} className={c.cls}>
          <rect x="172" y={c.y} width="156" height="54" rx="7" fill="#1c1400" stroke="#c9973a" strokeWidth="2"/>
          <rect x="172" y={c.y} width="156" height="24" rx="7" fill="#c9973a" opacity="0.25"/>
          <text x="188" y={c.y+17} fill="#ffd700" fontSize="14" fontWeight="700" fontFamily="Inter,sans-serif">{c.ar}</text>
          <text x="188" y={c.y+42} fill="#c9973a" fontSize="10.5" fontFamily="Inter,sans-serif" letterSpacing="0.5">{c.lat}</text>
        </g>
      ))}
    </NarrativeSvg>
  );
}

function VisualPlanEpisodes() {
  return (
    <NarrativeSvg titleId="n-plan-title" descId="n-plan-desc" title="Plan episode structure" desc="Book chapters are mapped into an episode sequence with pacing.">
      <defs><style>{`
        @keyframes pe-pop{from{opacity:0;transform:scale(.85)}to{opacity:1;transform:scale(1)}}
        .pe-e1{animation:pe-pop .35s .5s both}.pe-e2{animation:pe-pop .35s .85s both}
        .pe-e3{animation:pe-pop .35s 1.2s both}.pe-e4{animation:pe-pop .35s 1.55s both}
      `}</style></defs>

      {/* Chapters — left */}
      <text x="14" y="16" fill="#5aabf0" fontSize="10" fontWeight="700" fontFamily="Inter,sans-serif" letterSpacing="2">CHAPTERS</text>
      {[
        {y:24,  h:40, ar:'الفصل الأول',  en:'Chapter 1'},
        {y:72,  h:40, ar:'الفصل الثاني', en:'Chapter 2'},
        {y:120, h:48, ar:'الفصل الثالث', en:'Chapter 3'},
        {y:176, h:34, ar:'الفصل الرابع', en:'Chapter 4'},
      ].map((ch,i)=>(
        <g key={i}>
          <rect x="8" y={ch.y} width="144" height={ch.h} rx="6" fill="#061422" stroke="#5aabf0" strokeWidth="2"/>
          <text x="20" y={ch.y+20} fill="white" fontSize="13" fontWeight="700" fontFamily="Inter,sans-serif">{ch.ar}</text>
          <text x="20" y={ch.y+33} fill="#5aabf0" fontSize="9.5" fontFamily="Inter,sans-serif">{ch.en}</text>
        </g>
      ))}

      {/* Arrows */}
      {[44,92,144,193].map((y,i)=>(
        <g key={i}>
          <line x1="152" y1={y} x2="162" y2={y} stroke="#c9973a" strokeWidth="2.5" strokeLinecap="round"/>
          <polygon points={`161,${y-6} 172,${y} 161,${y+6}`} fill="#c9973a"/>
        </g>
      ))}

      {/* Episodes — right */}
      <text x="176" y="16" fill="#c9973a" fontSize="10" fontWeight="700" fontFamily="Inter,sans-serif" letterSpacing="2">EPISODES</text>
      {[
        {y:24,  title:'The Opening Letter',  cls:'pe-e1'},
        {y:80,  title:'Knowledge & Action',  cls:'pe-e2'},
        {y:136, title:'The Inner Journey',   cls:'pe-e3'},
        {y:190, title:'The Final Counsel',   cls:'pe-e4'},
      ].map((ep,i)=>(
        <g key={i} className={ep.cls}>
          <rect x="174" y={ep.y} width="158" height="48" rx="6" fill="#1c1400" stroke="#c9973a" strokeWidth="2"/>
          <rect x="174" y={ep.y} width="158" height="22" rx="6" fill="#c9973a" opacity="0.25"/>
          <text x="186" y={ep.y+16} fill="#ffd700" fontSize="11" fontWeight="700" fontFamily="Inter,sans-serif">Episode {i+1}</text>
          <text x="186" y={ep.y+36} fill="#c9973a" fontSize="9.5" fontFamily="Inter,sans-serif">{ep.title}</text>
        </g>
      ))}
    </NarrativeSvg>
  );
}

function VisualEnrich() {
  return (
    <NarrativeSvg titleId="n-enrich-title" descId="n-enrich-desc" title="Enrich chapter draft" desc="Core chapter text is expanded with contextual supporting material.">
      <defs><style>{`
        @keyframes en-left{from{opacity:0;transform:translateX(-14px)}to{opacity:1;transform:translateX(0)}}
        @keyframes en-right{from{opacity:0;transform:translateX(14px)}to{opacity:1;transform:translateX(0)}}
        @keyframes en-pulse{0%,100%{opacity:.7}50%{opacity:1}}
        .en-c1{animation:en-left .45s .2s both}.en-c2{animation:en-right .45s .7s both}
        .en-c3{animation:en-left .45s 1.2s both}.en-c4{animation:en-right .45s 1.7s both}
        .en-dot{animation:en-pulse 1.8s infinite}
      `}</style></defs>

      {/* Center source document */}
      <rect x="118" y="14" width="104" height="210" rx="7" fill="#1c1400" stroke="#c9973a" strokeWidth="2"/>
      <rect x="118" y="14" width="104" height="28" rx="7" fill="#c9973a" opacity="0.3"/>
      <text x="170" y="31" textAnchor="middle" fill="white" fontSize="11" fontWeight="700" fontFamily="Inter,sans-serif">SOURCE</text>
      {[50,64,78,92,106,120,134,148,162,176,190,204].map((y,i)=>(
        <rect key={i} x="128" y={y} width={76-i*2} height="6" rx="2" fill="white" opacity="0.2"/>
      ))}

      {/* Historical — top left (blue) */}
      <g className="en-c1">
        <rect x="4" y="14" width="106" height="54" rx="7" fill="#061422" stroke="#5aabf0" strokeWidth="2"/>
        <rect x="4" y="14" width="106" height="26" rx="7" fill="#5aabf0" opacity="0.3"/>
        <text x="57" y="31" textAnchor="middle" fill="white" fontSize="11" fontWeight="700" fontFamily="Inter,sans-serif">HISTORICAL</text>
        <text x="57" y="56" textAnchor="middle" fill="#5aabf0" fontSize="9.5" fontFamily="Inter,sans-serif">Context &amp; era</text>
        <line x1="110" y1="41" x2="118" y2="41" stroke="#5aabf0" strokeWidth="2" strokeDasharray="4 3"/>
        <circle cx="110" cy="41" r="5" fill="#5aabf0" className="en-dot"/>
      </g>

      {/* Key Term — bottom left (purple) */}
      <g className="en-c3">
        <rect x="4" y="152" width="106" height="54" rx="7" fill="#180620" stroke="#b87fc8" strokeWidth="2"/>
        <rect x="4" y="152" width="106" height="26" rx="7" fill="#b87fc8" opacity="0.28"/>
        <text x="57" y="169" textAnchor="middle" fill="white" fontSize="11" fontWeight="700" fontFamily="Inter,sans-serif">KEY TERM</text>
        <text x="57" y="195" textAnchor="middle" fill="#ffd700" fontSize="14" fontWeight="700" fontFamily="Inter,sans-serif">التوكل</text>
        <line x1="110" y1="179" x2="118" y2="155" stroke="#b87fc8" strokeWidth="2" strokeDasharray="4 3"/>
        <circle cx="110" cy="179" r="5" fill="#b87fc8" className="en-dot"/>
      </g>

      {/* Quran Ref — top right (green) */}
      <g className="en-c2">
        <rect x="230" y="14" width="106" height="54" rx="7" fill="#061a0c" stroke="#5ac87a" strokeWidth="2"/>
        <rect x="230" y="14" width="106" height="26" rx="7" fill="#5ac87a" opacity="0.28"/>
        <text x="283" y="31" textAnchor="middle" fill="white" fontSize="11" fontWeight="700" fontFamily="Inter,sans-serif">QURAN REF</text>
        <text x="283" y="56" textAnchor="middle" fill="#5ac87a" fontSize="9.5" fontFamily="Inter,sans-serif">Verse links</text>
        <line x1="222" y1="41" x2="230" y2="41" stroke="#5ac87a" strokeWidth="2" strokeDasharray="4 3"/>
        <circle cx="230" cy="41" r="5" fill="#5ac87a" className="en-dot"/>
      </g>

      {/* Scholar Note — bottom right (red) */}
      <g className="en-c4">
        <rect x="230" y="152" width="106" height="54" rx="7" fill="#1e0808" stroke="#f05555" strokeWidth="2"/>
        <rect x="230" y="152" width="106" height="26" rx="7" fill="#f05555" opacity="0.28"/>
        <text x="283" y="169" textAnchor="middle" fill="white" fontSize="11" fontWeight="700" fontFamily="Inter,sans-serif">SCHOLAR</text>
        <text x="283" y="193" textAnchor="middle" fill="#f09090" fontSize="9.5" fontFamily="Inter,sans-serif">Commentary</text>
        <line x1="222" y1="179" x2="230" y2="155" stroke="#f05555" strokeWidth="2" strokeDasharray="4 3"/>
        <circle cx="230" cy="179" r="5" fill="#f05555" className="en-dot"/>
      </g>
    </NarrativeSvg>
  );
}

function VisualOutsideKnowledge() {
  return (
    <NarrativeSvg titleId="n-knowledge-title" descId="n-knowledge-desc" title="Bring in outside knowledge" desc="External references and source knowledge are pulled into the pipeline.">
      <defs><style>{`
        @keyframes ok-in{from{opacity:0;transform:translateX(14px)}to{opacity:1;transform:translateX(0)}}
        @keyframes ok-ck{0%{stroke-dashoffset:26}100%{stroke-dashoffset:0}}
        .ok-c1{animation:ok-in .4s .3s both}.ok-c2{animation:ok-in .4s .8s both}.ok-c3{animation:ok-in .4s 1.3s both}
        .ok-k1{animation:ok-ck .35s .7s both;stroke-dasharray:26;stroke-dashoffset:26}
        .ok-k2{animation:ok-ck .35s 1.2s both;stroke-dasharray:26;stroke-dashoffset:26}
        .ok-k3{animation:ok-ck .35s 1.7s both;stroke-dasharray:26;stroke-dashoffset:26}
      `}</style></defs>

      {/* Episode text with citation markers */}
      <rect x="10" y="18" width="152" height="202" rx="7" fill="#1c1400" stroke="#c9973a" strokeWidth="2"/>
      <rect x="10" y="18" width="152" height="30" rx="7" fill="#c9973a" opacity="0.27"/>
      <text x="86" y="37" textAnchor="middle" fill="white" fontSize="12" fontWeight="700" fontFamily="Inter,sans-serif">EPISODE TEXT</text>
      {[58,72,86,100,114,128,142,156,170,184,198].map((y,i)=>(
        <rect key={i} x="20" y={y} width={118-i*3} height="7" rx="3" fill="white" opacity="0.18"/>
      ))}

      {/* Citation highlights */}
      {[
        {y:82,  label:'[1] Quran 39:9'},
        {y:128, label:'[2] Bukhari 79'},
        {y:174, label:'[3] al-Nawawi'},
      ].map((c,i)=>(
        <g key={i}>
          <rect x="20" y={c.y} width="130" height="16" rx="4" fill="#c9973a" opacity="0.3"/>
          <text x="26" y={c.y+12} fill="#ffd700" fontSize="10.5" fontWeight="700" fontFamily="Inter,sans-serif">{c.label}</text>
        </g>
      ))}

      {/* Arrow */}
      <path d="M 170 120 L 186 120" stroke="#c9973a" strokeWidth="3.5" strokeLinecap="round"/>
      <polygon points="184,112 200,120 184,128" fill="#c9973a"/>

      {/* Verified source cards */}
      {[
        {y:18,  label:'Quran 39:9',    sub:'وَقُل رَّبِّ زِدْنِي', color:'#5ac87a', bg:'#061a0c', cls:'ok-c1', kls:'ok-k1'},
        {y:98,  label:'Bukhari No. 79', sub:'Hadith on knowledge', color:'#5aabf0', bg:'#061422', cls:'ok-c2', kls:'ok-k2'},
        {y:176, label:'al-Nawawi',      sub:'Riyad al-Salihin',    color:'#c9973a', bg:'#1c1400', cls:'ok-c3', kls:'ok-k3'},
      ].map((c,i)=>(
        <g key={i} className={c.cls}>
          <rect x="202" y={c.y} width="128" height="66" rx="7" fill={c.bg} stroke={c.color} strokeWidth="2"/>
          <rect x="202" y={c.y} width="128" height="26" rx="7" fill={c.color} opacity="0.28"/>
          <text x="214" y={c.y+18} fill="white" fontSize="12" fontWeight="700" fontFamily="Inter,sans-serif">{c.label}</text>
          <text x="214" y={c.y+44} fill="white" fontSize="10.5" fontFamily="Inter,sans-serif" opacity="0.8">{c.sub}</text>
          <circle cx="318" cy={c.y+52} r="12" fill={c.color} opacity="0.25" stroke={c.color} strokeWidth="2"/>
          <polyline points={`312,${c.y+52} 316,${c.y+57} 324,${c.y+47}`}
            className={c.kls} fill="none" stroke={c.color} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/>
        </g>
      ))}
    </NarrativeSvg>
  );
}

function VisualCutPieces() {
  return (
    <NarrativeSvg titleId="n-cut-title" descId="n-cut-desc" title="Cut chapter into pieces" desc="A larger narrative is segmented into smaller structured parts.">
      <defs><style>{`
        @keyframes cp-cut{from{opacity:0;transform:translateY(-18px)}to{opacity:1;transform:translateY(0)}}
        @keyframes cp-drop{from{opacity:0;transform:translateY(-12px)}to{opacity:1;transform:translateY(0)}}
        @keyframes cp-line{0%{stroke-dashoffset:230}100%{stroke-dashoffset:0}}
        .cp-b1{animation:cp-cut .4s .4s both}.cp-b2{animation:cp-cut .4s .9s both}.cp-b3{animation:cp-cut .4s 1.4s both}
        .cp-p1{animation:cp-drop .4s .8s both}.cp-p2{animation:cp-drop .4s 1.3s both}
        .cp-p3{animation:cp-drop .4s 1.8s both}.cp-p4{animation:cp-drop .4s 2.3s both}
        .cp-l1{animation:cp-line .5s .4s both;stroke-dasharray:230;stroke-dashoffset:230}
        .cp-l2{animation:cp-line .5s .9s both;stroke-dasharray:230;stroke-dashoffset:230}
        .cp-l3{animation:cp-line .5s 1.4s both;stroke-dasharray:230;stroke-dashoffset:230}
      `}</style></defs>

      {/* Full text bar */}
      <rect x="10" y="26" width="320" height="58" rx="7" fill="#1c1400" stroke="#c9973a" strokeWidth="2"/>
      <rect x="10" y="26" width="320" height="28" rx="7" fill="#c9973a" opacity="0.27"/>
      <text x="170" y="44" textAnchor="middle" fill="white" fontSize="12" fontWeight="700" fontFamily="Inter,sans-serif">أيها الولد — FULL BOOK TEXT</text>
      {[62,72].map((y,i)=>(
        <rect key={i} x="20" y={y} width={288-i*24} height="7" rx="3" fill="white" opacity="0.2"/>
      ))}

      {/* Cut lines */}
      {[98,192,268].map((x,i)=>(
        <line key={i} x1={x} y1="14" x2={x} y2="98" className={`cp-l${i+1}`} stroke="#ffd700" strokeWidth="2.5" strokeDasharray="6 4"/>
      ))}

      {/* Scissor icons */}
      {[{x:98,cls:'cp-b1'},{x:192,cls:'cp-b2'},{x:268,cls:'cp-b3'}].map((b,i)=>(
        <g key={i} className={b.cls}>
          <ellipse cx={b.x} cy="13" rx="13" ry="9" fill="#ffd700" opacity="0.9"/>
          <text x={b.x} y="17" textAnchor="middle" fill="#1a1000" fontSize="12" fontWeight="700" fontFamily="Inter,sans-serif">✂</text>
        </g>
      ))}

      {/* Episode packets */}
      {[
        {x:10,  w:80,  ep:'Ep 1', title:'Opening',   cls:'cp-p1'},
        {x:100, w:84,  ep:'Ep 2', title:'Knowledge', cls:'cp-p2'},
        {x:194, w:66,  ep:'Ep 3', title:'Practice',  cls:'cp-p3'},
        {x:270, w:60,  ep:'Ep 4', title:'Close',     cls:'cp-p4'},
      ].map((p,i)=>(
        <g key={i} className={p.cls}>
          <line x1={p.x+p.w/2} y1="98" x2={p.x+p.w/2} y2="112" stroke="#c9973a" strokeWidth="2" opacity="0.6"/>
          <rect x={p.x+2} y="112" width={p.w-4} height="74" rx="6" fill="#1c1400" stroke="#c9973a" strokeWidth="2"/>
          <rect x={p.x+2} y="112" width={p.w-4} height="26" rx="6" fill="#c9973a" opacity="0.25"/>
          <text x={p.x+p.w/2} y="129" textAnchor="middle" fill="#ffd700" fontSize="13" fontWeight="700" fontFamily="Inter,sans-serif">{p.ep}</text>
          <text x={p.x+p.w/2} y="155" textAnchor="middle" fill="#c9973a" fontSize="9.5" fontFamily="Inter,sans-serif">{p.title}</text>
          {[167,176].map((y,j)=>(
            <rect key={j} x={p.x+8} y={y} width={p.w-18-j*6} height="5" rx="2" fill="white" opacity="0.15"/>
          ))}
        </g>
      ))}
    </NarrativeSvg>
  );
}

function VisualNarratorFraming() {
  return (
    <NarrativeSvg titleId="n-frame-title" descId="n-frame-desc" title="Add narrator framing" desc="A narrator layer wraps the content with opening and closing guidance.">
      <defs><style>{`
        @keyframes nf-in{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:translateY(0)}}
        @keyframes nf-talk{0%,100%{opacity:0;transform:scale(.8)}25%,75%{opacity:1;transform:scale(1)}}
        .nf-l1{animation:nf-in .3s .5s both}.nf-l2{animation:nf-in .3s .8s both}
        .nf-l3{animation:nf-in .3s 1.1s both}.nf-l4{animation:nf-in .3s 1.4s both}
        .nf-ba{animation:nf-talk 2.4s 1.8s infinite}
        .nf-bb{animation:nf-talk 2.4s 2.8s infinite}
      `}</style></defs>

      {/* Episode card */}
      <rect x="8" y="16" width="106" height="148" rx="7" fill="#1c1400" stroke="#c9973a" strokeWidth="2"/>
      <rect x="8" y="16" width="106" height="28" rx="7" fill="#c9973a" opacity="0.27"/>
      <text x="61" y="34" textAnchor="middle" fill="white" fontSize="12" fontWeight="700" fontFamily="Inter,sans-serif">EPISODE</text>
      {[54,66,78,90,102,114,126,140,152].map((y,i)=>(
        <rect key={i} x="18" y={y} width={76-i*3} height="7" rx="3" fill="white" opacity="0.2"/>
      ))}

      {/* Arrow → */}
      <path d="M 122 90 L 138 90" stroke="#c9973a" strokeWidth="3.5" strokeLinecap="round"/>
      <polygon points="136,82 152,90 136,98" fill="#c9973a"/>

      {/* Host briefing card */}
      <rect x="152" y="16" width="116" height="148" rx="7" fill="#061422" stroke="#5aabf0" strokeWidth="2"/>
      <rect x="152" y="16" width="116" height="28" rx="7" fill="#5aabf0" opacity="0.32"/>
      <text x="210" y="34" textAnchor="middle" fill="white" fontSize="12" fontWeight="700" fontFamily="Inter,sans-serif">HOST BRIEF</text>
      <g className="nf-l1"><rect x="162" y="54" width="96" height="9" rx="3" fill="white" opacity="0.5"/></g>
      <g className="nf-l2"><rect x="162" y="69" width="80" height="9" rx="3" fill="white" opacity="0.38"/></g>
      <g className="nf-l3"><rect x="162" y="84" width="92" height="9" rx="3" fill="white" opacity="0.32"/></g>
      <g className="nf-l4"><rect x="162" y="99" width="70" height="9" rx="3" fill="white" opacity="0.26"/></g>
      {[116,128,140,152].map((y,i)=>(
        <rect key={i} x="162" y={y} width={82-i*12} height="7" rx="2" fill="white" opacity="0.2"/>
      ))}

      {/* Arrow ↓ */}
      <line x1="210" y1="166" x2="210" y2="182" stroke="#5aabf0" strokeWidth="2.5" strokeDasharray="5 3"/>
      <polygon points="206,180 210,188 214,180" fill="#5aabf0"/>

      {/* Host A */}
      <circle cx="84" cy="218" r="22" fill="#1c1400" stroke="#c9973a" strokeWidth="2.5"/>
      <rect x="79" y="204" width="10" height="15" rx="5" fill="#c9973a" opacity="0.9"/>
      <path d="M 73 218 Q 73 232 84 232 Q 95 232 95 218" fill="none" stroke="#c9973a" strokeWidth="2.5" strokeLinecap="round"/>
      <text x="84" y="244" textAnchor="middle" fill="#c9973a" fontSize="10" fontWeight="700" fontFamily="Inter,sans-serif">HOST A</text>

      {/* Host B */}
      <circle cx="278" cy="218" r="22" fill="#061422" stroke="#5aabf0" strokeWidth="2.5"/>
      <rect x="273" y="204" width="10" height="15" rx="5" fill="#5aabf0" opacity="0.9"/>
      <path d="M 267 218 Q 267 232 278 232 Q 289 232 289 218" fill="none" stroke="#5aabf0" strokeWidth="2.5" strokeLinecap="round"/>
      <text x="278" y="244" textAnchor="middle" fill="#5aabf0" fontSize="10" fontWeight="700" fontFamily="Inter,sans-serif">HOST B</text>

      {/* Speech bubbles */}
      <g className="nf-ba">
        <rect x="110" y="200" width="58" height="22" rx="11" fill="#c9973a"/>
        <polygon points="110,214 102,220 110,220" fill="#c9973a"/>
        <text x="139" y="214" textAnchor="middle" fill="#1a1000" fontSize="9.5" fontWeight="700" fontFamily="Inter,sans-serif">On air...</text>
      </g>
      <g className="nf-bb">
        <rect x="194" y="200" width="58" height="22" rx="11" fill="#5aabf0"/>
        <polygon points="252,214 260,220 252,220" fill="#5aabf0"/>
        <text x="223" y="214" textAnchor="middle" fill="white" fontSize="9.5" fontWeight="700" fontFamily="Inter,sans-serif">Agreed!</text>
      </g>
    </NarrativeSvg>
  );
}

function VisualSlides() {
  return (
    <NarrativeSvg titleId="n-slides-title" descId="n-slides-desc" title="Prepare slide deck" desc="Chapter material is transformed into a visual slide sequence.">
      <defs><style>{`
        @keyframes sl-pop{from{opacity:0;transform:scale(.88)}to{opacity:1;transform:scale(1)}}
        .sl-s1{animation:sl-pop .4s .1s both}.sl-s2{animation:sl-pop .4s .5s both}
        .sl-s3{animation:sl-pop .4s .9s both}.sl-s4{animation:sl-pop .4s 1.3s both}
      `}</style></defs>

      {/* Slide 1 — Hierarchy (blue, top-left) */}
      <g className="sl-s1">
        <rect x="8" y="10" width="158" height="108" rx="7" fill="#061422" stroke="#5aabf0" strokeWidth="2.5"/>
        <rect x="8" y="10" width="158" height="28" rx="7" fill="#5aabf0" opacity="0.35"/>
        <text x="87" y="27" textAnchor="middle" fill="white" fontSize="12" fontWeight="700" fontFamily="Inter,sans-serif">HIERARCHY</text>
        <rect x="68" y="46" width="38" height="16" rx="5" fill="#5aabf0"/>
        <text x="87" y="58" textAnchor="middle" fill="white" fontSize="9.5" fontWeight="700" fontFamily="Inter,sans-serif">ROOT</text>
        <line x1="87" y1="62" x2="44" y2="76" stroke="#5aabf0" strokeWidth="1.8" opacity="0.7"/>
        <line x1="87" y1="62" x2="87" y2="76" stroke="#5aabf0" strokeWidth="1.8" opacity="0.7"/>
        <line x1="87" y1="62" x2="130" y2="76" stroke="#5aabf0" strokeWidth="1.8" opacity="0.7"/>
        {[[30,76],[72,76],[115,76]].map(([x,y],i)=>(
          <rect key={i} x={x} y={y} width={30} height="14" rx="4" fill="#5aabf0" opacity="0.45"/>
        ))}
        <text x="87" y="107" textAnchor="middle" fill="#5aabf0" fontSize="9" fontFamily="Inter,sans-serif" opacity="0.85">SLIDE TYPE 1</text>
      </g>

      {/* Slide 2 — Quote (gold, top-right) */}
      <g className="sl-s2">
        <rect x="174" y="10" width="158" height="108" rx="7" fill="#1c1400" stroke="#c9973a" strokeWidth="2.5"/>
        <rect x="174" y="10" width="158" height="28" rx="7" fill="#c9973a" opacity="0.35"/>
        <text x="253" y="27" textAnchor="middle" fill="white" fontSize="12" fontWeight="700" fontFamily="Inter,sans-serif">QUOTE</text>
        <text x="184" y="76" fill="#ffd700" fontSize="44" fontFamily="Georgia,serif" opacity="0.85">"</text>
        <rect x="212" y="54" width="108" height="9" rx="3" fill="white" opacity="0.5"/>
        <rect x="212" y="68" width="94" height="9" rx="3" fill="white" opacity="0.38"/>
        <rect x="212" y="82" width="104" height="9" rx="3" fill="white" opacity="0.32"/>
        <text x="253" y="107" textAnchor="middle" fill="#c9973a" fontSize="9" fontFamily="Inter,sans-serif" opacity="0.85">SLIDE TYPE 2</text>
      </g>

      {/* Slide 3 — Timeline (green, bottom-left) */}
      <g className="sl-s3">
        <rect x="8" y="128" width="158" height="108" rx="7" fill="#061a0c" stroke="#5ac87a" strokeWidth="2.5"/>
        <rect x="8" y="128" width="158" height="28" rx="7" fill="#5ac87a" opacity="0.3"/>
        <text x="87" y="145" textAnchor="middle" fill="white" fontSize="12" fontWeight="700" fontFamily="Inter,sans-serif">TIMELINE</text>
        <line x1="22" y1="192" x2="154" y2="192" stroke="#5ac87a" strokeWidth="2.5" strokeLinecap="round" opacity="0.75"/>
        {[22,66,110,154].map((x,i)=>(
          <g key={i}>
            <circle cx={x} cy="192" r="8" fill="#5ac87a"/>
            <line x1={x} y1="174" x2={x} y2="184" stroke="#5ac87a" strokeWidth="1.8" opacity="0.6"/>
            <rect x={x-18} y="161" width="36" height="13" rx="4" fill="#5ac87a" opacity="0.32"/>
          </g>
        ))}
        <text x="87" y="226" textAnchor="middle" fill="#5ac87a" fontSize="9" fontFamily="Inter,sans-serif" opacity="0.85">SLIDE TYPE 3</text>
      </g>

      {/* Slide 4 — Comparison (teal, bottom-right) */}
      <g className="sl-s4">
        <rect x="174" y="128" width="158" height="108" rx="7" fill="#061818" stroke="#38c9bf" strokeWidth="2.5"/>
        <rect x="174" y="128" width="158" height="28" rx="7" fill="#38c9bf" opacity="0.3"/>
        <text x="253" y="145" textAnchor="middle" fill="white" fontSize="12" fontWeight="700" fontFamily="Inter,sans-serif">COMPARISON</text>
        <line x1="253" y1="162" x2="253" y2="226" stroke="#38c9bf" strokeWidth="1.8" opacity="0.5"/>
        {[162,180,198,216].map((y,i)=>(
          <line key={i} x1="186" y1={y} x2="322" y2={y} stroke="#38c9bf" strokeWidth="1.2" opacity="0.3"/>
        ))}
        <text x="220" y="174" textAnchor="middle" fill="#38c9bf" fontSize="10" fontWeight="700" fontFamily="Inter,sans-serif">BEFORE</text>
        <text x="287" y="174" textAnchor="middle" fill="#38c9bf" fontSize="10" fontWeight="700" fontFamily="Inter,sans-serif">AFTER</text>
        {[182,200].map((y,i)=>(
          <g key={i}>
            <rect x="190" y={y} width="56" height="12" rx="3" fill="white" opacity="0.12"/>
            <rect x="258" y={y} width="56" height="12" rx="3" fill="#38c9bf" opacity="0.3"/>
          </g>
        ))}
        <text x="253" y="226" textAnchor="middle" fill="#38c9bf" fontSize="9" fontFamily="Inter,sans-serif" opacity="0.85">SLIDE TYPE 4</text>
      </g>
    </NarrativeSvg>
  );
}

function VisualAudit() {
  return (
    <NarrativeSvg titleId="n-audit-title" descId="n-audit-desc" title="Audit the final package" desc="Quality checks loop until the chapter package passes.">
      <defs><style>{`
        @keyframes au-ck{0%{stroke-dashoffset:28}100%{stroke-dashoffset:0}}
        @keyframes au-rect{0%,55%{fill:#1e0f00;stroke:#e8b430}100%{fill:#061a0c;stroke:#5ac87a}}
        @keyframes au-bang{0%,55%{opacity:1}100%{opacity:0}}
        @keyframes au-tick{0%,55%{opacity:0;stroke-dashoffset:28}100%{opacity:1;stroke-dashoffset:0}}
        @keyframes au-loop{0%{stroke-dashoffset:340}100%{stroke-dashoffset:0}}
        @keyframes au-pass{from{opacity:0;transform:scale(.7)}to{opacity:1;transform:scale(1)}}
        .au-c1{animation:au-ck .35s .3s both;stroke-dasharray:28;stroke-dashoffset:28}
        .au-c2{animation:au-ck .35s .7s both;stroke-dasharray:28;stroke-dashoffset:28}
        .au-c3{animation:au-ck .35s 1.1s both;stroke-dasharray:28;stroke-dashoffset:28}
        .au-r4{animation:au-rect 1s 2s both}.au-r5{animation:au-rect 1s 2.4s both}
        .au-b4{animation:au-bang 1s 2s both}.au-b5{animation:au-bang 1s 2.4s both}
        .au-c4{animation:au-tick .35s 2.8s both;stroke-dasharray:28;stroke-dashoffset:28}
        .au-c5{animation:au-tick .35s 3.1s both;stroke-dasharray:28;stroke-dashoffset:28}
        .au-loop{animation:au-loop 2s .5s both;stroke-dasharray:340;stroke-dashoffset:340}
        .au-pass{animation:au-pass .5s 3.5s both;opacity:0}
        .au-kick{opacity:0}
      `}</style></defs>

      <text x="14" y="18" fill="white" fontSize="13" fontWeight="700" fontFamily="Inter,sans-serif">QUALITY CHECKS</text>

      {/* Items 1–3: green from start */}
      {[
        {y:26,  label:'Citation accuracy',  ck:'au-c1'},
        {y:66,  label:'Narrative integrity', ck:'au-c2'},
        {y:106, label:'Coverage complete',   ck:'au-c3'},
      ].map((item,i)=>(
        <g key={i}>
          <rect x="8" y={item.y} width="198" height="34" rx="6" fill="#061a0c" stroke="#5ac87a" strokeWidth="2"/>
          <text x="22" y={item.y+21} fill="white" fontSize="11" fontFamily="Inter,sans-serif">{item.label}</text>
          <circle cx="190" cy={item.y+17} r="12" fill="#5ac87a" opacity="0.28" stroke="#5ac87a" strokeWidth="2"/>
          <polyline points={`183,${item.y+17} 188,${item.y+22} 197,${item.y+11}`}
            className={item.ck} fill="none" stroke="#5ac87a" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/>
        </g>
      ))}

      {/* Items 4–5: amber → green */}
      {[
        {y:146, label:'Enrichment depth',  rCls:'au-r4', bCls:'au-b4', kCls:'au-c4'},
        {y:184, label:'Audio alignment',   rCls:'au-r5', bCls:'au-b5', kCls:'au-c5'},
      ].map((item,i)=>(
        <g key={i}>
          <rect x="8" y={item.y} width="198" height="34" rx="6" fill="#1e0f00" stroke="#e8b430" strokeWidth="2" className={item.rCls}/>
          <text x="22" y={item.y+21} fill="white" fontSize="11" fontFamily="Inter,sans-serif">{item.label}</text>
          <circle cx="190" cy={item.y+17} r="12" fill="#e8b430" opacity="0.22" stroke="#e8b430" strokeWidth="2" className={item.rCls}/>
          <text x="190" y={item.y+22} textAnchor="middle" fill="#e8b430" fontSize="15" fontWeight="700" fontFamily="Inter,sans-serif" className={item.bCls}>!</text>
          <polyline points={`183,${item.y+17} 188,${item.y+22} 197,${item.y+11}`}
            className={`${item.kCls} au-kick`} fill="none" stroke="#5ac87a" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/>
        </g>
      ))}

      {/* Revision loop — right */}
      <text x="272" y="18" textAnchor="middle" fill="white" fontSize="11" fontWeight="700" fontFamily="Inter,sans-serif">LOOP</text>
      <path d="M 272 34 A 56 56 0 1 0 271 42" className="au-loop" fill="none" stroke="#c9973a" strokeWidth="3"/>
      <polygon points="266,38 272,32 278,39" fill="#c9973a"/>
      <text x="272" y="112" textAnchor="middle" fill="white" fontSize="11" fontFamily="Inter,sans-serif" opacity="0.65">up to</text>
      <text x="272" y="140" textAnchor="middle" fill="#ffd700" fontSize="32" fontWeight="700" fontFamily="Inter,sans-serif">15×</text>
      <g className="au-pass">
        <rect x="228" y="180" width="88" height="28" rx="14" fill="#5ac87a"/>
        <text x="272" y="198" textAnchor="middle" fill="white" fontSize="12" fontWeight="700" fontFamily="Inter,sans-serif">✓ PASSED</text>
      </g>
    </NarrativeSvg>
  );
}

function VisualShip() {
  return (
    <NarrativeSvg titleId="n-ship-title" descId="n-ship-desc" title="Ship the finished episode" desc="Draft materials move into a finished packaged podcast release.">
      <defs><style>{`
        @keyframes sh-fade{0%{opacity:1}100%{opacity:.2;transform:scale(.95)}}
        @keyframes sh-slide{from{opacity:0;transform:translateX(20px)}to{opacity:1;transform:translateX(0)}}
        @keyframes sh-seal{from{opacity:0;transform:scale(0) rotate(-20deg)}to{opacity:1;transform:scale(1) rotate(0)}}
        @keyframes sh-ep{from{opacity:0;transform:translateY(-7px)}to{opacity:1;transform:translateY(0)}}
        .sh-draft{animation:sh-fade 1s .4s both}
        .sh-card{animation:sh-slide .5s .8s both}
        .sh-seal{animation:sh-seal .6s 1.5s both;transform-origin:285px 82px}
        .sh-e1{animation:sh-ep .3s 1.6s both}.sh-e2{animation:sh-ep .3s 1.95s both}
        .sh-e3{animation:sh-ep .3s 2.3s both}.sh-e4{animation:sh-ep .3s 2.65s both}
      `}</style></defs>

      {/* DRAFT stack */}
      <g className="sh-draft">
        {[6,3,0].map((o,i)=>(
          <rect key={i} x={16+o} y={16-o} width="132" height="198" rx="7" fill="#1e0808" stroke="#f05555" strokeWidth={2.2-i*0.4}/>
        ))}
        <text x="82" y="124" textAnchor="middle" fill="#f05555" fontSize="34" fontWeight="700" fontFamily="Inter,sans-serif"
          transform="rotate(-18 82 124)" opacity="0.55">DRAFT</text>
        <text x="82" y="226" textAnchor="middle" fill="#f05555" fontSize="10" fontFamily="Inter,sans-serif" opacity="0.55">IN WORKSHOP</text>
      </g>

      {/* Arrow */}
      <path d="M 160 120 L 178 120" stroke="#c9973a" strokeWidth="3.5" strokeLinecap="round"/>
      <polygon points="176,112 192,120 176,128" fill="#c9973a"/>

      {/* Published card */}
      <g className="sh-card">
        <rect x="194" y="16" width="140" height="208" rx="7" fill="#1c1400" stroke="#c9973a" strokeWidth="2.5"/>
        <rect x="194" y="16" width="140" height="38" rx="7" fill="#c9973a" opacity="0.28"/>
        <text x="264" y="36" textAnchor="middle" fill="#ffd700" fontSize="13" fontWeight="700" fontFamily="Inter,sans-serif">Ayyuhal Walad</text>
        <text x="264" y="52" textAnchor="middle" fill="#c9973a" fontSize="11" fontFamily="Inter,sans-serif">أيها الولد</text>
        <line x1="204" y1="60" x2="324" y2="60" stroke="#c9973a" strokeWidth="1" opacity="0.4"/>
        {[
          {label:'Ep 1 — The Opening Letter', cls:'sh-e1'},
          {label:'Ep 2 — Knowledge & Action',  cls:'sh-e2'},
          {label:'Ep 3 — The Inner Journey',   cls:'sh-e3'},
          {label:'Ep 4 — The Final Counsel',   cls:'sh-e4'},
        ].map((ep,i)=>(
          <g key={i} className={ep.cls}>
            <circle cx="208" cy={82+i*36} r="5.5" fill="#c9973a" opacity="0.75"/>
            <text x="220" y={87+i*36} fill="white" fontSize="9.5" fontFamily="Inter,sans-serif" opacity="0.88">{ep.label}</text>
            <line x1="204" y1={100+i*36} x2="324" y2={100+i*36} stroke="#c9973a" strokeWidth="0.8" opacity="0.22"/>
          </g>
        ))}
        <text x="264" y="218" textAnchor="middle" fill="#c9973a" fontSize="9.5" fontFamily="Inter,sans-serif" letterSpacing="1.5" opacity="0.6">PUBLISHED</text>
      </g>

      {/* VERIFIED seal */}
      <g className="sh-seal">
        <circle cx="285" cy="82" r="28" fill="#1c1400" stroke="#c9973a" strokeWidth="2.5"/>
        <circle cx="285" cy="82" r="21" fill="none" stroke="#c9973a" strokeWidth="1" strokeDasharray="4 3" opacity="0.65"/>
        <text x="285" y="77" textAnchor="middle" fill="#ffd700" fontSize="8" fontWeight="700" fontFamily="Inter,sans-serif" letterSpacing="1.5">VERI</text>
        <text x="285" y="89" textAnchor="middle" fill="#ffd700" fontSize="8" fontWeight="700" fontFamily="Inter,sans-serif" letterSpacing="1.5">FIED</text>
        <text x="285" y="68" textAnchor="middle" fill="#ffd700" fontSize="13">✦</text>
      </g>
    </NarrativeSvg>
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
                 xmlns="http://www.w3.org/2000/svg" role="img"
                 aria-labelledby="logo-placeholder-title logo-placeholder-desc">
              <title id="logo-placeholder-title">Podcast factory logo placeholder</title>
              <desc id="logo-placeholder-desc">A stylized factory outline with smokestacks and sound waves.</desc>
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

  const particles = Array.from({ length: 22 }, (_, i) => symbols[i % symbols.length]);

  return (
    <div className="narrative-hero-particles" aria-hidden="true">
      {particles.map((symbol, i) => (
        <span key={i} className="n-particle">{symbol}</span>
      ))}
    </div>
  );
}
