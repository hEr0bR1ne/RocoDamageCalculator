import { mkdir, copyFile } from "node:fs/promises";
import path from "node:path";

const root = process.cwd();
const source = path.resolve(root, "..", "data", "精灵完整数据.json");
const targetDir = path.resolve(root, "public", "data");
const target = path.resolve(targetDir, "精灵完整数据.json");

async function main() {
  await mkdir(targetDir, { recursive: true });
  await copyFile(source, target);
  console.log(`[sync:data] copied ${source} -> ${target}`);
}

main().catch((err) => {
  console.error("[sync:data] failed:", err);
  process.exit(1);
});
