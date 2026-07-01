import { NextResponse } from "next/server";
import { getThreatStore } from "@/lib/store";

export const dynamic = "force-dynamic";

export async function GET() {
  const status = getThreatStore().getStatus();
  return NextResponse.json({ ok: true, ...status });
}
