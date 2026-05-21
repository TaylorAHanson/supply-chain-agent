import React, { useState, useEffect } from 'react';

interface ArchitecturePresentationProps {
  onClose: () => void;
}

// Qualcomm Brand Colors for Tailwind arbitrary values
const QC_BLUE = '#3253DC';
const QC_DARK = '#00205B';
const QC_RED = '#E32029';
const QC_LIGHT = '#F5F7FF';

// Reusable SVG Arrow Component
const ArrowDown = ({ className = "w-6 h-6 text-gray-400" }) => (
  <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 14l-7 7m0 0l-7-7m7 7V3"></path>
  </svg>
);

const ArrowRight = ({ className = "w-6 h-6 text-gray-400" }) => (
  <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M14 5l7 7m0 0l-7 7m7-7H3"></path>
  </svg>
);

const slides = [
  {
    title: "North Star Agent Architecture",
    subtitle: "A scalable foundation for Enterprise AI",
    content: (
      <div className="flex flex-col h-full items-center justify-center animate-in fade-in duration-700">
        <h1 className="text-5xl md:text-6xl font-bold text-[#00205B] mb-16 tracking-tight text-center">North Star Agent Architecture</h1>
        
        <div className="flex flex-col space-y-10 w-full max-w-4xl">
          <div className="flex items-center">
            <svg className="w-10 h-10 text-[#3253DC] mr-6 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M5 13l4 4L19 7"></path></svg>
            <h3 className="text-3xl font-semibold text-gray-800">Copy-Pasteable Agent Template</h3>
          </div>

          <div className="flex items-center">
            <svg className="w-10 h-10 text-[#3253DC] mr-6 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M5 13l4 4L19 7"></path></svg>
            <h3 className="text-3xl font-semibold text-gray-800">Includes Every Databricks Platform Best Practice</h3>
          </div>

          <div className="flex items-center">
            <svg className="w-10 h-10 text-[#3253DC] mr-6 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M5 13l4 4L19 7"></path></svg>
            <h3 className="text-3xl font-semibold text-gray-800">Auto-Discovery of Skills & Tools via OBO</h3>
          </div>

          <div className="flex items-center">
            <svg className="w-10 h-10 text-[#3253DC] mr-6 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M5 13l4 4L19 7"></path></svg>
            <div>
              <h3 className="text-3xl font-semibold text-gray-800">No Code Required to Reuse Pattern</h3>
              <p className="text-2xl text-gray-500 mt-2 font-light">Just change the main text prompt</p>
            </div>
          </div>
        </div>
      </div>
    )
  },
  {
    title: "North Star Architecture",
    subtitle: "Enterprise-Grade AI on Databricks",
    content: (
      <div className="flex flex-col items-center justify-center h-full space-y-8 animate-in fade-in duration-700">
        <div className="text-center max-w-4xl">
          <h3 className="text-3xl font-light text-[#00205B] mb-4">
            Secure, Observable, and Governed AI
          </h3>
          <p className="text-base text-gray-600 font-light leading-relaxed">
            A reusable, repeatable template that packs in every Databricks best practice possible, ensuring that security, governance, and observability are built-in from day one.
          </p>
        </div>
        
        {/* High level visual */}
        <div className="flex items-center justify-center space-x-6 w-full max-w-7xl">
          {/* Node 1 */}
          <div className="flex-1 bg-white border border-gray-200 rounded-md p-6 text-center shadow-lg hover:shadow-xl transition-all duration-300 transform hover:-translate-y-1 relative overflow-hidden group h-[380px] flex flex-col">
            <div className="absolute top-0 left-0 w-full h-1 bg-orange-400 transform origin-left scale-x-0 group-hover:scale-x-100 transition-transform duration-300"></div>
            <div className="w-14 h-14 bg-orange-50 text-orange-500 rounded-md flex items-center justify-center mx-auto mb-4 border border-orange-200 shrink-0">
              <svg className="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"></path></svg>
            </div>
            <h3 className="font-semibold text-lg text-[#00205B] mb-0.5">App & Orchestration</h3>
            <p className="text-[10px] font-medium text-orange-500 uppercase tracking-wider mb-3">Databricks Apps</p>
            <ul className="text-xs text-gray-600 text-left space-y-2 flex-1 overflow-y-auto">
              <li className="flex items-start"><span className="text-orange-500 mr-2">•</span> Serverless Databricks Apps Hosting</li>
              <li className="flex items-start"><span className="text-orange-500 mr-2">•</span> Native SSO & Identity Propagation</li>
              <li className="flex items-start"><span className="text-orange-500 mr-2">•</span> Auto Service Principal Provisioning</li>
              <li className="flex items-start"><span className="text-orange-500 mr-2">•</span> LangGraph State Machine Engine</li>
              <li className="flex items-start"><span className="text-orange-500 mr-2">•</span> FastAPI Server-Sent Events (SSE)</li>
            </ul>
          </div>
          
          {/* Node 2 */}
          <div className="flex-1 bg-white border border-gray-200 rounded-md p-6 text-center shadow-lg hover:shadow-xl transition-all duration-300 transform hover:-translate-y-1 relative overflow-hidden group h-[380px] flex flex-col">
            <div className="absolute top-0 left-0 w-full h-1 bg-purple-500 transform origin-left scale-x-0 group-hover:scale-x-100 transition-transform duration-300"></div>
            <div className="w-14 h-14 bg-purple-50 text-purple-600 rounded-md flex items-center justify-center mx-auto mb-4 border border-purple-200 shrink-0">
              <svg className="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z"></path></svg>
            </div>
            <h3 className="font-semibold text-lg text-[#00205B] mb-0.5">Model Control & Guardrails</h3>
            <p className="text-[10px] font-medium text-purple-500 uppercase tracking-wider mb-3">AI Gateway</p>
            <ul className="text-xs text-gray-600 text-left space-y-2 flex-1 overflow-y-auto">
              <li className="flex items-start"><span className="text-purple-500 mr-2">•</span> Decoupled Model Routing</li>
              <li className="flex items-start"><span className="text-purple-500 mr-2">•</span> Zero-Downtime A/B Testing</li>
              <li className="flex items-start"><span className="text-purple-500 mr-2">•</span> Input Guardrails (CCI, PII, Jailbreak)</li>
              <li className="flex items-start"><span className="text-purple-500 mr-2">•</span> Sync Output Guardrails (Trade-off: No Streaming)</li>
              <li className="flex items-start"><span className="text-purple-500 mr-2">•</span> Centralized Rate Limits & Costing</li>
            </ul>
          </div>
          
          {/* Node 3 */}
          <div className="flex-1 bg-white border border-gray-200 rounded-md p-6 text-center shadow-lg hover:shadow-xl transition-all duration-300 transform hover:-translate-y-1 relative overflow-hidden group h-[380px] flex flex-col">
            <div className="absolute top-0 left-0 w-full h-1 bg-emerald-500 transform origin-left scale-x-0 group-hover:scale-x-100 transition-transform duration-300"></div>
            <div className="w-14 h-14 bg-emerald-50 text-emerald-600 rounded-md flex items-center justify-center mx-auto mb-4 border border-emerald-200 shrink-0">
              <svg className="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"></path><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path></svg>
            </div>
            <h3 className="font-semibold text-lg text-[#00205B] mb-0.5">Governance & Security</h3>
            <p className="text-[10px] font-medium text-emerald-500 uppercase tracking-wider mb-3">Unity Catalog</p>
            <ul className="text-xs text-gray-600 text-left space-y-2 flex-1 overflow-y-auto">
              <li className="flex items-start"><span className="text-emerald-500 mr-2">•</span> Unity Catalog Tool Registry</li>
              <li className="flex items-start"><span className="text-emerald-500 mr-2">•</span> On-Behalf-Of (OBO) Execution</li>
              <li className="flex items-start"><span className="text-emerald-500 mr-2">•</span> Fine-Grained SQL GRANT Controls</li>
              <li className="flex items-start"><span className="text-emerald-500 mr-2">•</span> Human-in-the-Loop Write Approvals</li>
              <li className="flex items-start"><span className="text-emerald-500 mr-2">•</span> Dynamic Skills via UC Volumes</li>
            </ul>
          </div>

          {/* Node 4 */}
          <div className="flex-1 bg-white border border-gray-200 rounded-md p-6 text-center shadow-lg hover:shadow-xl transition-all duration-300 transform hover:-translate-y-1 relative overflow-hidden group h-[380px] flex flex-col">
            <div className="absolute top-0 left-0 w-full h-1 bg-blue-500 transform origin-left scale-x-0 group-hover:scale-x-100 transition-transform duration-300"></div>
            <div className="w-14 h-14 bg-blue-50 text-blue-600 rounded-md flex items-center justify-center mx-auto mb-4 border border-blue-200 shrink-0">
              <svg className="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4"></path></svg>
            </div>
            <h3 className="font-semibold text-lg text-[#00205B] mb-0.5">Observability & Evaluation</h3>
            <p className="text-[10px] font-medium text-blue-500 uppercase tracking-wider mb-3">MLflow & Delta</p>
            <ul className="text-xs text-gray-600 text-left space-y-2 flex-1 overflow-y-auto">
              <li className="flex items-start"><span className="text-blue-500 mr-2">•</span> MLflow ResponsesAgent Contract</li>
              <li className="flex items-start"><span className="text-blue-500 mr-2">•</span> Automatic Multi-Step Tracing</li>
              <li className="flex items-start"><span className="text-blue-500 mr-2">•</span> Inference Tables (Delta Logging)</li>
              <li className="flex items-start"><span className="text-blue-500 mr-2">•</span> Active UI Feedback (Thumbs Up/Down)</li>
              <li className="flex items-start"><span className="text-blue-500 mr-2">•</span> Automated LLM-as-a-Judge Scoring</li>
            </ul>
          </div>
        </div>
      </div>
    )
  },
  {
    title: "Tool Plane & Governance",
    subtitle: "Govern Tools & Skills just like Data",
    content: (
      <div className="flex flex-col h-full space-y-8 animate-in fade-in slide-in-from-bottom-8 duration-700">
        <div className="flex-1 flex items-center justify-center">
          <div className="w-full max-w-5xl flex items-center justify-between">
            
            {/* Agent Node */}
            <div className="w-72 bg-white border border-gray-200 rounded-lg p-8 shadow-xl text-center relative z-10">
              <div className="absolute -top-4 -right-4 bg-[#E32029] text-white text-xs uppercase tracking-wider font-bold px-4 py-2 rounded-md shadow-lg transform rotate-3">
                OBO Auth
              </div>
              <div className="w-16 h-16 bg-[#F5F7FF] text-[#3253DC] rounded-md flex items-center justify-center mx-auto mb-4 border border-[#3253DC]/20">
                <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"></path></svg>
              </div>
              <h3 className="font-bold text-xl text-[#00205B] mb-2">1. Authenticate</h3>
              <p className="text-xs text-gray-500 leading-relaxed">Passes the user's <code className="bg-gray-100 px-1 rounded">X-Forwarded-Access-Token</code> to execute tools securely.</p>
            </div>
            
            {/* Connection */}
            <div className="flex-1 flex flex-col items-center justify-center px-6">
              <span className="text-xs font-bold text-[#3253DC] tracking-wider mb-3 bg-[#F5F7FF] px-4 py-1.5 rounded-lg border border-[#3253DC]/20 shadow-sm">2. Dynamic Query</span>
              <div className="w-full flex items-center">
                <div className="h-1 w-full bg-[#3253DC]/30 rounded-md"></div>
                <svg className="w-8 h-8 text-[#3253DC] -ml-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5l7 7-7 7"></path></svg>
              </div>
              <p className="text-[10px] text-gray-400 mt-2 text-center">Queries <code className="bg-gray-100 px-1 rounded text-[#3253DC]">system.information_schema</code> as YOU</p>
            </div>
            
            {/* UC Node */}
            <div className="w-80 bg-white border border-gray-200 rounded-lg shadow-xl overflow-hidden z-10">
              <div className="bg-[#00205B] py-4 px-6 flex items-center justify-center">
                <svg className="w-6 h-6 text-white mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4"></path></svg>
                <span className="font-bold text-white text-lg tracking-wide">3. Tool Injection</span>
              </div>
              <div className="p-5 space-y-3 bg-gray-50">
                <div className="bg-white border border-gray-200 rounded-md p-3 flex flex-col shadow-sm hover:border-[#3253DC] transition-colors">
                  <div className="flex items-center mb-1">
                    <span className="w-2 h-2 rounded-md bg-emerald-500 mr-2"></span>
                    <span className="font-mono font-bold text-sm text-gray-800">get_inventory()</span>
                  </div>
                  <span className="text-[10px] text-gray-500 ml-4">Only injected if you have <code className="bg-gray-100 px-1 rounded text-[#3253DC]">EXECUTE</code></span>
                </div>
                
                <div className="bg-white border border-gray-200 rounded-md p-3 flex flex-col shadow-sm hover:border-[#3253DC] transition-colors">
                  <div className="flex items-center mb-1">
                    <span className="w-2 h-2 rounded-md bg-[#E32029] mr-2"></span>
                    <span className="font-mono font-bold text-sm text-gray-800">manage_safety_stock()</span>
                  </div>
                  <span className="text-[10px] text-gray-500 ml-4">Human-in-the-Loop Write actions</span>
                </div>
                
                <div className="bg-white border border-gray-200 rounded-md p-3 flex flex-col shadow-sm hover:border-[#3253DC] transition-colors">
                  <div className="flex items-center mb-1">
                    <span className="w-2 h-2 rounded-md bg-[#3253DC] mr-2"></span>
                    <span className="font-mono font-bold text-sm text-gray-800">skills/ (Volume)</span>
                  </div>
                  <span className="text-[10px] text-gray-500 ml-4">Only injected if you have <code className="bg-gray-100 px-1 rounded text-[#3253DC]">READ</code></span>
                </div>
              </div>
            </div>
            
          </div>
        </div>
        
        <div className="bg-white border-t border-gray-200 pt-6 mt-2">
          <div className="grid grid-cols-2 gap-x-12 gap-y-6 max-w-5xl mx-auto">
            <div>
              <span className="flex items-center font-bold text-[#00205B] text-sm mb-2 uppercase tracking-wide">
                <svg className="w-5 h-5 mr-2 text-[#3253DC]" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z"></path></svg>
                On-Behalf-Of (OBO) Execution
              </span>
              <p className="text-xs text-gray-600 leading-relaxed">The agent becomes <strong>YOU</strong>. It doesn't use a generic service principal. Two users interacting with the exact same agent might have completely different capabilities based on their UC grants.</p>
            </div>
            <div>
              <span className="flex items-center font-bold text-[#00205B] text-sm mb-2 uppercase tracking-wide">
                <svg className="w-5 h-5 mr-2 text-[#3253DC]" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path></svg>
                No Hardcoded Tools
              </span>
              <p className="text-xs text-gray-600 leading-relaxed">As new tools are added to Unity Catalog, the agent automatically discovers them without code changes. The agent can pull tools and skills from any catalog or schema in the workspace.</p>
            </div>
            <div>
              <span className="flex items-center font-bold text-[#00205B] text-sm mb-2 uppercase tracking-wide">
                <svg className="w-5 h-5 mr-2 text-[#3253DC]" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"></path></svg>
                Governance & Configuration
              </span>
              <p className="text-xs text-gray-600 leading-relaxed">Admins control access via standard SQL <code className="bg-gray-100 px-1 rounded">GRANT EXECUTE ON FUNCTION</code>. They can set default active tools in <code className="bg-gray-100 px-1 rounded">databricks.yml</code>, while users can toggle specific tools on or off in the UI.</p>
            </div>
            <div>
              <span className="flex items-center font-bold text-[#00205B] text-sm mb-2 uppercase tracking-wide">
                <svg className="w-5 h-5 mr-2 text-[#3253DC]" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path></svg>
                Human-in-the-Loop
              </span>
              <p className="text-xs text-gray-600 leading-relaxed">Destructive operations (like updating safety stock) require explicit string matching of user approval before the UC function executes the write, ensuring the agent cannot autonomously modify critical data.</p>
            </div>
          </div>
        </div>
      </div>
    )
  },
  {
    title: "Model Access & Control",
    subtitle: "AI Gateway + LangGraph Orchestration",
    content: (
      <div className="flex flex-col h-full space-y-6 animate-in fade-in slide-in-from-bottom-8 duration-700">
        <div className="flex-1 flex items-center justify-center w-full pt-8">
          
          <div className="w-full max-w-6xl flex items-center justify-center space-x-6 relative">
            
            {/* Agent */}
            <div className="w-64 bg-white border border-gray-200 rounded-lg p-5 text-center shadow-md relative shrink-0">
              <div className="absolute -top-3 -right-3 bg-orange-500 text-white text-[10px] font-bold px-2 py-1 rounded shadow-sm">Databricks Apps</div>
              <h3 className="font-bold text-lg text-[#00205B]">LangGraph State Machine</h3>
              <p className="text-xs text-gray-500 mt-2 leading-relaxed">Core cognitive engine hosted on Serverless FastAPI. Manages state and requests Completions.</p>
            </div>
            
            {/* Arrow Right */}
            <ArrowRight className="w-6 h-6 text-[#3253DC]/40 shrink-0" />
            
            {/* Gateway */}
            <div className="w-[450px] bg-[#F5F7FF] border-2 border-[#3253DC] rounded-lg p-4 text-center shadow-xl relative shrink-0">
              <div className="flex items-center justify-center mb-1 text-[#3253DC]">
                <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4"></path></svg>
                <h3 className="font-bold text-lg text-[#00205B]">AI Gateway Route</h3>
              </div>
              <p className="text-[10px] text-[#3253DC] font-mono bg-white py-1 px-2 rounded-lg border border-[#3253DC]/20 inline-block shadow-sm mb-3">supply_chain_agent_endpoint</p>
              
              {/* Features inside Gateway */}
              <div className="bg-white border border-[#3253DC]/20 rounded-md p-3 text-left shadow-sm">
                
                <div className="flex justify-between items-center border-b border-gray-100 pb-2 mb-2">
                  <h4 className="font-bold text-[#00205B] text-xs flex items-center">
                    <svg className="w-3 h-3 mr-1 text-[#E32029]" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"></path></svg>
                    Active Guardrails & Limits
                  </h4>
                </div>
                
                <div className="grid grid-cols-2 gap-x-3 gap-y-2">
                  <div className="bg-gray-50 px-2 py-1.5 rounded text-[10px] font-medium text-gray-700 border border-gray-200 flex items-center">
                    <span className="w-1.5 h-1.5 rounded-full bg-purple-500 mr-1.5"></span> PII Redaction (Input)
                  </div>
                  <div className="bg-gray-50 px-2 py-1.5 rounded text-[10px] font-medium text-gray-700 border border-gray-200 flex items-center">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 mr-1.5"></span> Unsafe Content (Output)
                  </div>
                  <div className="bg-gray-50 px-2 py-1.5 rounded text-[10px] font-medium text-gray-700 border border-gray-200 flex items-center">
                    <span className="w-1.5 h-1.5 rounded-full bg-orange-500 mr-1.5"></span> Rate Limits (Per User)
                  </div>
                  <div className="bg-gray-50 px-2 py-1.5 rounded text-[10px] font-medium text-gray-700 border border-gray-200 flex items-center">
                    <span className="w-1.5 h-1.5 rounded-full bg-blue-500 mr-1.5"></span> Cost Limits (Per Service)
                  </div>
                </div>
              </div>
              
              {/* Logging branching down */}
              <div className="absolute -bottom-16 left-1/2 -translate-x-1/2 flex flex-col items-center">
                <ArrowDown className="w-5 h-5 text-gray-400 mb-1" />
                <div className="bg-blue-50 border border-blue-200 text-blue-700 text-[10px] font-bold px-3 py-1.5 rounded-full shadow-sm flex items-center whitespace-nowrap">
                  <svg className="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4"></path></svg>
                  Logs to Inference Tables
                </div>
              </div>
            </div>
            
            {/* Split paths using SVG */}
            <div className="relative w-16 h-36 shrink-0 flex items-center -ml-2">
              <svg className="w-full h-full text-[#3253DC]/40" viewBox="0 0 64 144" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M0 72 L20 72 Q32 72 32 52 L32 32 Q32 20 44 20 L64 20" stroke="currentColor" strokeWidth="2" fill="none" />
                <path d="M0 72 L20 72 Q32 72 32 92 L32 112 Q32 124 44 124 L64 124" stroke="currentColor" strokeWidth="2" fill="none" />
                <polygon points="59,15 64,20 59,25" fill="currentColor" />
                <polygon points="59,119 64,124 59,129" fill="currentColor" />
                
                <rect x="0" y="5" width="36" height="18" rx="4" fill="white" stroke="#3253DC" strokeWidth="1" />
                <text x="18" y="17" fontSize="10" fontWeight="bold" fill="#3253DC" textAnchor="middle">80%</text>
                
                <rect x="0" y="109" width="36" height="18" rx="4" fill="white" stroke="#3253DC" strokeWidth="1" />
                <text x="18" y="121" fontSize="10" fontWeight="bold" fill="#3253DC" textAnchor="middle">20%</text>
              </svg>
            </div>
            
            {/* Models */}
            <div className="flex flex-col justify-between h-40 shrink-0 space-y-6">
              <div className="w-56 bg-white border border-gray-200 rounded-lg p-3 text-center shadow-md relative">
                <div className="absolute -top-2 -right-2 bg-blue-500 text-white text-[9px] font-bold px-1.5 py-0.5 rounded shadow-sm">MLflow Serving</div>
                <h3 className="font-bold text-sm text-[#00205B] mt-1">Claude 3.5 Sonnet</h3>
                <span className="inline-block mt-1 px-1.5 py-0.5 bg-gray-100 text-gray-600 text-[9px] uppercase font-bold tracking-wider rounded">Target A (Control)</span>
              </div>
              <div className="w-56 bg-white border border-gray-200 rounded-lg p-3 text-center shadow-md relative">
                <div className="absolute -top-2 -right-2 bg-blue-500 text-white text-[9px] font-bold px-1.5 py-0.5 rounded shadow-sm">MLflow Serving</div>
                <h3 className="font-bold text-sm text-[#00205B] mt-1">Llama 3.1 8B</h3>
                <span className="inline-block mt-1 px-1.5 py-0.5 bg-[#F5F7FF] text-[#3253DC] text-[9px] uppercase font-bold tracking-wider rounded border border-[#3253DC]/20">Target B (Experiment)</span>
              </div>
            </div>
          </div>
          
        </div>
        
        <div className="bg-white border-t border-gray-200 pt-5 mt-12">
          <div className="grid grid-cols-3 gap-6 max-w-5xl mx-auto">
            <div>
              <span className="block font-bold text-[#00205B] text-sm mb-1.5 uppercase tracking-wide">Decoupled Architecture</span>
              <p className="text-xs text-gray-600 leading-relaxed">The agent code never hardcodes a specific model version. It points to a stable route, preventing code churn when models update or deprecate.</p>
            </div>
            <div>
              <span className="block font-bold text-[#00205B] text-sm mb-1.5 uppercase tracking-wide">Zero-Downtime A/B Testing</span>
              <p className="text-xs text-gray-600 leading-relaxed">We are currently routing 20% of traffic to Llama 3 to test cost/performance tradeoffs. We can adjust this dial instantly without redeploying the app.</p>
            </div>
            <div>
              <span className="block font-bold text-[#00205B] text-sm mb-1.5 uppercase tracking-wide">Centralized Guardrails & Limits</span>
              <p className="text-xs text-gray-600 leading-relaxed">Enforce safety at the gateway level. Input/output guardrails run seamlessly, while Rate and Cost limits prevent abuse per-user or per-service.</p>
            </div>
          </div>
        </div>
      </div>
    )
  },
  {
    title: "Observability & Feedback Loop",
    subtitle: "Data-Driven Agent Improvement",
    content: (
      <div className="flex flex-col h-full space-y-4 animate-in fade-in slide-in-from-bottom-8 duration-700">
        
        <div className="flex-1 bg-white border border-gray-200 rounded-lg p-6 shadow-xl relative overflow-hidden flex flex-col justify-center">
          {/* Background pattern */}
          <div className="absolute inset-0 opacity-[0.02]" style={{ backgroundImage: 'radial-gradient(#00205B 1px, transparent 1px)', backgroundSize: '24px 24px' }}></div>
          
          <div className="relative z-10 w-full max-w-5xl mx-auto">
            
            {/* Top Row: The Flow */}
            <div className="flex justify-between items-center w-full mb-4">
              <div className="bg-white border border-gray-200 shadow-md rounded-lg p-4 text-center w-56 transform transition-transform hover:-translate-y-1 duration-300">
                <div className="w-10 h-10 bg-[#F5F7FF] text-[#3253DC] rounded-md flex items-center justify-center mx-auto mb-2 border border-[#3253DC]/20">
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M14 10h4.764a2 2 0 011.789 2.894l-3.5 7A2 2 0 0115.263 21h-4.017c-.163 0-.326-.02-.485-.06L7 20m7-10V5a2 2 0 00-2-2h-.095c-.5 0-.905.405-.905.905 0 .714-.211 1.412-.608 2.006L7 11v9m7-10h-2M7 20H5a2 2 0 01-2-2v-6a2 2 0 012-2h2.5"></path></svg>
                </div>
                <span className="text-sm font-bold text-[#00205B] block">User Chat Feedback</span>
                <span className="text-[10px] text-gray-500 mt-1 block">Thumbs Up/Down sent to backend</span>
              </div>
              
              <ArrowRight className="w-6 h-6 text-gray-300" />
              
              <div className="bg-white border border-gray-200 shadow-md rounded-lg p-4 text-center w-56 transform transition-transform hover:-translate-y-1 duration-300">
                <div className="w-10 h-10 bg-[#F5F7FF] text-[#3253DC] rounded-md flex items-center justify-center mx-auto mb-2 border border-[#3253DC]/20">
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path></svg>
                </div>
                <span className="text-sm font-bold text-[#00205B] block">MLflow Tracing</span>
                <span className="text-[10px] text-gray-500 mt-1 block">Captures prompts, tools, & latency</span>
              </div>
              
              <ArrowRight className="w-6 h-6 text-gray-300" />
              
              <div className="bg-white border border-gray-200 shadow-md rounded-lg p-4 text-center w-56 transform transition-transform hover:-translate-y-1 duration-300">
                <div className="w-10 h-10 bg-[#F5F7FF] text-[#3253DC] rounded-md flex items-center justify-center mx-auto mb-2 border border-[#3253DC]/20">
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4"></path></svg>
                </div>
                <span className="text-sm font-bold text-[#00205B] block">Inference Tables</span>
                <span className="text-[10px] text-gray-500 mt-1 block">Payloads logged to Delta via Gateway</span>
              </div>
            </div>
            
            {/* Connection down to Job */}
            <div className="flex justify-end pr-28 mb-1">
              <svg className="w-8 h-8 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 32">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 0v24m0 0l-4-4m4 4l4-4"></path>
              </svg>
            </div>
            
            {/* Bottom: The Job */}
            <div className="bg-[#00205B] rounded-lg p-5 text-white w-full shadow-2xl relative overflow-hidden flex">
              <div className="absolute top-0 right-0 w-32 h-32 bg-[#3253DC] rounded-md blur-3xl opacity-30 -mr-10 -mt-10"></div>
              
              <div className="flex-1 pr-6 border-r border-white/10">
                <div className="flex items-center justify-between mb-3 relative z-10">
                  <h4 className="font-bold text-base flex items-center">
                    <svg className="w-5 h-5 mr-2 text-yellow-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg>
                    Databricks Job: LLM-as-a-Judge
                  </h4>
                  <span className="text-[9px] bg-white/10 border border-white/20 px-2 py-1 rounded font-bold text-white uppercase tracking-wider">Runs Daily</span>
                </div>
                <div className="text-[10px] text-gray-300 space-y-1.5 font-mono bg-black/30 p-3 rounded-md border border-white/5 relative z-10">
                  <p><span className="text-pink-400">SELECT</span> trace_id, request, response <span className="text-pink-400">FROM</span> inference_tables</p>
                  <p><span className="text-pink-400">EVALUATE USING</span> databricks-meta-llama-3-70b-instruct</p>
                  <p className="text-[#3253DC] border-l-4 border-[#3253DC] pl-3 ml-2 my-2 py-1.5 bg-[#3253DC]/10 font-bold">
                    Metrics: Relevance, Professionalism, Tool Accuracy
                  </p>
                  <p><span className="text-pink-400">INSERT INTO</span> agent_metrics_dashboard</p>
                </div>
              </div>
              
              <div className="w-[45%] pl-6 flex flex-col justify-center relative z-10">
                <h4 className="font-bold text-white mb-2 text-xs uppercase tracking-wider flex items-center">
                  <svg className="w-3 h-3 mr-1.5 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                  Actionable Result Example
                </h4>
                <div className="space-y-2">
                  <div className="bg-white/5 border border-white/10 rounded-md p-2 relative overflow-hidden">
                    <div className="absolute left-0 top-0 bottom-0 w-1 bg-red-500"></div>
                    <span className="text-red-400 font-bold text-[9px] uppercase tracking-wider block mb-0.5">1. Issue Detected</span>
                    <p className="text-[10px] text-gray-300 leading-snug">Judge flags "Tool Accuracy" score 2/5. Agent gave wrong lead time.</p>
                  </div>
                  <div className="bg-white/5 border border-white/10 rounded-md p-2 relative overflow-hidden">
                    <div className="absolute left-0 top-0 bottom-0 w-1 bg-yellow-500"></div>
                    <span className="text-yellow-400 font-bold text-[9px] uppercase tracking-wider block mb-0.5">2. Root Cause Analysis</span>
                    <p className="text-[10px] text-gray-300 leading-snug">Trace shows Agent passed a String instead of an Integer to <code className="text-yellow-200 bg-black/20 px-1 py-0.5 rounded">get_lead_time</code>.</p>
                  </div>
                  <div className="bg-white/5 border border-white/10 rounded-md p-2 relative overflow-hidden">
                    <div className="absolute left-0 top-0 bottom-0 w-1 bg-emerald-500"></div>
                    <span className="text-emerald-400 font-bold text-[9px] uppercase tracking-wider block mb-0.5">3. The Zero-Code Fix</span>
                    <p className="text-[10px] text-gray-300 leading-snug">Data Engineer updates <code className="text-emerald-200 bg-black/20 px-1 py-0.5 rounded">COMMENT</code> via SQL. Agent auto-discovers fix via OBO.</p>
                  </div>
                </div>
              </div>
            </div>
            
          </div>
        </div>
        
      </div>
    )
  }
];

