const { spawnSync } = require("child_process");

const candidates = process.platform === "win32"
  ? [["py", ["-3"]], ["python", []], ["python3", []]]
  : [["python3", []], ["python", []]];

for (const [command, prefixArgs] of candidates) {
  const result = spawnSync(command, [...prefixArgs, "scripts/start.py"], {
    cwd: process.cwd(),
    stdio: "inherit",
    shell: false,
  });

  if (result.error && result.error.code === "ENOENT") {
    continue;
  }

  process.exit(result.status ?? 1);
}

console.error("No se encontro Python 3.10+. Instala Python y vuelve a ejecutar npm start.");
process.exit(1);
