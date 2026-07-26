import type { PressingRecord } from "@/lib/pressings";

type PressingObjectProps = {
  pressing: PressingRecord;
  assetUrl?: string | null;
  compact?: boolean;
  back?: boolean;
};

function accentFor(pressing: PressingRecord) {
  const palette = pressing.understanding?.palette ?? [];
  return palette.find((value) => /^#[0-9a-f]{6}$/i.test(value)) ?? "#8d9c91";
}

export function PressingObject({ pressing, assetUrl, compact = false, back = false }: PressingObjectProps) {
  const accent = accentFor(pressing);
  const domain = pressing.source.domain ?? pressing.source.submittedUrl ?? pressing.anchors.submittedSourceIdentity;
  const captured = new Date(pressing.source.capturedAt ?? pressing.createdAt ?? Date.now());

  return (
    <article
      className={`pressing-object ${compact ? "pressing-object--compact" : ""} ${back ? "pressing-object--back" : ""}`}
      style={{ "--pressing-accent": accent } as React.CSSProperties}
      aria-label={`${back ? "Back" : "Front"} of ${pressing.serialNumber} from ${domain}`}
    >
      <div className="pressing-object__shadow" aria-hidden="true" />
      <div className="pressing-object__rear" aria-hidden="true" />
      <div className="pressing-object__body">
        <div className="pressing-object__edge" aria-hidden="true" />
        <div className="pressing-object__highlight" aria-hidden="true" />
        {!back ? (
          <>
            <div className="pressing-object__world" aria-hidden="true">
              {assetUrl ? <img src={assetUrl} alt="" /> : <div className="pressing-object__fallback" />}
            </div>
            <div className="pressing-object__front-copy">
              <p className="pressing-object__domain">{domain}</p>
              <blockquote>{pressing.anchors.selectedFragment}</blockquote>
              <p className="pressing-object__serial">{pressing.serialNumber}</p>
            </div>
          </>
        ) : (
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
        )}
      </div>
    </article>
  );
}
