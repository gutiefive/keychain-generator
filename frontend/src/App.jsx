import { useState, useCallback, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Layers, Github, RotateCcw, KeyRound } from "lucide-react";
import DropZone from "./components/DropZone";
import ProgressStepper from "./components/ProgressStepper";
import DownloadSection from "./components/DownloadButton";
import ProductConfig from "./components/ProductConfig";

export default function App() {
  const [step, setStep] = useState(null);
  const [jobId, setJobId] = useState(null);
  const [error, setError] = useState(null);
  const [done, setDone] = useState(false);
  const [previewSrc, setPreviewSrc] = useState(null);
  const [configuring, setConfiguring] = useState(false);
  const [productSchema, setProductSchema] = useState(null);

  useEffect(() => {
    fetch("/api/product-config")
      .then((r) => r.json())
      .then((data) => {
        if (data.keychain) {
          setProductSchema(data.keychain.config);
        }
      })
      .catch(() => {});
  }, []);

  const reset = () => {
    setStep(null);
    setJobId(null);
    setError(null);
    setDone(false);
    setPreviewSrc(null);
    setConfiguring(false);
  };

  const safeError = async (res, fallback) => {
    try {
      const body = await res.json();
      return body.detail || fallback;
    } catch {
      return `${fallback} (HTTP ${res.status})`;
    }
  };

  const runPipeline = useCallback(async (file) => {
    setError(null);
    setDone(false);
    setPreviewSrc(null);
    setConfiguring(false);

    try {
      // Step 1 — Upload
      setStep("upload");
      const form = new FormData();
      form.append("file", file);

      const uploadRes = await fetch("/api/upload", { method: "POST", body: form });
      if (!uploadRes.ok) throw new Error(await safeError(uploadRes, "Upload failed"));
      const { job_id } = await uploadRes.json();
      setJobId(job_id);

      // Step 2 — Remove Background
      setStep("remove_bg");
      const bgRes = await fetch(`/api/remove-bg/${job_id}`, { method: "POST" });
      if (!bgRes.ok) throw new Error(await safeError(bgRes, "Background removal failed"));

      setPreviewSrc(`/api/files/${job_id}/transparent.png`);

      // Step 3 — Vectorize
      setStep("vectorize");
      const vecRes = await fetch(`/api/vectorize/${job_id}`, { method: "POST" });
      if (!vecRes.ok) throw new Error(await safeError(vecRes, "Vectorization failed"));

      // Step 4 — Show config UI (pause pipeline here)
      setStep("configure");
      setConfiguring(true);
    } catch (err) {
      console.error(err);
      setError(err.message);
    }
  }, []);

  const handleGenerate = useCallback(
    async (config) => {
      setConfiguring(false);
      setError(null);

      try {
        setStep("extrude");
        const stlRes = await fetch(`/api/generate-stl/${jobId}`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(config),
        });
        if (!stlRes.ok) throw new Error(await safeError(stlRes, "Generation failed"));

        setDone(true);
      } catch (err) {
        console.error(err);
        setError(err.message);
      }
    },
    [jobId]
  );

  const processing = step !== null && !done && !error && !configuring;

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="w-full border-b border-white/5">
        <div className="max-w-4xl mx-auto flex items-center justify-between px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-bambu/10 border border-bambu/30 flex items-center justify-center">
              <KeyRound className="text-bambu" size={18} />
            </div>
            <div>
              <h1 className="text-lg font-bold tracking-tight">
                Keychain<span className="text-bambu">Gen</span>
              </h1>
              <p className="text-[10px] text-white/30 font-mono uppercase tracking-wider -mt-0.5">
                Logo &rarr; Keychain
              </p>
            </div>
          </div>
          <a
            href="https://github.com"
            target="_blank"
            rel="noopener noreferrer"
            className="text-white/20 hover:text-white/50 transition-colors"
          >
            <Github size={20} />
          </a>
        </div>
      </header>

      {/* Main */}
      <main className="flex-1 flex items-start justify-center px-4 py-12">
        <div className="w-full max-w-xl flex flex-col gap-8">
          {/* Title block */}
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-center"
          >
            <h2 className="text-3xl sm:text-4xl font-extrabold tracking-tight">
              Turn any logo into a
              <br />
              <span className="text-bambu text-glow">custom keychain</span>
            </h2>
            <p className="text-white/35 mt-3 text-sm max-w-md mx-auto leading-relaxed">
              Drop a PNG or JPG. Choose your shape, style, and size.
              Get a 3D-printable STL and multi-color 3MF for Bambu Lab.
            </p>
          </motion.div>

          {/* Drop zone */}
          <DropZone onFile={runPipeline} disabled={processing || configuring} />

          {/* Progress Stepper */}
          <AnimatePresence>
            {step && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0 }}
                className="overflow-hidden"
              >
                <div className="glass rounded-2xl p-6">
                  <ProgressStepper
                    activeStep={done ? "complete" : step}
                    error={error}
                  />

                  {/* Intermediate preview */}
                  <AnimatePresence>
                    {previewSrc && (
                      <motion.div
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="mt-5 flex justify-center"
                      >
                        <div className="relative">
                          <div
                            className="absolute inset-0 rounded-lg"
                            style={{
                              background:
                                "repeating-conic-gradient(#1a1a1a 0% 25%, #242424 0% 50%) 0 0 / 16px 16px",
                            }}
                          />
                          <img
                            src={previewSrc}
                            alt="Transparent preview"
                            className="relative max-h-36 rounded-lg border border-white/10"
                          />
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>

                  {/* Error message */}
                  {error && (
                    <motion.p
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      className="mt-4 text-red-400 text-sm text-center font-mono"
                    >
                      {error}
                    </motion.p>
                  )}
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Product Configuration */}
          <AnimatePresence>
            {configuring && productSchema && (
              <ProductConfig
                config={productSchema}
                onGenerate={handleGenerate}
              />
            )}
          </AnimatePresence>

          {/* Downloads */}
          <AnimatePresence>
            {done && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
              >
                <DownloadSection jobId={jobId} />
              </motion.div>
            )}
          </AnimatePresence>

          {/* Reset */}
          {(done || error) && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex justify-center"
            >
              <button
                onClick={reset}
                className="flex items-center gap-2 text-white/30 hover:text-white/60
                           text-sm transition-colors font-medium"
              >
                <RotateCcw size={14} />
                Start over
              </button>
            </motion.div>
          )}
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-white/5 py-5">
        <p className="text-center text-white/15 text-xs font-mono">
          KeychainGen &bull; rembg + scikit-image + numpy-stl &bull; Built for Bambu Lab
        </p>
      </footer>
    </div>
  );
}
