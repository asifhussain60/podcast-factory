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
    <svg viewBox="0 0 300 220" xmlns="http://www.w3.org/2000/svg">
      {/* Scanner beam moving across a document */}
      <rect x="40" y="30" width="220" height="160" rx="4" fill="none" stroke="rgba(201,151,58,0.2)" strokeWidth="1.5"/>
      {/* Page lines */}
      {[55, 72, 89, 106, 123, 140, 157, 174].map((y, i) => (
        <line key={i} x1="60" y1={y} x2={180 - i * 4} y2={y}
          stroke="rgba(240,236,227,0.15)" strokeWidth="1.5" strokeLinecap="round"/>
      ))}
      {/* Scanner beam */}
      <rect x="40" y="88" width="220" height="3" rx="1.5"
        fill="rgba(201,151,58,0.5)"
        style={{ filter: 'blur(2px)' }}>
        <animate attributeName="y" values="30;187;30" dur="3s" repeatCount="indefinite" calcMode="ease-in-out"/>
      </rect>
      <rect x="40" y="88" width="220" height="18" rx="2"
        fill="rgba(201,151,58,0.04)">
        <animate attributeName="y" values="22;179;22" dur="3s" repeatCount="indefinite" calcMode="ease-in-out"/>
      </rect>
      {/* Corner marks */}
      {([[40,30],[260,30],[40,190],[260,190]] as [number,number][]).map(([x,y], i) => (
        <g key={i}>
          <line x1={x} y1={y} x2={x + (x < 150 ? 14 : -14)} y2={y}
            stroke="rgba(201,151,58,0.5)" strokeWidth="1.5" strokeLinecap="round"/>
          <line x1={x} y1={y} x2={x} y2={y + (y < 110 ? 14 : -14)}
            stroke="rgba(201,151,58,0.5)" strokeWidth="1.5" strokeLinecap="round"/>
        </g>
      ))}
      {/* Labels */}
      <text x="150" y="215" textAnchor="middle" fill="rgba(201,151,58,0.4)"
        fontSize="11" fontFamily="Inter, sans-serif" letterSpacing="2">READING</text>
    </svg>
  );
}

function VisualPolishText() {
  const before = 'Th3 schol@r said,\n"Kn0wledge is—\na trust."';
  const after  = 'The scholar said,\n"Knowledge is\na trust."';
  return (
    <svg viewBox="0 0 300 220" xmlns="http://www.w3.org/2000/svg">
      {/* Before card */}
      <rect x="20" y="30" width="115" height="90" rx="4"
        fill="rgba(168,50,50,0.08)" stroke="rgba(168,50,50,0.25)" strokeWidth="1"/>
      <text x="30" y="52" fill="rgba(240,100,100,0.7)" fontSize="10"
        fontFamily="Inter, sans-serif" fontWeight="600" letterSpacing="1">BEFORE</text>
      {before.split('\n').map((line, i) => (
        <text key={i} x="30" y={68 + i * 16} fill="rgba(240,236,227,0.45)"
          fontSize="11" fontFamily="'Source Serif 4', serif">{line}</text>
      ))}
      {/* Arrow */}
      <path d="M148 75 L165 75" stroke="rgba(201,151,58,0.5)"
        strokeWidth="1.5" strokeLinecap="round"/>
      <polygon points="163,71 169,75 163,79" fill="rgba(201,151,58,0.5)"/>
      {/* After card */}
      <rect x="168" y="30" width="115" height="90" rx="4"
        fill="rgba(74,124,74,0.08)" stroke="rgba(74,124,74,0.25)" strokeWidth="1"/>
      <text x="178" y="52" fill="rgba(126,207,126,0.7)" fontSize="10"
        fontFamily="Inter, sans-serif" fontWeight="600" letterSpacing="1">AFTER</text>
      {after.split('\n').map((line, i) => (
        <text key={i} x="178" y={68 + i * 16} fill="rgba(240,236,227,0.7)"
          fontSize="11" fontFamily="'Source Serif 4', serif">{line}</text>
      ))}
      {/* Underline corrections */}
      <line x1="30" y1="72" x2="100" y2="72"
        stroke="rgba(168,50,50,0.5)" strokeWidth="1" strokeDasharray="3 2"/>
      <text x="150" y="215" textAnchor="middle" fill="rgba(201,151,58,0.4)"
        fontSize="11" fontFamily="Inter, sans-serif" letterSpacing="2">POLISHING</text>
    </svg>
  );
}

