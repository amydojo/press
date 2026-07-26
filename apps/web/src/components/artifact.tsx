import type { Pressing } from "@/lib/pressings";

export function PressingArtifact({ pressing, compact = false }: { pressing: Pressing; compact?: boolean }) {
  const title = pressing.result?.title ?? "Artifact unavailable";
  return (
    <figure className={`artifact ${compact ? "artifact--compact" : ""}`} aria-label={`${title} artifact`}>
      <div className="artifact__machine" aria-hidden="true">
        <div className="artifact__slot" />
        <div className="artifact__sheet">
          <span className="artifact__index">{pressing.number}</span>
          <span className="artifact__signal">DECIDING<br />WHETHER<br />TO CONTINUE</span>
          <span className="artifact__rule" />
          <span className="artifact__caption">A domestic machine caught in hesitation.</span>
        </div>
        <div className="artifact__sleeve" />
      </div>
      {!compact && <figcaption className="sr-only">A manufactured editorial object titled {title}.</figcaption>}
    </figure>
  );
}
