import { motion } from "framer-motion";
import { Check, Loader2, ImageMinus, Spline, Box, Upload, Settings } from "lucide-react";

const STEPS = [
  { id: "upload",    label: "Upload",       icon: Upload },
  { id: "remove_bg", label: "Removing BG",  icon: ImageMinus },
  { id: "vectorize", label: "Tracing SVG",  icon: Spline },
  { id: "configure", label: "Configure",    icon: Settings },
  { id: "extrude",   label: "Generating",   icon: Box },
];

const STATUS = {
  pending: "pending",
  active: "active",
  done: "done",
  error: "error",
};

function stepStatus(stepIdx, activeIdx, error) {
  if (error && stepIdx === activeIdx) return STATUS.error;
  if (stepIdx < activeIdx) return STATUS.done;
  if (stepIdx === activeIdx) return STATUS.active;
  return STATUS.pending;
}

export default function ProgressStepper({ activeStep, error }) {
  const activeIdx = STEPS.findIndex((s) => s.id === activeStep);

  return (
    <div className="w-full">
      {/* Desktop horizontal stepper */}
      <div className="hidden sm:flex items-center justify-between gap-2">
        {STEPS.map((step, i) => {
          const status = stepStatus(i, activeIdx, error);
          const Icon = step.icon;
          return (
            <div key={step.id} className="flex items-center flex-1 last:flex-none">
              <div className="flex flex-col items-center gap-2 min-w-[70px]">
                <motion.div
                  animate={
                    status === STATUS.active
                      ? { boxShadow: ["0 0 10px rgba(0,255,65,0.3)", "0 0 25px rgba(0,255,65,0.5)", "0 0 10px rgba(0,255,65,0.3)"] }
                      : {}
                  }
                  transition={status === STATUS.active ? { repeat: Infinity, duration: 1.5 } : {}}
                  className={`
                    w-10 h-10 rounded-xl flex items-center justify-center transition-all duration-500
                    ${status === STATUS.done ? "bg-bambu/20 border border-bambu/40" : ""}
                    ${status === STATUS.active ? "bg-bambu/10 border border-bambu/60" : ""}
                    ${status === STATUS.pending ? "glass border border-white/5" : ""}
                    ${status === STATUS.error ? "bg-red-500/20 border border-red-500/40" : ""}
                  `}
                >
                  {status === STATUS.done ? (
                    <motion.div initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ type: "spring" }}>
                      <Check className="text-bambu" size={18} />
                    </motion.div>
                  ) : status === STATUS.active ? (
                    <Loader2 className="text-bambu animate-spin" size={18} />
                  ) : status === STATUS.error ? (
                    <span className="text-red-400 text-lg font-bold">!</span>
                  ) : (
                    <Icon className="text-white/25" size={16} />
                  )}
                </motion.div>
                <span
                  className={`text-[11px] font-medium transition-colors duration-300
                    ${status === STATUS.done ? "text-bambu/80" : ""}
                    ${status === STATUS.active ? "text-bambu text-glow" : ""}
                    ${status === STATUS.pending ? "text-white/25" : ""}
                    ${status === STATUS.error ? "text-red-400" : ""}
                  `}
                >
                  {step.label}
                </span>
              </div>
              {i < STEPS.length - 1 && (
                <div className="flex-1 h-px mx-1 mt-[-20px]">
                  <div className="relative h-px w-full bg-white/5 rounded-full overflow-hidden">
                    <motion.div
                      initial={{ width: "0%" }}
                      animate={{ width: i < activeIdx ? "100%" : "0%" }}
                      transition={{ duration: 0.6, ease: "easeOut" }}
                      className="absolute inset-y-0 left-0 bg-bambu/50 rounded-full"
                    />
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Mobile vertical stepper */}
      <div className="sm:hidden flex flex-col gap-3">
        {STEPS.map((step, i) => {
          const status = stepStatus(i, activeIdx, error);
          const Icon = step.icon;
          return (
            <div key={step.id} className="flex items-center gap-3">
              <div
                className={`
                  w-9 h-9 rounded-lg flex items-center justify-center shrink-0
                  ${status === STATUS.done ? "bg-bambu/20 border border-bambu/40" : ""}
                  ${status === STATUS.active ? "bg-bambu/10 border border-bambu/60 animate-pulse-glow" : ""}
                  ${status === STATUS.pending ? "glass border border-white/5" : ""}
                  ${status === STATUS.error ? "bg-red-500/20 border border-red-500/40" : ""}
                `}
              >
                {status === STATUS.done ? (
                  <Check className="text-bambu" size={16} />
                ) : status === STATUS.active ? (
                  <Loader2 className="text-bambu animate-spin" size={16} />
                ) : (
                  <Icon className="text-white/25" size={16} />
                )}
              </div>
              <span
                className={`text-sm font-medium
                  ${status === STATUS.done ? "text-bambu/80" : ""}
                  ${status === STATUS.active ? "text-bambu" : ""}
                  ${status === STATUS.pending ? "text-white/25" : ""}
                  ${status === STATUS.error ? "text-red-400" : ""}
                `}
              >
                {step.label}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
