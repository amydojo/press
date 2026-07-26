"use client";

import { useRef, useState } from "react";
import type { CSSProperties, PointerEvent } from "react";

import type { PressingRecord } from "@/lib/pressings";

type PressingObjectProps = {
  pressing: PressingRecord;
  assetUrl?: string | null;
  compact?: boolean;
  back?: boolean;
  interactive?: boolean;
  revealed?: boolean;
  onSideChange?: (back: boolean) => void;
};

function accentFor(pressing: PressingRecord) {
  const palette = pressing.understanding?.palette ?? [];
  return palette.find((value) => /^#[0-9a-f]{6}$/i.test(value)) ?? "#8d9c91";
}

export function PressingObject({
  pressing,
  assetUrl,
  compact = false,
  back = false,
  interactive = false,
  revealed = false,
  onSideChange,
}: PressingObjectProps) {
  const accent = accentFor(pressing);
  const domain = pressing.source.domain ?? pressing.source.submittedUrl ?? pressing.anchors.submittedSourceIdentity;
  const captured = new Date(pressing.source.capturedAt ?? pressing.createdAt ?? Date.now());
  const frame = useRef<number | null>(null);
  const [tilt, setTilt] = useState({ x: 0, y: 0 });

  function updateTilt(event: PointerEvent<HTMLElement>) {
    if (!interactive) return;
    const bounds = event.currentTarget.getBoundingClientRect();
    const x = (event.clientX - bounds.left) / bounds.width - 0.5;
    const y = (event.clientY - bounds.top) / bounds.height - 0.5;
    if (frame.current) cancelAnimationFrame(frame.current);
    frame.current = requestAnimationFrame(() => setTilt({ x: y * -12, y: x * 16 }));
  }

  function resetTilt() {
    if (!interactive) return;
    setTilt({ x: 0, y: 0 });
  }

  function toggleSide() {
    if (!interactive || !onSideChange) return;
    onSideChange(!back);
  }

  const style = {
    "--pressing-accent": accent,
    "--pressing-rotate-x": `${tilt.x}deg`,
    "--pressing-rotate-y": `${tilt.y + (back ? 180 : 0)}deg`,
  } as CSSProperties;

  return (
    <article
      className={`pressing-object ${compact ? "pressing-object--compact" : ""} ${interactive ? "pressing-object--interactive" : ""} ${revealed ? "pressing-object--revealed" : ""}`}
      style={style}
      aria-label={`${back ? "Back" : "Front"} of ${pressing.serialNumber} from ${domain}`}
      aria-live="polite"
      onPointerMove={updateTilt}
      onPointerLeave={resetTilt}
      onPointerUp={resetTilt}
      onDoubleClick={toggleSide}
    >
      <div className="pressing-object__shadow" aria-hidden="true" />
      <div className="pressing-object__stage">
        <div className="pressing-object__body">
          <div className="pressing-object__face pressing-object__face--front">
            <div className="pressing-object__rear" aria-hidden="true" />
            <div className="pressing-object__edge" aria-hidden="true" />
            <div className="pressing-object__world" aria-hidden="true">
              {assetUrl ? <img src={assetUrl} alt="" /> : <div className="pressing-object__fallback"><span /><span /><span /></div>}
            </div>
            <div className="pressing-object__depth pressing-object__depth--one" aria-hidden="true" />
            <div className="pressing-object__depth pressing-object__depth--two" aria-hidden="true" />
            <div className="pressing-object__highlight" aria-hidden="true" />
            <div className="pressing-object__front-copy">
              <p className="pressing-object__domain">{domain}</p>
              <blockquote>{pressing.anchors.selectedFragment}</blockquote>
              <p className="pressing-object__serial">{pressing.serialNumber}</p>
            </div>
          </div>
          <div className="pressing-object__face pressing-object__face--back">
            <div className="pressing-object__metadata">
              <p className="pressing-object__kicker">Pressed from the internet</p>
              <p className="pressing-object__serial">{pressing.serialNumber}</p>
              <dl>
                <div><dt>Source</dt><dd>{domain}</dd></div>
                <div><dt>Captured</dt><dd>{captured.toLocaleString()}</dd></div>
                <div><dt>Fragment</dt><dd>{pressing.anchors.selectedFragment}</dd></div>
                <div><dt>Why it stopped me</dt><dd>{pressing.anchors.personalNote}</dd></div>
              </dl>
              <p className="pressing-object__mark">PRESS</p>
            </div>
          </div>
        </div>
      </div>
    </article>
  );
}
