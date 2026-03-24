import { motion } from "framer-motion";
import { Download, FileBox, FileImage, FileCode, Palette } from "lucide-react";

function DLButton({ href, label, icon: Icon, primary }) {
  return (
    <motion.a
      href={href}
      download
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ scale: 1.03 }}
      whileTap={{ scale: 0.97 }}
      className={`
        inline-flex items-center gap-2.5 px-6 py-3 rounded-xl font-semibold text-sm
        transition-all duration-200 select-none
        ${
          primary
            ? "bg-bambu text-carbon-900 shadow-glow hover:shadow-glow"
            : "glass-bright text-white/80 hover:text-white hover:border-white/20"
        }
      `}
    >
      <Icon size={18} />
      {label}
      <Download size={14} className="opacity-60" />
    </motion.a>
  );
}

export default function DownloadSection({ jobId }) {
  if (!jobId) return null;

  const base = `/api/files/${jobId}`;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: "easeOut" }}
      className="flex flex-col items-center gap-5"
    >
      <div className="flex items-center gap-2 mb-1">
        <div className="h-px w-8 bg-bambu/30" />
        <span className="text-bambu/70 text-xs font-mono uppercase tracking-widest">
          Ready
        </span>
        <div className="h-px w-8 bg-bambu/30" />
      </div>

      <div className="flex flex-wrap justify-center gap-3">
        <DLButton
          href={`${base}/logo.stl`}
          label="Download STL"
          icon={FileBox}
          primary
        />
        <DLButton
          href={`${base}/logo.3mf`}
          label="3MF Multi-Color"
          icon={Palette}
        />
        <DLButton
          href={`${base}/logo.svg`}
          label="Download SVG"
          icon={FileCode}
        />
        <DLButton
          href={`${base}/transparent.png`}
          label="Transparent PNG"
          icon={FileImage}
        />
      </div>

      <p className="text-white/20 text-xs font-mono mt-2">
        STL: single body &bull; 3MF: multi-color for AMS &bull;
        Keychain ready for Bambu Lab
      </p>
    </motion.div>
  );
}