function VisualLearnNames() {
  // Network of name nodes radiating from center
  const center = { x: 150, y: 110 };
  const nodes = [
    { x: 150, y: 45, label: 'Ibn Sina', type: 'scholar' },
    { x: 230, y: 75, label: 'Baghdad', type: 'place' },
    { x: 255, y: 145, label: '980 CE', type: 'date' },
    { x: 205, y: 185, label: 'al-Qifṭī', type: 'scholar' },
    { x: 95,  y: 185, label: 'Hamadan', type: 'place' },
    { x: 45,  y: 145, label: 'Peripatetic', type: 'term' },
    { x: 50,  y: 75,  label: 'al-Fārābī', type: 'scholar' },
    { x: 105, y: 45,  label: '1037 CE', type: 'date' },
  ];
  const colors: Record<string, string> = {
    scholar: 'rgba(201,151,58,',
    place:   'rgba(74,124,74,',
    date:    'rgba(26,92,138,',
    term:    'rgba(139,69,19,',
  };
  return (
    <svg viewBox="0 0 300 220" xmlns="http://www.w3.org/2000/svg">
      {nodes.map((n, i) => (
        <line key={i} x1={center.x} y1={center.y} x2={n.x} y2={n.y}
          stroke={`${colors[n.type]}0.2)`} strokeWidth="1"/>
      ))}
      {/* Center */}
      <circle cx={center.x} cy={center.y} r="22"
        fill={`${colors.term}0.08)`} stroke={`${colors.term}0.35)`} strokeWidth="1.5"/>
      <text x={center.x} y={center.y + 4} textAnchor="middle"
        fill="rgba(240,236,227,0.8)" fontSize="9" fontFamily="Inter, sans-serif">SOURCE</text>
      {nodes.map((n, i) => (
        <g key={i}>
          <circle cx={n.x} cy={n.y} r="16"
            fill={`${colors[n.type]}0.08)`}
            stroke={`${colors[n.type]}0.35)`} strokeWidth="1"/>
          <text x={n.x} y={n.y + 4} textAnchor="middle"
            fill={`${colors[n.type]}0.85)`} fontSize="8"
            fontFamily="Inter, sans-serif">{n.label}</text>
        </g>
      ))}
      <text x="150" y="215" textAnchor="middle" fill="rgba(201,151,58,0.4)"
        fontSize="11" fontFamily="Inter, sans-serif" letterSpacing="2">IDENTIFYING</text>
    </svg>
  );
}

function VisualPlanEpisodes() {
  // Blueprint-style episode arc diagram
  const chapters = [
    { w: 60, label: 'Ch 1' },
    { w: 40, label: 'Ch 2' },
    { w: 80, label: 'Ch 3' },
    { w: 35, label: 'Ch 4' },
    { w: 55, label: 'Ch 5' },
  ];
  const episodes = [
    { x: 20,  w: 115, label: 'Ep 1' },
    { x: 143, w: 80,  label: 'Ep 2' },
    { x: 231, w: 50,  label: 'Ep 3' },
  ];
  let cx = 20;
  return (
    <svg viewBox="0 0 300 200" xmlns="http://www.w3.org/2000/svg">
      <text x="14" y="44" fill="rgba(240,236,227,0.35)" fontSize="10"
        fontFamily="Inter, sans-serif" letterSpacing="1">CHAPTERS</text>
      {chapters.map((ch, i) => {
        const x = cx;
        cx += ch.w + 4;
        return (
          <g key={i}>
            <rect x={x} y={50} width={ch.w} height={28} rx="3"
              fill="rgba(240,236,227,0.06)" stroke="rgba(240,236,227,0.18)" strokeWidth="1"/>
            <text x={x + ch.w / 2} y={68} textAnchor="middle"
              fill="rgba(240,236,227,0.45)" fontSize="9"
              fontFamily="Inter, sans-serif">{ch.label}</text>
          </g>
        );
      })}
      {/* Arrow down */}
      <line x1="150" y1="84" x2="150" y2="102"
        stroke="rgba(201,151,58,0.4)" strokeWidth="1.5" strokeDasharray="4 3"/>
      <polygon points="146,100 150,107 154,100" fill="rgba(201,151,58,0.4)"/>
      <text x="14" y="125" fill="rgba(201,151,58,0.4)" fontSize="10"
        fontFamily="Inter, sans-serif" letterSpacing="1">EPISODES</text>
      {episodes.map((ep, i) => (
        <g key={i}>
          <rect x={ep.x} y={130} width={ep.w} height={28} rx="3"
            fill="rgba(201,151,58,0.08)" stroke="rgba(201,151,58,0.35)" strokeWidth="1"/>
          <text x={ep.x + ep.w / 2} y={148} textAnchor="middle"
            fill="rgba(201,151,58,0.75)" fontSize="9"
            fontFamily="Inter, sans-serif">{ep.label}</text>
        </g>
      ))}
      <text x="150" y="195" textAnchor="middle" fill="rgba(201,151,58,0.4)"
        fontSize="11" fontFamily="Inter, sans-serif" letterSpacing="2">STRUCTURING</text>
    </svg>
  );
}

