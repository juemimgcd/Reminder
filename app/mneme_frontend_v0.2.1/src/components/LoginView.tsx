import React from "react";
import { Lock, ShieldCheck, ArrowRight, Mail, Key } from "lucide-react";
import { motion } from "motion/react";

interface LoginViewProps {
  onLogin: () => void;
}

export default function LoginView({ onLogin }: LoginViewProps) {
  return (
    <div className="min-h-screen flex items-center justify-center p-8 bg-[radial-gradient(circle_at_15%_50%,rgba(79,78,185,0.04),transparent_25%),radial-gradient(circle_at_85%_30%,rgba(79,78,185,0.04),transparent_25%)] bg-background relative overflow-hidden">
      <div className="absolute inset-0 bg-[linear-gradient(to_right,rgba(0,0,0,0.01)_1px,transparent_1px),linear-gradient(to_bottom,rgba(0,0,0,0.01)_1px,transparent_1px)] bg-[size:40px_40px] opacity-50" />
      
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-5xl mx-auto flex flex-col md:flex-row shadow-2xl rounded-2xl overflow-hidden bg-surface-container-lowest/70 backdrop-blur-xl border border-outline-variant/30 relative z-10"
      >
        {/* Left Side */}
        <div className="hidden md:flex md:w-1/2 p-24 flex-col justify-between border-r border-outline-variant/20 relative">
          <div className="absolute inset-0 bg-gradient-to-b from-primary/5 to-transparent pointer-events-none" />
          
          <div>
            <div className="inline-flex items-center gap-2 mb-12 px-3 py-1 rounded-full border border-primary/20 bg-primary/5">
              <Lock size={14} className="text-primary" />
              <span className="font-label-mono text-[10px] text-primary uppercase tracking-wider">Personal Vault</span>
            </div>
            <h1 className="font-serif text-5xl font-semibold text-on-surface mb-6">Mneme</h1>
            <p className="text-body-lg text-text-muted max-w-sm leading-relaxed">
              Your private digital garden. Cultivate your thoughts in a secure, local-first environment designed for clarity and deep focus.
            </p>
          </div>

          <div className="flex items-center gap-2 text-text-muted/60">
            <ShieldCheck size={18} />
            <span className="font-label-mono text-[10px] uppercase tracking-widest">End-to-End Encrypted</span>
          </div>
        </div>

        {/* Right Side */}
        <div className="w-full md:w-1/2 p-12 md:p-24 bg-surface-container-lowest relative">
          <div className="max-w-[360px] mx-auto flex flex-col justify-center h-full">
            <div className="mb-12">
              <h2 className="font-serif text-3xl font-semibold text-on-surface mb-2">Welcome back</h2>
              <p className="text-sm text-text-muted">Enter your details to access your workspace.</p>
            </div>

            <form 
              className="space-y-8" 
              onSubmit={(e) => {
                e.preventDefault();
                onLogin();
              }}
            >
              <div className="space-y-2">
                <label className="block font-label-mono text-[10px] text-on-surface-variant uppercase tracking-wider" htmlFor="email">Email Address</label>
                <div className="relative">
                  <Mail size={16} className="absolute left-0 top-1/2 -translate-y-1/2 text-text-muted/40" />
                  <input 
                    id="email"
                    type="email"
                    className="w-full pl-7 py-3 font-sans text-sm bg-transparent border-b border-outline-variant focus:outline-none focus:border-primary focus:bg-primary/5 transition-all outline-none"
                    placeholder="name@example.com"
                    required
                  />
                </div>
              </div>

              <div className="space-y-2">
                <label className="block font-label-mono text-[10px] text-on-surface-variant uppercase tracking-wider" htmlFor="password">Password</label>
                <div className="relative">
                  <Key size={16} className="absolute left-0 top-1/2 -translate-y-1/2 text-text-muted/40" />
                  <input 
                    id="password"
                    type="password"
                    className="w-full pl-7 py-3 font-sans text-sm bg-transparent border-b border-outline-variant focus:outline-none focus:border-primary focus:bg-primary/5 transition-all outline-none"
                    placeholder="••••••••"
                    required
                  />
                </div>
                <div className="text-right">
                  <button type="button" className="font-label-mono text-[10px] text-text-muted hover:text-primary transition-colors">
                    Forgot password?
                  </button>
                </div>
              </div>

              <div className="pt-4">
                <button 
                  type="submit"
                  className="group w-full h-12 flex items-center justify-center gap-2 bg-primary text-on-primary font-button rounded-full hover:bg-primary-container hover:shadow-lg transition-all duration-300 relative overflow-hidden"
                >
                  <span className="relative z-10">Access Vault</span>
                  <ArrowRight size={18} className="relative z-10 group-hover:translate-x-1 transition-transform" />
                  <div className="absolute inset-0 bg-white/10 translate-y-full group-hover:translate-y-0 transition-transform duration-300" />
                </button>
              </div>
            </form>

            <div className="mt-12 pt-8 border-t border-outline-variant/30 text-center">
              <p className="text-sm text-text-muted">
                Don't have an account? <button className="text-primary hover:underline font-medium">Sign up</button>
              </p>
            </div>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