const ArchitecturePresentation: React.FC<ArchitecturePresentationProps> = ({ onClose }) => {
  const [currentSlide, setCurrentSlide] = useState(0);

  // Add keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'ArrowRight') {
        if (currentSlide < slides.length - 1) setCurrentSlide(prev => prev + 1);
      } else if (e.key === 'ArrowLeft') {
        if (currentSlide > 0) setCurrentSlide(prev => prev - 1);
      } else if (e.key === 'Escape') {
        onClose();
      }
    };
    
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [currentSlide, onClose]);

  const nextSlide = () => {
    if (currentSlide < slides.length - 1) setCurrentSlide(currentSlide + 1);
  };

  const prevSlide = () => {
    if (currentSlide > 0) setCurrentSlide(currentSlide - 1);
  };

  return (
    <div className="fixed inset-0 bg-[#00205B]/80 z-50 flex justify-center items-center p-4 sm:p-8 backdrop-blur-md animate-in fade-in duration-300">
      <div className="bg-white rounded-lg shadow-2xl w-full max-w-7xl h-[90vh] flex flex-col overflow-hidden border border-white/20">
        
        {/* Header */}
        <div className="bg-white border-b border-gray-100 px-10 py-6 flex justify-between items-center shrink-0 z-20 shadow-sm">
          <div>
            <h2 className="text-2xl font-bold text-[#00205B] tracking-tight">{slides[currentSlide].title}</h2>
            <p className="text-base text-gray-500 mt-1 font-light">{slides[currentSlide].subtitle}</p>
          </div>
          <button 
            onClick={onClose}
            className="text-gray-400 hover:text-[#E32029] bg-gray-50 hover:bg-red-50 rounded-md p-3 transition-colors focus:outline-none"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12"></path>
            </svg>
          </button>
        </div>
        
        {/* Slide Content */}
        <div className="flex-1 overflow-y-auto p-10 relative bg-gray-50/30">
          {/* We use key={currentSlide} to force React to re-mount the content, triggering the animate-in classes */}
          <div key={currentSlide} className="h-full">
            {slides[currentSlide].content}
          </div>
        </div>
        
        {/* Footer / Controls */}
        <div className="bg-white border-t border-gray-100 px-10 py-5 flex justify-between items-center shrink-0 z-20">
          <button 
            onClick={prevSlide}
            disabled={currentSlide === 0}
            className={`flex items-center px-5 py-2.5 rounded-md font-semibold text-sm transition-all ${
              currentSlide === 0 
                ? 'text-gray-300 cursor-not-allowed' 
                : 'text-[#00205B] hover:bg-[#F5F7FF]'
            }`}
          >
            <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 19l-7-7 7-7"></path></svg>
            Previous
          </button>
          
          <div className="flex space-x-3">
            {slides.map((_, idx) => (
              <button
                key={idx}
                onClick={() => setCurrentSlide(idx)}
                className={`h-2.5 rounded-md transition-all duration-500 ${
                  currentSlide === idx ? 'bg-[#3253DC] w-10' : 'bg-gray-200 hover:bg-gray-300 w-2.5'
                }`}
                aria-label={`Go to slide ${idx + 1}`}
              />
            ))}
          </div>
          
          <button 
            onClick={nextSlide}
            disabled={currentSlide === slides.length - 1}
            className={`flex items-center px-6 py-2.5 rounded-md font-semibold text-sm transition-all shadow-sm ${
              currentSlide === slides.length - 1 
                ? 'text-gray-400 bg-gray-100 cursor-not-allowed' 
                : 'text-white bg-[#3253DC] hover:bg-[#00205B] hover:shadow-md transform hover:-translate-y-0.5'
            }`}
          >
            Next
            <svg className="w-5 h-5 ml-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5l7 7-7 7"></path></svg>
          </button>
        </div>
        
      </div>
    </div>
  );
};

export default ArchitecturePresentation;