function VisualEnrich() {
  // Layered document — context notes appearing around text
  return (
    <svg viewBox="0 0 300 210" xmlns="http://www.w3.org/2000/svg">
      {/* Core document */}
      <rect x="75" y="25" width="150" height="160" rx="4"
        fill="rgba(240,236,227,0.04)" stroke="rgba(240,236,227,0.15)" strokeWidth="1.5"/>
      {[45, 60, 75, 90, 105, 120, 135, 150, 165].map((y, i) => (
        <line key={i} x1="92" y1={y} x2={190 - i * 3} y2={y}
          stroke="rgba(240,236,227,0.12)" strokeWidth="1.2" strokeLinecap="round"/>
      ))}
      {/* Context callout bubbles */}
      {[
        { x: 8,   y: 42,  w: 60, label: 'Context', color: 'rgba(26,92,138,' },
        { x: 232, y: 65,  w: 62, label: 'Who?',    color: 'rgba(74,124,74,' },
        { x: 8,   y: 120, w: 60, label: 'Why now?', color: 'rgba(139,69,19,' },
        { x: 232, y: 140, w: 62, label: 'Source',   color: 'rgba(201,151,58,' },
      ].map((b, i) => (
        <g key={i}>
          <rect x={b.x} y={b.y} width={b.w} height={22} rx="11"
            fill={`${b.color}0.1)`} stroke={`${b.color}0.35)`} strokeWidth="1"/>
          <text x={b.x + b.w / 2} y={b.y + 14} textAnchor="middle"
            fill={`${b.color}0.8)`} fontSize="9"
            fontFamily="Inter, sans-serif">{b.label}</text>
          {/* Connector line */}
          <line
            x1={b.x < 75 ? b.x + b.w : b.x}
            y1={b.y + 11}
            x2={b.x < 75 ? 75 : 225}
            y2={b.y + 8}
            stroke={`${b.color}0.25)`} strokeWidth="1" strokeDasharray="3 2"/>
        </g>
      ))}
      <text x="150" y="205" textAnchor="middle" fill="rgba(201,151,58,0.4)"
        fontSize="11" fontFamily="Inter, sans-serif" letterSpacing="2">ENRICHING</text>
    </svg>
  );
}

