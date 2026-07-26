import Link from "next/link";

export default function HomePage() {
  return (
    <main className="product-shell home-shell">
      <header className="product-nav"><Link href="/">PRESS</Link><Link href="/pressings">Your pressings</Link></header>
      <section className="home-hero" aria-labelledby="press-title">
        <p className="eyebrow">A small object for what mattered</p>
        <h1 id="press-title">Keep what made you stop.</h1>
        <p className="promise">Turn one source, one exact fragment, and one human sentence into a collectible pressing.</p>
        <div className="home-actions"><Link className="primary-button" href="/press/new">Press something</Link><Link className="text-link" href="/pressings">Open your collection</Link></div>
      </section>
      <section className="home-process" aria-label="How PRESS works">
        <article><span>01</span><h2>Capture</h2><p>Bring the exact source and fragment that caught you.</p></article>
        <article><span>02</span><h2>Press</h2><p>PRESS creates a miniature world inside one consistent shell.</p></article>
        <article><span>03</span><h2>Keep</h2><p>Reopen the object later without losing your original words.</p></article>
      </section>
    </main>
  );
}
