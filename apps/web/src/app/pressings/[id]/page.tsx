import Link from "next/link";
import { notFound } from "next/navigation";

import { getPressing } from "@/lib/pressings";

import { PressingDetail } from "./pressing-detail";

export const dynamic = "force-dynamic";

async function loadPressing(id: string) {
  try {
    return await getPressing(id);
  } catch {
    notFound();
  }
}

export default async function PressingDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const response = await loadPressing(id);

  if (response.pressing.status === "deleted") notFound();

  return (
    <main className="product-shell">
      <header className="product-nav"><Link href="/">PRESS</Link><Link href="/pressings">Your pressings</Link></header>
      <PressingDetail response={response} />
    </main>
  );
}