function VisualOutsideKnowledge() {
  // Streams converging into the document from outside
  const streams = [
    { x1: 20,  y1: 30, label: 'Research papers',     color: 'rgba(201,151,58,' },
    { x1: 20,  y1: 80, label: 'Historical records',  color: 'rgba(74,124,74,'  },
    { x1: 20,  y1: 130,label: 'Cross-references',    color: 'rgba(26,92,138,'  },
    { x1: 20,  y1: 180,label: 'Verified citations',  color: 'rgba(139,69,19,'  },
  ];
  return (
    <svg viewBox="0 0 300 210" xmlns="http://www.w3.org/2000/svg">
      {/* Central document */}
      <rect x="175" y="70" width="105" height="80" rx="4"
        fill="rgba(201,151,58,0.06)" stroke="rgba(201,151,58,0.3)" strokeWidth="1.5"/>
      {[85, 100, 115, 130, 145].map((y, i) => (
        <line key={i} x1="188" y1={y} x2={265 - i * 6} y2={y}
          stroke="rgba(240,236,227,0.12)" strokeWidth="1.2" strokeLinecap="round"/>
      ))}
      <text x="227" y="158" textAnchor="middle" fill="rgba(201,151,58,0.5)"
        fontSize="9" fontFamily="Inter, sans-serif">EPISODE</text>
      {streams.map((s, i) => (
        <g key={i}>
          {/* Source label chip */}
          <rect x={s.x1} y={s.y1 - 10} width={140} height={20} rx="10"
            fill={`${s.color}0.08)`} stroke={`${s.color}0.2)`} strokeWidth="1"/>
          <text x={s.x1 + 10} y={s.y1 + 4} fill={`${s.color}0.65)`}
            fontSize="9" fontFamily="Inter, sans-serif">{s.label}</text>
          {/* Stream arrow */}
          <path d={`M ${s.x1 + 140} ${s.y1} Q 168 ${s.y1} 175 110`}
            fill="none" stroke={`${s.color}0.2)`} strokeWidth="1.5"
            strokeDasharray="4 3"/>
        </g>
      ))}
      <text x="150" y="205" textAnchor="middle" fill="rgba(201,151,58,0.4)"
        fontSize="11" fontFamily="Inter, sans-serif" letterSpacing="2">AUGMENTING</text>
    </svg>
  );
}

function VisualCutPieces() {
  // Slicing bar across chapters → separate bundles
  return (
    <svg viewBox="0 0 300 200" xmlns="http://www.w3.org/2000/svg">
      {/* Long document bar */}
      <rect x="20" y="60" width="260" height="40" rx="4"
        fill="rgba(240,236,227,0.05)" stroke="rgba(240,236,227,0.15)" strokeWidth="1.5"/>
      {/* Chapter dividers with cut lines */}
      {[110, 185, 245].map((x, i) => (
        <line key={i} x1={x} y1="50" x2={x} y2="110"
          stroke="rgba(201,151,58,0.6)" strokeWidth="1.5" strokeDasharray="5 3"/>
      ))}
      {/* Cut blade icons */}
      {[110, 185, 245].map((x, i) => (
        <polygon key={i} points={`${x-5},48 ${x+5},48 ${x},56`}
          fill="rgba(201,151,58,0.6)"/>
      ))}
      {/* Resulting bundle cards below */}
      {[
        { x: 20,  w: 85, label: 'Bundle 1' },
        { x: 115, w: 65, label: 'Bundle 2' },
        { x: 190, w: 55, label: 'Bundle 3' },
        { x: 255, w: 25, label: 'B4' },
      ].map((b, i) => (
        <g key={i}>
          <line x1={b.x + b.w/2} y1="110" x2={b.x + b.w/2} y2="122"
            stroke="rgba(201,151,58,0.25)" strokeWidth="1"/>
          <rect x={b.x + 2} y="122" width={b.w - 4} height="32" rx="3"
            fill="rgba(201,151,58,0.07)" stroke="rgba(201,151,58,0.3)" strokeWidth="1"/>
          <text x={b.x + b.w/2} y="142" textAnchor="middle"
            fill="rgba(201,151,58,0.65)" fontSize="9"
            fontFamily="Inter, sans-serif">{b.label}</text>
        </g>
      ))}
      <text x="150" y="192" textAnchor="middle" fill="rgba(201,151,58,0.4)"
        fontSize="11" fontFamily="Inter, sans-serif" letterSpacing="2">SLICING</text>
    </svg>
  );
}

