// Starts WORKERS copies of the server. They share port 3000 via SO_REUSEPORT,
// so the Linux kernel spreads connections between them (like uvicorn --workers).
const workers = Number(process.env.WORKERS ?? 1);
const children = Array.from({ length: workers }, () =>
  Bun.spawn(["bun", "src/index.ts"], { stdio: ["inherit", "inherit", "inherit"], env: process.env }),
);

for (const signal of ["SIGTERM", "SIGINT"] as const) {
  process.on(signal, () => {
    for (const child of children) child.kill(signal);
    process.exit(0);
  });
}

await Promise.all(children.map((child) => child.exited));
