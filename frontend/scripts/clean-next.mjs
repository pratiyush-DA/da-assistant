import { appendFileSync, existsSync, lstatSync, rmSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(fileURLToPath(new URL(".", import.meta.url)), "..");
const nextDir = join(root, ".next");
const logPath = join(root, "..", "debug-8f6aae.log");

function debugLog(message, data, hypothesisId) {
  // #region agent log
  try {
    appendFileSync(
      logPath,
      `${JSON.stringify({
        sessionId: "8f6aae",
        hypothesisId,
        location: "clean-next.mjs",
        message,
        data,
        timestamp: Date.now(),
        runId: process.env.DEBUG_RUN_ID || "clean",
      })}\n`,
    );
  } catch {
    /* ignore */
  }
  // #endregion
}

function inspectPackageJson() {
  const pkg = join(nextDir, "package.json");
  if (!existsSync(pkg)) return { exists: false };
  try {
    const st = lstatSync(pkg);
    return {
      exists: true,
      isSymbolicLink: st.isSymbolicLink(),
      mode: st.mode,
      size: st.size,
    };
  } catch (err) {
    return { exists: true, statError: String(err) };
  }
}

function removeNextDir() {
  if (!existsSync(nextDir)) {
    debugLog("No .next directory", { nextDir }, "H2");
    return true;
  }

  const before = inspectPackageJson();
  debugLog("Before rm .next", { nextDir, packageJson: before }, "H1");

  try {
    rmSync(nextDir, { recursive: true, force: true, maxRetries: 5, retryDelay: 200 });
    debugLog("Removed .next via rmSync", { nextDir }, "H3");
    return true;
  } catch (err) {
    debugLog("rmSync failed", { error: String(err) }, "H3");
    throw err;
  }
}

try {
  removeNextDir();
  console.log("Removed .next build cache");
} catch (err) {
  console.error("Failed to remove .next:", err.message);
  console.error("Close the dev server, then run: npm run clean");
  process.exit(1);
}