function VisualNarratorFraming() {
  // Briefing document with two host avatars
  return (
    <svg viewBox="0 0 300 200" xmlns="http://www.w3.org/2000/svg">
      {/* Briefing card */}
      <rect x="40" y="20" width="220" height="120" rx="6"
        fill="rgba(26,92,138,0.07)" stroke="rgba(26,92,138,0.25)" strokeWidth="1.5"/>
      <text x="55" y="44" fill="rgba(106,180,240,0.6)" fontSize="10"
        fontFamily="Inter, sans-serif" fontWeight="600" letterSpacing="1">EPISODE BRIEF</text>
      {[58, 72, 86, 100, 114, 128].map((y, i) => (
        <line key={i} x1="55" y1={y} x2={230 - i * 8} y2={y}
          stroke="rgba(240,236,227,0.1)" strokeWidth="1.2" strokeLinecap="round"/>
      ))}
      {/* Two host circles */}
      <circle cx="100" cy="168" r="18"
        fill="rgba(201,151,58,0.08)" stroke="rgba(201,151,58,0.4)" strokeWidth="1.5"/>
      <text x="100" y="172" textAnchor="middle"
        fill="rgba(201,151,58,0.7)" fontSize="10"
        fontFamily="Inter, sans-serif">H₁</text>
      <circle cx="200" cy="168" r="18"
        fill="rgba(74,124,74,0.08)" stroke="rgba(74,124,74,0.4)" strokeWidth="1.5"/>
      <text x="200" y="172" textAnchor="middle"
        fill="rgba(126,207,126,0.7)" fontSize="10"
        fontFamily="Inter, sans-serif">H₂</text>
      {/* Lines from brief to hosts */}
      <path d="M 150 140 Q 100 154 100 150" fill="none"
        stroke="rgba(201,151,58,0.2)" strokeWidth="1" strokeDasharray="3 2"/>
      <path d="M 150 140 Q 200 154 200 150" fill="none"
        stroke="rgba(74,124,74,0.2)" strokeWidth="1" strokeDasharray="3 2"/>
      <text x="150" y="197" textAnchor="middle" fill="rgba(201,151,58,0.4)"
        fontSize="11" fontFamily="Inter, sans-serif" letterSpacing="2">FRAMING</text>
    </svg>
  );
}

function VisualSlides() {
  // Slide deck thumbnails arranged as a fan
  const slides = [
    { rotate: -12, x: -35, fill: 'rgba(26,92,138,0.08)',   stroke: 'rgba(26,92,138,0.25)' },
    { rotate: -5,  x: -12, fill: 'rgba(74,124,74,0.08)',   stroke: 'rgba(74,124,74,0.25)' },
    { rotate: 3,   x: 12,  fill: 'rgba(139,69,19,0.08)',   stroke: 'rgba(139,69,19,0.25)' },
    { rotate: 10,  x: 35,  fill: 'rgba(201,151,58,0.12)',  stroke: 'rgba(201,151,58,0.45)' },
  ];
  return (
    <svg viewBox="0 0 300 200" xmlns="http://www.w3.org/2000/svg">
      <g transform="translate(150 105)">
        {slides.map((s, i) => (
          <g key={i} transform={`rotate(${s.rotate}) translate(${s.x} 0)`}>
            <rect x="-45" y="-60" width="90" height="68" rx="4"
              fill={s.fill} stroke={s.stroke} strokeWidth="1.5"/>
            {/* Slide content lines */}
            <line x1="-32" y1="-44" x2="32" y2="-44"
              stroke="rgba(240,236,227,0.12)" strokeWidth="1.5" strokeLinecap="round"/>
            {[-28, -16, -4, 8].map((y, j) => (
              <line key={j} x1="-32" y1={y} x2={20 - j * 4} y2={y}
                stroke="rgba(240,236,227,0.08)" strokeWidth="1" strokeLinecap="round"/>
            ))}
          </g>
        ))}
      </g>
      <text x="150" y="192" textAnchor="middle" fill="rgba(201,151,58,0.4)"
        fontSize="11" fontFamily="Inter, sans-serif" letterSpacing="2">DESIGNING</text>
    </svg>
  );
}

