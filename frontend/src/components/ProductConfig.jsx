import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Layers, Square, Circle, Hexagon, Shield, Tag,
  ArrowUp, ArrowDown, ArrowLeft, ArrowRight, Crosshair,
  ArrowUpLeft, ArrowUpRight, ArrowDownLeft, ArrowDownRight,
  Stamp, PenTool, Scissors, Type, Palette, Sparkles,
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
  center:       Crosshair,
  top:          ArrowUp,
  bottom:       ArrowDown,
  left:         ArrowLeft,
  right:        ArrowRight,
  top_left:     ArrowUpLeft,
  top_right:    ArrowUpRight,
  bottom_left:  ArrowDownLeft,
  bottom_right: ArrowDownRight,
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

function ColorSwatch({ hex, label, selected, onClick }) {
  return (
    <motion.button
      whileHover={{ scale: 1.08 }}
      whileTap={{ scale: 0.95 }}
      onClick={onClick}
      className={`
        flex flex-col items-center gap-1.5 p-2 rounded-xl transition-all duration-200
        ${selected
          ? "ring-2 ring-bambu ring-offset-2 ring-offset-carbon-900"
          : "hover:ring-1 hover:ring-white/20 hover:ring-offset-1 hover:ring-offset-carbon-900"
        }
      `}
    >
      <div
        className="w-8 h-8 rounded-lg border border-white/20 shadow-inner"
        style={{ backgroundColor: hex }}
      />
      <span className="text-[10px] text-white/40">{label}</span>
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
      defaults[f.key] = f.default ?? f.options?.[0]?.value ?? "";
    });
    setValues(defaults);
  }, [schema]);

  const set = (key, val) => setValues((prev) => ({ ...prev, [key]: val }));

  const style = values.style || "raised";
  const isSilhouette = style === "silhouette";
  const hasText = (values.text || "").trim().length > 0;
  const hasText2 = (values.text_line2 || "").trim().length > 0;
  const hasDeco = values.decoration && values.decoration !== "none";

  const handleGenerate = () => {
    onGenerate({ product: "keychain", ...values });
  };

  if (!schema?.fields) return null;

  const field = (key) => schema.fields.find((f) => f.key === key);

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
        {field("style")?.options.map((opt) => {
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
          {field("shape")?.options.map((opt) => {
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
        {field("size")?.options.map((opt) => (
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
          {field("logo_position")?.options.map((opt) => {
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
        {field("keyhole")?.options.map((opt) => (
          <OptionCard
            key={opt.value}
            selected={values.keyhole === opt.value}
            onClick={() => set("keyhole", opt.value)}
          >
            {opt.label}
          </OptionCard>
        ))}
      </Section>

      {/* Base Color */}
      <div className="space-y-2">
        <div className="flex items-center gap-2">
          <Palette className="text-bambu" size={14} />
          <label className="text-xs font-mono uppercase tracking-wider text-white/30">
            Base Color
          </label>
        </div>
        <div className="flex flex-wrap gap-1.5">
          {field("base_color")?.options.map((opt) => (
            <ColorSwatch
              key={opt.value}
              hex={opt.hex}
              label={opt.label}
              selected={values.base_color === opt.value}
              onClick={() => set("base_color", opt.value)}
            />
          ))}
        </div>
      </div>

      {/* ---- Text Section ---- */}
      <div className="border-t border-white/10 pt-4 space-y-4">
        <div className="flex items-center gap-2">
          <Type className="text-bambu" size={16} />
          <label className="text-xs font-mono uppercase tracking-wider text-white/30">
            Custom Text (optional)
          </label>
        </div>

        <input
          type="text"
          maxLength={30}
          placeholder="e.g. your name, team, etc."
          value={values.text || ""}
          onChange={(e) => set("text", e.target.value)}
          className="w-full px-4 py-2.5 rounded-xl bg-white/5 border border-white/10
                     text-white placeholder-white/20 text-sm
                     focus:outline-none focus:border-bambu/50 focus:ring-1 focus:ring-bambu/30
                     transition-all duration-200"
        />

        <AnimatePresence>
          {hasText && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              className="space-y-4"
            >
              {/* Font */}
              <Section label="Font">
                {field("font")?.options.map((opt) => (
                  <OptionCard
                    key={opt.value}
                    selected={values.font === opt.value}
                    onClick={() => set("font", opt.value)}
                  >
                    {opt.label}
                  </OptionCard>
                ))}
              </Section>

              {/* Text Position */}
              <Section label="Text Position">
                {field("text_position")?.options.map((opt) => (
                  <OptionCard
                    key={opt.value}
                    selected={values.text_position === opt.value}
                    onClick={() => set("text_position", opt.value)}
                  >
                    {opt.label}
                  </OptionCard>
                ))}
              </Section>

              {/* Text Color */}
              <Section label="Text Color">
                {field("text_color")?.options.map((opt) => (
                  <OptionCard
                    key={opt.value}
                    selected={values.text_color === opt.value}
                    onClick={() => set("text_color", opt.value)}
                  >
                    {opt.label}
                  </OptionCard>
                ))}
              </Section>

              {/* Line 2 */}
              <div className="space-y-3 pt-2 border-t border-white/5">
                <label className="text-xs font-mono uppercase tracking-wider text-white/20">
                  Second Line (optional)
                </label>
                <input
                  type="text"
                  maxLength={20}
                  placeholder="e.g. jersey number"
                  value={values.text_line2 || ""}
                  onChange={(e) => set("text_line2", e.target.value)}
                  className="w-full px-4 py-2.5 rounded-xl bg-white/5 border border-white/10
                             text-white placeholder-white/20 text-sm
                             focus:outline-none focus:border-bambu/50 focus:ring-1 focus:ring-bambu/30
                             transition-all duration-200"
                />

                <AnimatePresence>
                  {hasText2 && (
                    <motion.div
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: "auto" }}
                      exit={{ opacity: 0, height: 0 }}
                    >
                      <Section label="Line 2 Font">
                        {field("font_line2")?.options.map((opt) => (
                          <OptionCard
                            key={opt.value}
                            selected={values.font_line2 === opt.value}
                            onClick={() => set("font_line2", opt.value)}
                          >
                            {opt.label}
                          </OptionCard>
                        ))}
                      </Section>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* ---- Decoration Section ---- */}
      <div className="border-t border-white/10 pt-4 space-y-4">
        <div className="flex items-center gap-2">
          <Sparkles className="text-bambu" size={16} />
          <label className="text-xs font-mono uppercase tracking-wider text-white/30">
            Decoration (optional)
          </label>
        </div>

        <Section label="Add an Item">
          {field("decoration")?.options.map((opt) => (
            <OptionCard
              key={opt.value}
              selected={values.decoration === opt.value}
              onClick={() => set("decoration", opt.value)}
            >
              {opt.label}
            </OptionCard>
          ))}
        </Section>

        <AnimatePresence>
          {hasDeco && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              className="space-y-4"
            >
              <Section label="Decoration Position">
                {field("decoration_position")?.options.map((opt) => (
                  <OptionCard
                    key={opt.value}
                    selected={values.decoration_position === opt.value}
                    onClick={() => set("decoration_position", opt.value)}
                  >
                    {opt.label}
                  </OptionCard>
                ))}
              </Section>

              <Section label="Decoration Color">
                {field("decoration_color")?.options.map((opt) => (
                  <OptionCard
                    key={opt.value}
                    selected={values.decoration_color === opt.value}
                    onClick={() => set("decoration_color", opt.value)}
                  >
                    {opt.label}
                  </OptionCard>
                ))}
              </Section>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

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
