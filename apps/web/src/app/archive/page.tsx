"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { PressingArtifact } from "@/components/artifact";
import { browserRepository, type Pressing } from "@/lib/pressings";

export default function ArchivePage() {
  const [pressings, setPressings] = useState<Pressing[] | null>(null);
  const [malformed, setMalformed] = useState(false);

  useEffect(() => {
    const repository = browserRepository();
    setMalformed(repository.hasMalformedData());
    setPressings(repository.listKept());
  }, []);

  return (
    <main className="page-shell page-shell--top">
      <header className="site-header"><Link href="/" className="brand">PRESS</Link><span className="quiet-label">Local archive</span></header>
      <section className="archive" aria-labelledby="archive-title">
        <div className="archive-heading"><p className="eyebrow">Kept pressings</p><h1 id="archive-title" className="display-small">Archive</h1></div>
        {malformed && <p className="storage-note" role="status">One or more damaged local records were ignored.</p>}
        {pressings === null ? <p>Reading local archive…</p> : pressings.length === 0 ? (
          <div className="empty-state"><p>Nothing has been kept yet.</p><Link className="button button--primary" href="/">Make a pressing</Link></div>
        ) : (
          <ol className="archive-list">
            {pressings.map((pressing) => (
              <li key={pressing.id}>
                <Link href={`/pressings/${pressing.id}`} className="archive-item" aria-label={`Open ${pressing.result?.title ?? "pressing"}, ${pressing.number}`}>
                  <div className="archive-object"><PressingArtifact pressing={pressing} compact /></div>
                  <div className="archive-copy">
                    <span className="archive-number">{pressing.number}</span>
                    <h2>{pressing.result?.title ?? "Artifact unavailable"}</h2>
                    <p>{pressing.source.content.slice(0, 110)}{pressing.source.content.length > 110 ? "…" : ""}</p>
                    <time dateTime={pressing.keptAt}>Kept {pressing.keptAt ? new Date(pressing.keptAt).toLocaleDateString() : "date unavailable"}</time>
                  </div>
                </Link>
              </li>
            ))}
          </ol>
        )}
      </section>
    </main>
  );
}
