import Link from "next/link";

export default function PressingNotFound() {
  return (
    <main className="product-shell">
      <header className="product-nav"><Link href="/">PRESS</Link><Link href="/pressings">Your pressings</Link></header>
      <section className="empty-state">
        <p className="eyebrow">Missing pressing</p>
        <h1>This pressing could not be found.</h1>
        <p>It may have been deleted, or PRESS may be temporarily unable to load it.</p>
        <Link className="primary-link" href="/pressings">Return to your pressings</Link>
      </section>
    </main>
  );
}
