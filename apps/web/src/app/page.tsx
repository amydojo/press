import Link from "next/link";

export default function HomePage() {
  return (
    <main className="page-shell">
      <section className="foundation-hero" aria-labelledby="press-title">
        <p className="eyebrow">Generative media object system</p>
        <h1 id="press-title">PRESS</h1>
        <p className="promise">Keep what made you stop.</p>
        <p className="status">Foundation in progress.</p>
        <Link className="text-link" href="/system">
          Open system diagnostics
        </Link>
      </section>
    </main>
  );
}