function VisualAudit() {
  // Review loop with arrows cycling, pass/fail flags
  return (
    <svg viewBox="0 0 300 200" xmlns="http://www.w3.org/2000/svg">
      {/* Center review icon */}
      <circle cx="150" cy="95" r="30"
        fill="rgba(201,151,58,0.07)" stroke="rgba(201,151,58,0.3)" strokeWidth="1.5"/>
      <text x="150" y="91" textAnchor="middle"
        fill="rgba(201,151,58,0.8)" fontSize="11"
        fontFamily="Inter, sans-serif">AUDIT</text>
      <text x="150" y="105" textAnchor="middle"
        fill="rgba(201,151,58,0.5)" fontSize="9"
        fontFamily="Inter, sans-serif">up to 15×</text>
      {/* Outer ring */}
      <circle cx="150" cy="95" r="55"
        fill="none" stroke="rgba(201,151,58,0.1)" strokeWidth="1" strokeDasharray="4 5"/>
      {/* Rotate arrow around ring */}
      <path d="M 205 95 A 55 55 0 1 0 204 89"
        fill="none" stroke="rgba(201,151,58,0.35)" strokeWidth="1.5"/>
      <polygon points="200,84 207,90 213,83" fill="rgba(201,151,58,0.5)"/>
      {/* Pass / fail chips */}
      <rect x="20" y="35" width="50" height="18" rx="9"
        fill="rgba(168,50,50,0.1)" stroke="rgba(168,50,50,0.3)" strokeWidth="1"/>
      <text x="45" y="48" textAnchor="middle"
        fill="rgba(220,80,80,0.75)" fontSize="9"
        fontFamily="Inter, sans-serif">Flag</text>
      <rect x="230" y="35" width="50" height="18" rx="9"
        fill="rgba(74,124,74,0.1)" stroke="rgba(74,124,74,0.3)" strokeWidth="1"/>
      <text x="255" y="48" textAnchor="middle"
        fill="rgba(126,207,126,0.75)" fontSize="9"
        fontFamily="Inter, sans-serif">Pass</text>
      {/* Fix loop arrow */}
      <path d="M 45 44 Q 30 140 90 148 Q 130 155 150 150"
        fill="none" stroke="rgba(168,50,50,0.2)" strokeWidth="1" strokeDasharray="3 3"/>
      <text x="150" y="192" textAnchor="middle" fill="rgba(201,151,58,0.4)"
        fontSize="11" fontFamily="Inter, sans-serif" letterSpacing="2">CONVERGING</text>
    </svg>
  );
}

function VisualShip() {
  // Catalog shelf with books + checkmark
  const books = [
    { color: 'rgba(201,151,58,', h: 90 },
    { color: 'rgba(74,124,74,',  h: 80 },
    { color: 'rgba(26,92,138,',  h: 100 },
    { color: 'rgba(139,69,19,',  h: 75 },
    { color: 'rgba(201,151,58,', h: 88 },
  ];
  let bx = 48;
  return (
    <svg viewBox="0 0 300 200" xmlns="http://www.w3.org/2000/svg">
      {/* Shelf line */}
      <line x1="40" y1="162" x2="260" y2="162"
        stroke="rgba(240,236,227,0.2)" strokeWidth="2" strokeLinecap="round"/>
      {books.map((b, i) => {
        const x = bx;
        bx += 42;
        return (
          <g key={i}>
            <rect x={x} y={162 - b.h} width="32" height={b.h} rx="2"
              fill={`${b.color}0.12)`} stroke={`${b.color}0.4)`} strokeWidth="1.5"/>
            {/* Spine line */}
            <line x1={x + 6} y1={162 - b.h + 8} x2={x + 6} y2={162 - 8}
              stroke={`${b.color}0.25)`} strokeWidth="1"/>
          </g>
        );
      })}
      {/* Checkmark badge on last book */}
      <circle cx={bx - 42 + 16} cy={162 - books[books.length-1].h - 14} r="12"
        fill="rgba(74,124,74,0.15)" stroke="rgba(74,124,74,0.6)" strokeWidth="1.5"/>
      <polyline points={`${bx-42+9},${162-books[books.length-1].h-14} ${bx-42+14},${162-books[books.length-1].h-9} ${bx-42+23},${162-books[books.length-1].h-19}`}
        fill="none" stroke="rgba(126,207,126,0.9)" strokeWidth="2" strokeLinecap="round"/>
      <text x="150" y="192" textAnchor="middle" fill="rgba(201,151,58,0.4)"
        fontSize="11" fontFamily="Inter, sans-serif" letterSpacing="2">PUBLISHING</text>
    </svg>
  );
}

// Real images override SVG placeholders as they arrive.
// Add entries here as each station image is generated.
const PHASE_IMAGES: Record<string, string> = {
  P0: '/stations/p0.jpg',
  P1: '/stations/p1.jpg',
  P2: '/stations/p2.jpg',
  P3: '/stations/p3.jpg',
  P4: '/stations/p4.jpg',
  P5: '/stations/p5.jpg',
  P6: '/stations/p6.jpg',
  P7: '/stations/p7.jpg',
  P8: '/stations/p8.jpg',
  P9: '/stations/p9.jpg',
  P10: '/stations/p10.jpg',
};

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
