import Link from "next/link";

import { PressingObject } from "@/components/pressing-object";
import { listPressings, type PressingResponse } from "@/lib/pressings";

export const dynamic = "force-dynamic";

export default async function PressingsPage() {
  let items: PressingResponse[] = [];
  let error = "";
  try {
    items = await listPressings();
  } catch (caught) {
    error = caught instanceof Error ? caught.message : "Your pressings could not be loaded.";
  }

  const ready = items
    .filter((item) => item.pressing.status === "ready")
    .sort((a, b) => new Date(b.pressing.createdAt ?? 0).getTime() - new Date(a.pressing.createdAt ?? 0).getTime());

  return (
    <main className="product-shell">
      <header className="product-nav"><Link href="/">PRESS</Link><Link className="primary-link" href="/press/new">Press something</Link></header>
      <section className="archive-heading"><p className="eyebrow">Collection</p><h1>Your pressings</h1></section>
      {error ? <section className="empty-state"><p>Your pressings could not be loaded.</p><p className="helper">{error}</p><Link className="text-link" href="/pressings">Try again</Link></section> : null}
      {!error && ready.length === 0 ? <section className="empty-state"><p>Nothing pressed yet.</p><p>Start with something worth keeping.</p><Link className="primary-link" href="/press/new">Create a pressing</Link></section> : null}
      <section className="archive-grid" aria-label="Saved pressings">
        {ready.map(({ pressing, finalAssetAccess }) => {
          const createdAt = pressing.createdAt;
          return (
            <Link className="archive-item" href={`/pressings/${pressing.id}`} key={pressing.id} aria-label={`Open ${pressing.serialNumber} from ${pressing.source.domain ?? pressing.anchors.submittedSourceIdentity}`}>
              <PressingObject pressing={pressing} assetUrl={finalAssetAccess?.url} compact />
              <div className="archive-item__caption"><strong>{pressing.serialNumber}</strong><span>{pressing.source.domain ?? pressing.anchors.submittedSourceIdentity}</span><time>{createdAt ? new Date(createdAt).toLocaleDateString() : "Unknown"}</time></div>
            </Link>
          );
        })}
      </section>
    </main>
  );
}
