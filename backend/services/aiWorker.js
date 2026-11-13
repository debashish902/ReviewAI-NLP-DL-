const { spawn } = require("child_process");
const path = require("path");
const readline = require("readline");
const crypto = require("crypto");

const AI_ENGINE_DIR = path.resolve(
    __dirname,
    "../../ai-engine"
);

const WORKER_PATH = path.join(
    AI_ENGINE_DIR,
    "inference",
    "ai_worker.py"
);

const PYTHON_COMMAND = process.env.PYTHON_COMMAND || "python";

let workerProcess = null;
let workerReady = false;

const pendingRequests = new Map();

let stdoutBuffer = "";
let startupPromise = null;

const STARTUP_TIMEOUT = 120000;
const REQUEST_TIMEOUT = 120000;


// ============================================================
// START PYTHON AI WORKER
// ============================================================

function startWorker() {
    if (workerProcess && !workerProcess.killed) {
        if (workerReady) {
            return Promise.resolve();
        }

        if (startupPromise) {
            return startupPromise;
        }
    }

    startupPromise = new Promise((resolve, reject) => {
        console.log("[AI] Starting Python worker...");

        workerReady = false;
        stdoutBuffer = "";

        const child = spawn(
            PYTHON_COMMAND,
            ["-u", WORKER_PATH],
            {
                cwd: AI_ENGINE_DIR,
                stdio: ["pipe", "pipe", "pipe"],
                windowsHide: true
            }
        );

        workerProcess = child;

        let startupTimer;

        const cleanupStartup = () => {
            if (startupTimer) {
                clearTimeout(startupTimer);
            }
        };

        startupTimer = setTimeout(() => {
            cleanupStartup();

            reject(
                new Error("Python AI worker startup timed out.")
            );

            child.kill();
        }, STARTUP_TIMEOUT);

        // ----------------------------------------------------
        // Standard output: JSON responses only
        // ----------------------------------------------------

        child.stdout.on("data", (chunk) => {
            stdoutBuffer += chunk.toString();

            const lines = stdoutBuffer.split(/\r?\n/);

            stdoutBuffer = lines.pop() || "";

            for (const line of lines) {
                const trimmedLine = line.trim();

                if (!trimmedLine) {
                    continue;
                }

                let response;

                try {
                    response = JSON.parse(trimmedLine);
                } catch (error) {
                    console.error(
                        "[AI] Invalid JSON received from worker:",
                        trimmedLine
                    );

                    continue;
                }

                const requestId = response.id;

                // Startup readiness is indicated through stderr,
                // not stdout. JSON stdout is reserved for requests.
                if (!requestId) {
                    continue;
                }

                const pending = pendingRequests.get(requestId);

                if (!pending) {
                    continue;
                }

                clearTimeout(pending.timeout);

                pendingRequests.delete(requestId);

                if (response.success) {
                    pending.resolve(response.data);
                } else {
                    pending.reject(
                        new Error(
                            response.error || "AI analysis failed."
                        )
                    );
                }
            }
        });

        // ----------------------------------------------------
        // Standard error: startup logs and diagnostics
        // ----------------------------------------------------

        const stderrReader = readline.createInterface({
            input: child.stderr
        });

        stderrReader.on("line", (line) => {
            console.log(`[Python AI] ${line}`);

            if (line.includes("AI worker is ready.")) {
                cleanupStartup();

                workerReady = true;

                console.log("[AI] Python worker is ready.");

                resolve();
            }
        });

        // ----------------------------------------------------
        // Process errors
        // ----------------------------------------------------

        child.on("error", (error) => {
            cleanupStartup();

            workerReady = false;

            if (workerProcess === child) {
                workerProcess = null;
            }

            reject(error);

            rejectPendingRequests(
                "Unable to start Python AI worker."
            );
        });

        child.on("exit", (code, signal) => {
            cleanupStartup();

            if (workerProcess === child) {
                workerProcess = null;
                workerReady = false;
            }

            console.log(
                `[AI] Python worker exited. Code=${code}, Signal=${signal}`
            );

            rejectPendingRequests(
                "Python AI worker stopped unexpectedly."
            );
        });
    });

    startupPromise = startupPromise.finally(() => {
        startupPromise = null;
    });

    return startupPromise;
}


// ============================================================
// REJECT PENDING REQUESTS
// ============================================================

function rejectPendingRequests(message) {
    for (const [requestId, pending] of pendingRequests.entries()) {
        clearTimeout(pending.timeout);

        pending.reject(new Error(message));

        pendingRequests.delete(requestId);
    }
}


// ============================================================
// ANALYZE A REVIEW
// ============================================================

async function analyzeReview(review) {
    if (typeof review !== "string" || !review.trim()) {
        throw new Error("Review text is required.");
    }

    if (review.length > 10000) {
        throw new Error(
            "Review cannot exceed 10000 characters."
        );
    }

    await startWorker();

    if (
        !workerProcess ||
        workerProcess.killed ||
        !workerReady
    ) {
        throw new Error("Python AI worker is not ready.");
    }

    const requestId = crypto.randomUUID();

    return new Promise((resolve, reject) => {
        const timeout = setTimeout(() => {
            pendingRequests.delete(requestId);

            reject(
                new Error("AI review analysis timed out.")
            );
        }, REQUEST_TIMEOUT);

        pendingRequests.set(requestId, {
            resolve,
            reject,
            timeout
        });

        const request = JSON.stringify({
            id: requestId,
            review
        });

        workerProcess.stdin.write(
            request + "\n",
            (error) => {
                if (error) {
                    clearTimeout(timeout);

                    pendingRequests.delete(requestId);

                    reject(error);
                }
            }
        );
    });
}


// ============================================================
// SHUTDOWN
// ============================================================

function stopWorker() {
    if (workerProcess && !workerProcess.killed) {
        workerProcess.kill();
    }

    workerProcess = null;
    workerReady = false;

    rejectPendingRequests(
        "AI worker is shutting down."
    );
}

process.once("SIGINT", stopWorker);
process.once("SIGTERM", stopWorker);


// ============================================================
// EXPORT SERVICE
// ============================================================

module.exports = {
    startWorker,
    analyzeReview,
    stopWorker
};