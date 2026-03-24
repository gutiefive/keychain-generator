import { useCallback, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Upload, Image, X } from "lucide-react";

const ACCEPTED = ["image/png", "image/jpeg", "image/jpg", "image/webp"];

export default function DropZone({ onFile, disabled }) {
  const [dragOver, setDragOver] = useState(false);
  const [preview, setPreview] = useState(null);
  const [fileName, setFileName] = useState("");

  const handleFile = useCallback(
    (file) => {
      if (!file || disabled) return;
      if (!ACCEPTED.includes(file.type)) {
        alert("Please drop a PNG, JPG, or WebP image.");
        return;
      }
      setFileName(file.name);
      const reader = new FileReader();
      reader.onload = (e) => setPreview(e.target.result);
      reader.readAsDataURL(file);
      onFile(file);
    },
    [onFile, disabled]
  );

  const onDrop = useCallback(
    (e) => {
      e.preventDefault();
      setDragOver(false);
      const file = e.dataTransfer.files[0];
      handleFile(file);
    },
    [handleFile]
  );

  const onDragOver = (e) => {
    e.preventDefault();
    if (!disabled) setDragOver(true);
  };

  const clear = (e) => {
    e.stopPropagation();
    setPreview(null);
    setFileName("");
  };

  return (
    <motion.div
      onDrop={onDrop}
      onDragOver={onDragOver}
      onDragLeave={() => setDragOver(false)}
      onClick={() => {
        if (disabled || preview) return;
        const input = document.createElement("input");
        input.type = "file";
        input.accept = ACCEPTED.join(",");
        input.onchange = (e) => handleFile(e.target.files[0]);
        input.click();
      }}
      className={`
        relative w-full rounded-2xl p-8 transition-all duration-300 cursor-pointer
        min-h-[260px] flex flex-col items-center justify-center gap-4
        ${disabled ? "opacity-60 cursor-not-allowed" : ""}
        ${dragOver ? "glow-border-active scale-[1.01]" : "glow-border"}
        ${preview ? "glass-bright" : "glass"}
      `}
      whileHover={!disabled && !preview ? { scale: 1.005 } : {}}
      whileTap={!disabled && !preview ? { scale: 0.995 } : {}}
    >
      <AnimatePresence mode="wait">
        {preview ? (
          <motion.div
            key="preview"
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.9 }}
            className="flex flex-col items-center gap-4"
          >
            <div className="relative">
              <img
                src={preview}
                alt="Preview"
                className="max-h-40 max-w-full rounded-lg border border-white/10 shadow-lg"
              />
              {!disabled && (
                <button
                  onClick={clear}
                  className="absolute -top-2 -right-2 bg-carbon-600 hover:bg-red-500/80
                             rounded-full p-1 transition-colors border border-white/10"
                >
                  <X size={14} />
                </button>
              )}
            </div>
            <p className="text-sm text-white/50 font-mono truncate max-w-[240px]">
              {fileName}
            </p>
          </motion.div>
        ) : (
          <motion.div
            key="empty"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="flex flex-col items-center gap-4"
          >
            <motion.div
              animate={dragOver ? { scale: 1.15, rotate: 5 } : { scale: 1, rotate: 0 }}
              transition={{ type: "spring", stiffness: 300 }}
              className="w-16 h-16 rounded-2xl glass-bright flex items-center justify-center"
            >
              {dragOver ? (
                <Image className="text-bambu" size={28} />
              ) : (
                <Upload className="text-bambu/70" size={28} />
              )}
            </motion.div>

            <div className="text-center">
              <p className="text-white/80 font-medium text-lg">
                {dragOver ? "Drop it!" : "Drop your logo here"}
              </p>
              <p className="text-white/30 text-sm mt-1">
                PNG, JPG, or WebP &bull; Max 20 MB
              </p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
