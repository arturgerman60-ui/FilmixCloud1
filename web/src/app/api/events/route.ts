import { NextResponse } from "next/server";
import { getThreatStore } from "@/lib/store";

export const dynamic = "force-dynamic";

export async function GET() {
  const snapshot = getThreatStore().getSnapshot();
  return NextResponse.json(snapshot);
}
