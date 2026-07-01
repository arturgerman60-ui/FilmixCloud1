export async function register() {
  if (process.env.NEXT_RUNTIME === "nodejs") {
    const { getThreatStore } = await import("./lib/store");
    getThreatStore();
  }
}
