import React from "react";
import { X, Sliders, Palette, PenTool, Link2, Puzzle, ChevronDown, Info } from "lucide-react";
import { motion, AnimatePresence } from "motion/react";
import { cn } from "@/src/lib/utils";

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function SettingsModal({ isOpen, onClose }: SettingsModalProps) {
  if (!isOpen) return null;

  const categories = [
    { id: "general", label: "General", icon: Sliders },
    { id: "appearance", label: "Appearance", icon: Palette, active: true },
    { id: "editor", label: "Editor", icon: PenTool },
    { id: "links", label: "Files & Links", icon: Link2 },
    { id: "plugins", label: "Community Plugins", icon: Puzzle },
  ];

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center p-8">
      <motion.div 
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        onClick={onClose}
        className="absolute inset-0 bg-on-surface/40 backdrop-blur-sm" 
      />
      
      <motion.div 
        initial={{ scale: 0.95, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.95, opacity: 0 }}
        className="relative w-full max-w-5xl h-full max-h-[800px] flex shadow-2xl rounded-lg overflow-hidden bg-surface"
      >
        {/* Left Sidebar */}
        <div className="w-64 bg-surface-container-lowest border-r border-outline-variant flex flex-col">
          <div className="p-6 border-b border-outline-variant">
            <h2 className="font-headline-sm font-bold text-on-surface">Settings</h2>
          </div>
          <div className="flex-1 py-4 px-2">
            {categories.map((cat) => (
              <button 
                key={cat.id}
                className={cn(
                  "flex items-center gap-3 w-full px-3 py-2 rounded transition-colors text-sm",
                  cat.active 
                    ? "text-primary border-l-2 border-primary bg-surface-container-low font-medium" 
                    : "text-on-surface-variant hover:bg-surface-container"
                )}
              >
                <cat.icon size={18} />
                {cat.label}
              </button>
            ))}
          </div>
          <div className="p-4 border-t border-outline-variant text-[10px] text-text-muted font-label-mono">
            v1.4.2
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-12 relative">
          <button 
            onClick={onClose}
            className="absolute top-6 right-6 p-2 rounded hover:bg-surface-container transition-colors"
          >
            <X size={20} />
          </button>

          <header className="mb-12">
            <h1 className="font-display-lg text-on-surface mb-2">Appearance</h1>
            <p className="text-body-lg text-on-surface-variant">Manage the look and feel of your knowledge base.</p>
          </header>

          <div className="space-y-12">
            <section>
              <h3 className="font-headline-sm text-on-surface mb-6 border-b border-outline-variant pb-2">Theme</h3>
              <div className="grid gap-3">
                <div className="flex items-center justify-between p-4 bg-surface-container-lowest border border-primary rounded hover:border-primary transition-colors cursor-pointer ring-1 ring-primary/20">
                  <div className="flex items-center gap-4">
                    <div className="w-10 h-10 rounded bg-surface-container flex items-center justify-center text-primary">
                      <Palette size={20} />
                    </div>
                    <div>
                      <div className="text-sm font-medium text-on-surface">Light</div>
                      <div className="font-label-mono text-[10px] text-text-muted">High contrast paper feel</div>
                    </div>
                  </div>
                  <div className="w-4 h-4 rounded-full border-2 border-primary flex items-center justify-center">
                    <div className="w-2 h-2 rounded-full bg-primary" />
                  </div>
                </div>
                {/* Other theme options */}
              </div>
            </section>

            <section>
              <h3 className="font-headline-sm text-on-surface mb-6 border-b border-outline-variant pb-2">Typography</h3>
              <div className="space-y-8">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-sm font-medium text-on-surface">Interface Font</div>
                    <div className="text-[12px] text-on-surface-variant mt-1">Font used for UI elements</div>
                  </div>
                  <button className="px-4 py-2 bg-surface-container-lowest border border-outline-variant rounded flex items-center gap-2 text-sm hover:border-outline transition-colors">
                    Inter <ChevronDown size={16} />
                  </button>
                </div>

                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-sm font-medium text-on-surface">Base Font Size</div>
                    <div className="text-[12px] text-on-surface-variant mt-1">Controls global text scaling</div>
                  </div>
                  <div className="flex items-center gap-4">
                    <span className="font-label-mono text-xs text-text-muted px-2 py-1 bg-surface-container rounded border border-outline-variant">16px</span>
                  </div>
                </div>
              </div>
            </section>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
