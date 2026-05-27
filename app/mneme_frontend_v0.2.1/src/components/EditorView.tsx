import React, { useState } from "react";
import { 
  ZoomIn, 
  ZoomOut, 
  Highlighter, 
  MessageSquare, 
  Bold, 
  List, 
  Search 
} from "lucide-react";
import { cn } from "@/src/lib/utils";

export default function EditorView() {
  const [zoom, setZoom] = useState(100);

  return (
    <div className="flex-1 flex overflow-hidden bg-white h-full relative">
      {/* Main Content Area: Content & Metadata View */}
      <div className="flex-1 flex flex-col min-w-0 bg-white">
        <div className="h-10 border-b border-slate-100 flex items-center justify-between px-6 bg-white shrink-0">
          <div className="flex items-center space-x-2">
            <button onClick={() => setZoom(z => Math.max(50, z - 10))} className="p-1 rounded hover:bg-slate-50 text-slate-400">
              <ZoomOut size={14} />
            </button>
            <span className="text-[10px] font-mono text-slate-400 w-8 text-center">{zoom}%</span>
            <button onClick={() => setZoom(z => Math.min(200, z + 10))} className="p-1 rounded hover:bg-slate-50 text-slate-400">
              <ZoomIn size={14} />
            </button>
          </div>
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-1">
              <span className="text-[10px] text-slate-400 font-medium">Last edit: 2 mins ago</span>
            </div>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-12 bg-slate-50 shadow-inner flex justify-center">
          <div 
            className="w-full max-w-2xl bg-white shadow-sm border border-slate-200 p-16 transition-all h-fit"
            style={{ transform: `scale(${zoom / 100})`, transformOrigin: 'top center' }}
          >
            <h1 className="text-4xl font-bold text-slate-900 mb-6">Digital Garden Architecture</h1>
            <p className="text-slate-600 leading-relaxed mb-6 italic border-l-4 border-indigo-500 pl-4 bg-indigo-50 py-3 rounded-r-sm">
              Exploring the convergence of bi-directional linking and mental graph visualization for personal knowledge management.
            </p>
            <div className="space-y-6 text-slate-700 leading-relaxed text-sm">
              <p>The core philosophy of Mneme v2.0 is based on the <strong>Zettelkasten</strong> method, where every node is a small, atomic idea that connects to others. Unlike hierarchical storage, these connections create a <i>rhizomatic</i> structure.</p>
              
              <h2 className="text-xl font-semibold text-slate-900 mt-10 mb-4">Key Concepts</h2>
              <ul className="list-disc pl-5 space-y-3">
                <li><strong>Bi-directional links</strong>: Seeing who refers to you as much as who you refer to.</li>
                <li><strong>Unlinked mentions</strong>: Discovering connections automatically via NLP.</li>
                <li><strong>Local Graph</strong>: Focusing on immediate context rather than global noise.</li>
              </ul>
              
              <div className="mt-10 p-4 bg-slate-50 border border-slate-200 rounded-lg">
                <code className="text-[11px] text-indigo-600 font-mono">[[Graph Visualization Strategy]] -- link to research</code>
              </div>
              
              <p>As we move toward v2.0, the focus shifts to performance. Indexing 10,000+ markdown files requires a custom WASM-based search engine to maintain the fluid UX we desire.</p>
            </div>
          </div>
        </div>
      </div>

      {/* Right Sidebar: Metadata & Local Graph */}
      <aside className="w-72 bg-slate-50 border-l border-slate-200 flex flex-col shrink-0">
        <div className="h-48 border-b border-slate-200 relative overflow-hidden bg-white/50">
          <div className="absolute inset-0 bg-[radial-gradient(#e2e8f0_1px,transparent_1px)] [background-size:16px_16px]"></div>
          <div className="absolute inset-0 flex items-center justify-center p-4">
            <div className="w-full h-full border border-slate-200/50 rounded flex items-center justify-center bg-slate-50/50 backdrop-blur-[1px]">
              <div className="relative w-32 h-32">
                <div className="absolute top-1/2 left-1/2 w-3 h-3 bg-indigo-500 rounded-full -translate-x-1/2 -translate-y-1/2 shadow-lg shadow-indigo-100" />
                <div className="absolute top-1/4 left-1/4 w-1.5 h-1.5 bg-slate-300 rounded-full" />
                <div className="absolute bottom-1/4 right-1/4 w-2 h-2 bg-slate-300 rounded-full" />
                <div className="absolute top-10 right-10 w-1.5 h-1.5 bg-slate-300 rounded-full" />
                <svg className="absolute inset-0 w-full h-full opacity-20">
                  <line x1="50%" y1="50%" x2="25%" y2="25%" stroke="#64748b" strokeWidth="1" />
                  <line x1="50%" y1="50%" x2="75%" y2="75%" stroke="#64748b" strokeWidth="1" />
                </svg>
              </div>
            </div>
          </div>
          <div className="absolute top-2 left-2 px-2 py-0.5 bg-white/80 backdrop-blur rounded text-[8px] font-bold text-slate-400 border border-slate-200 uppercase tracking-tighter">Local Graph</div>
        </div>

        <div className="flex-1 overflow-y-auto p-5 space-y-8">
          <div>
            <h4 className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-4">Properties</h4>
            <div className="space-y-2">
              <div className="flex justify-between text-[11px]">
                <span className="text-slate-400">Created</span>
                <span className="text-slate-600 font-medium">Nov 24, 2023</span>
              </div>
              <div className="flex justify-between text-[11px]">
                <span className="text-slate-400">State</span>
                <span className="bg-emerald-50 text-emerald-600 px-1.5 py-0.5 rounded text-[9px] font-bold border border-emerald-100 uppercase tracking-tighter">Evergreen</span>
              </div>
            </div>
          </div>

          <div>
            <h4 className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-4">Linked References</h4>
            <div className="space-y-2">
              <div className="p-3 bg-white border border-slate-200 rounded text-[11px] hover:border-indigo-300 transition-colors cursor-pointer group shadow-sm">
                <div className="font-semibold text-indigo-600 truncate group-hover:text-primary transition-colors">PKM Workflow 2024</div>
                <div className="text-[10px] text-slate-400 mt-1 line-clamp-2">...using Digital Garden Architecture as a foundation for nodes...</div>
              </div>
              <div className="p-3 bg-white border border-slate-200 rounded text-[11px] hover:border-indigo-300 transition-colors cursor-pointer group shadow-sm">
                <div className="font-semibold text-indigo-600 truncate group-hover:text-primary transition-colors">Zettelkasten Systems</div>
                <div className="text-[10px] text-slate-400 mt-1 line-clamp-2">Exploring density in notes using Atomic Ideas...</div>
              </div>
            </div>
          </div>
        </div>
      </aside>
    </div>
  );
}
