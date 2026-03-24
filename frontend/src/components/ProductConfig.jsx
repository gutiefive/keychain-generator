import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Layers, Square, Circle, Hexagon, Shield, Tag,
  ArrowUp, ArrowDown, ArrowLeft, ArrowRight, Crosshair,
  Stamp, PenTool, Scissors,
} from "lucide-react";

const STYLE_META = {
  raised:     { icon: Stamp,    desc: "Logo sits on top of the base" },
  embedded:   { icon: PenTool,  desc: "Logo engraved into the surface" },
  silhouette: { icon: Scissors, desc: "Logo shape IS the keychain" },
};

const SHAPE_ICONS = {
  rectangle: Square,
  circle:    Circle,
  oval:      Hexagon,
  dog_tag:   Tag,
  shield:    Shield,
};

const POSITION_ICONS = {
  center: Crosshair,
  top:    ArrowUp,
  bottom: ArrowDown,
  left:   ArrowLeft,
  right:  ArrowRight,
};

const KEYHOLE_LABELS = {
  round_hole: "Round Hole",
  tab_loop:   "Tab Loop",
  none:       "No Hole",
};

function OptionCard({ selected, onClick, children, className = "" }) {
  return (
    <motion.button
      whileHover={{ scale: 1.03 }}
      whileTap={{ scale: 0.97 }}
      onClick={onClick}
      className={`
        px-4 py-3 rounded-xl text-sm font-medium transition-all duration-200
        ${selected
          ? "bg-bambu/15 border-bambu/50 text-bambu border-2"
          : "glass border border-white/10 text-white/60 hover:text-white/80 hover:border-white/20"
        }
        ${className}
      `}
    >
      {children}
    </motion.button>
  );
}

function Section({ label, children, visible = true }) {
  if (!visible) return null;
  return (
    <motion.div
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: "auto" }}
      exit={{ opacity: 0, height: 0 }}
      className="space-y-2"
    >
      <label className="text-xs font-mono uppercase tracking-wider text-white/30">
        {label}
      </label>
      <div className="flex flex-wrap gap-2">{children}</div>
    </motion.div>
  );
}

export default function ProductConfig({ config: schema, onGenerate }) {
  const [values, setValues] = useState({});

  useEffect(() => {
    if (!schema?.fields) return;
    const defaults = {};
    schema.fields.forEach((f) => {
      defaults[f.key] = f.default || f.options?.[0]?.value;
    });
    setValues(defaults);
  }, [schema]);

  const set = (key, val) => setValues((prev) => ({ ...prev, [key]: val }));

  const isHidden = (field) => {
    if (!field.hide_if) return false;
    return values[field.hide_if.field] === field.hide_if.value;
  };

  const style = values.style || "raised";
  const isSilhouette = style === "silhouette";

  const handleGenerate = () => {
    onGenerate({ product: "keychain", ...values });
  };

  if (!schema?.fields) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="glass rounded-2xl p-6 space-y-5"
    >
      <div className="flex items-center gap-2 mb-1">
        <Layers className="text-bambu" size={16} />
        <h3 className="text-sm font-bold text-white/80 uppercase tracking-wider">
          Customize Your Keychain
        </h3>
      </div>

      {/* Style */}
      <Section label="Logo Style">
        {schema.fields
          .find((f) => f.key === "style")
          ?.options.map((opt) => {
            const meta = STYLE_META[opt.value] || {};
            const Icon = meta.icon || Layers;
            return (
              <OptionCard
                key={opt.value}
                selected={style === opt.value}
                onClick={() => set("style", opt.value)}
                className="flex flex-col items-center gap-1 min-w-[100px]"
              >
                <Icon size={18} />
                <span>{opt.label}</span>
                {meta.desc && (
                  <span className="text-[10px] text-white/30 font-normal">
                    {meta.desc}
                  </span>
                )}
              </OptionCard>
            );
          })}
      </Section>

      {/* Shape */}
      <AnimatePresence>
        <Section label="Base Shape" visible={!isSilhouette}>
          {schema.fields
            .find((f) => f.key === "shape")
            ?.options.map((opt) => {
              const Icon = SHAPE_ICONS[opt.value] || Square;
              return (
                <OptionCard
                  key={opt.value}
                  selected={values.shape === opt.value}
                  onClick={() => set("shape", opt.value)}
                  className="flex items-center gap-2"
                >
                  <Icon size={16} />
                  {opt.label}
                </OptionCard>
              );
            })}
        </Section>
      </AnimatePresence>

      {/* Size */}
      <Section label="Size">
        {schema.fields
          .find((f) => f.key === "size")
          ?.options.map((opt) => (
            <OptionCard
              key={opt.value}
              selected={values.size === opt.value}
              onClick={() => set("size", opt.value)}
            >
              {opt.label}
            </OptionCard>
          ))}
      </Section>

      {/* Logo Position */}
      <AnimatePresence>
        <Section label="Logo Position" visible={!isSilhouette}>
          {schema.fields
            .find((f) => f.key === "logo_position")
            ?.options.map((opt) => {
              const Icon = POSITION_ICONS[opt.value] || Crosshair;
              return (
                <OptionCard
                  key={opt.value}
                  selected={values.logo_position === opt.value}
                  onClick={() => set("logo_position", opt.value)}
                  className="flex items-center gap-2"
                >
                  <Icon size={14} />
                  {opt.label}
                </OptionCard>
              );
            })}
        </Section>
      </AnimatePresence>

      {/* Keyhole */}
      <Section label="Key Ring Hole">
        {schema.fields
          .find((f) => f.key === "keyhole")
          ?.options.map((opt) => (
            <OptionCard
              key={opt.value}
              selected={values.keyhole === opt.value}
              onClick={() => set("keyhole", opt.value)}
            >
              {opt.label}
            </OptionCard>
          ))}
      </Section>

      {/* Generate Button */}
      <motion.button
        whileHover={{ scale: 1.02 }}
        whileTap={{ scale: 0.98 }}
        onClick={handleGenerate}
        className="w-full mt-4 py-3 rounded-xl bg-bambu text-carbon-900 font-bold text-sm
                   shadow-glow hover:shadow-glow transition-all duration-200"
      >
        Generate Keychain
      </motion.button>
    </motion.div>
  );
}
