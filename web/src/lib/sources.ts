export const PUBLIC_TELEGRAM_SOURCES = [
  "monitor_ukr",
  "cxidua",
  "war_monitor",
  "sashakots",
  "DeepStateUA",
  "UKR7",
];

export const CONFIG = {
  pollSeconds: Number(process.env.INGEST_POLL_SECONDS ?? 5),
  bootstrapLimit: Number(process.env.INGEST_BOOTSTRAP_LIMIT ?? 20),
  historyHours: 2,
};
