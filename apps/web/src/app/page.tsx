import Link from "next/link";

import { PressWordmark } from "@/components/press-wordmark";

const examples = [
  { serial: "P-0019", domain: "are.na", fragment: "A room can teach you how to look.", accent: "#8fa79e" },
  { serial: "P-0027", domain: "example.com", fragment: "Design is paced through rhythm.", accent: "#8d99ad" },
  { serial: "P-0031", domain: "music.apple.com", fragment: "The silence is part of the song.", accent: "#b09c87" },
];

export default function HomePage() {
  return (
    <main className="product-shell home-shell">
      <header className="product-nav"><PressWordmark /><Link href="/pressings">Your pressings</Link></header>
      <section className="home-hero" aria-labelledby="press-title">
        <div className="home-hero__copy">
          <p className="eyebrow">A preservation instrument for the internet</p>
          <h1 id="press-title">Keep what made you stop.</h1>
          <p className="promise">Turn a page, post, link, or screenshot into a tiny thing you can keep.</p>
          <div className="home-actions"><Link className="primary-button" href="/press/new">Press something</Link><a className="secondary-button" href="#how-it-works">See how it works</a></div>
        </div>
        <div className="hero-objects" aria-label="Example PRESS objects">
          {examples.map((example, index) => (
            <article className={`hero-object hero-object--${index + 1}`} key={example.serial} style={{ "--example-accent": example.accent } as React.CSSProperties}>
              <span className="hero-object__glow" />
              <span className="hero-object__world" />
              <p>{example.domain}</p>
              <blockquote>{example.fragment}</blockquote>
              <strong>{example.serial}</strong>
            </article>
          ))}
        </div>
      </section>
      <section className="home-process" id="how-it-works" aria-label="How PRESS works">
        <article><span>01</span><h2>Capture</h2><p>Bring the exact source and fragment that caught you.</p></article>
        <article><span>02</span><h2>Press</h2><p>A miniature world forms inside one consistent shell.</p></article>
        <article><span>03</span><h2>Keep</h2><p>Return later without losing the source or your own words.</p></article>
      </section>
      <section className="home-manifesto">
        <p>The internet is full of things worth more than a tab.</p>
        <Link className="text-link" href="/press/new">Make one physical enough to remember</Link>
      </section>
    </main>
  );
}
