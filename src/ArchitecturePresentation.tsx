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
    title: "What am I getting?",
    subtitle: "A reusable and repeatable pattern that comes with...",
    content: (
      <div className="flex flex-col h-full animate-in fade-in duration-700">
        <div className="grid grid-cols-4 gap-6 flex-1">
          
          {/* Column 1: Hosting & Orchestration */}
          <div className="bg-white border border-gray-200 rounded-lg p-6 shadow-md hover:shadow-xl transition-all duration-300 transform hover:-translate-y-1">
            <div className="w-12 h-12 bg-[#F5F7FF] text-[#3253DC] rounded-md flex items-center justify-center mb-5 border border-[#3253DC]/20">
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2m-2-4h.01M17 16h.01"></path></svg>
            </div>
            <h3 className="font-bold text-lg text-[#00205B] mb-4 border-b border-gray-100 pb-3">App & Orchestration</h3>
            <ul className="space-y-4 text-sm text-gray-600">
              <li className="flex items-start"><span className="text-[#3253DC] mr-2 font-bold">✓</span> Serverless Databricks Apps Hosting</li>
              <li className="flex items-start"><span className="text-[#3253DC] mr-2 font-bold">✓</span> Native SSO & Identity Propagation</li>
              <li className="flex items-start"><span className="text-[#3253DC] mr-2 font-bold">✓</span> Auto Service Principal Provisioning</li>
              <li className="flex items-start"><span className="text-[#3253DC] mr-2 font-bold">✓</span> LangGraph State Machine Engine</li>
              <li className="flex items-start"><span className="text-[#3253DC] mr-2 font-bold">✓</span> Streaming Server-Sent Events (SSE)</li>
            </ul>
          </div>

          {/* Column 2: Governance & Security */}
          <div className="bg-white border border-gray-200 rounded-lg p-6 shadow-md hover:shadow-xl transition-all duration-300 transform hover:-translate-y-1">
            <div className="w-12 h-12 bg-[#F5F7FF] text-[#3253DC] rounded-md flex items-center justify-center mb-5 border border-[#3253DC]/20">
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"></path></svg>
            </div>
            <h3 className="font-bold text-lg text-[#00205B] mb-4 border-b border-gray-100 pb-3">Governance & Security</h3>
            <ul className="space-y-4 text-sm text-gray-600">
              <li className="flex items-start"><span className="text-[#3253DC] mr-2 font-bold">✓</span> Unity Catalog Tool Registry</li>
              <li className="flex items-start"><span className="text-[#3253DC] mr-2 font-bold">✓</span> On-Behalf-Of (OBO) Execution</li>
              <li className="flex items-start"><span className="text-[#3253DC] mr-2 font-bold">✓</span> Fine-Grained SQL GRANT Controls</li>
              <li className="flex items-start"><span className="text-[#3253DC] mr-2 font-bold">✓</span> Human-in-the-Loop Write Approvals</li>
              <li className="flex items-start"><span className="text-[#3253DC] mr-2 font-bold">✓</span> Dynamic Skills via UC Volumes</li>
            </ul>
          </div>

          {/* Column 3: Model Control & Guardrails */}
          <div className="bg-white border border-gray-200 rounded-lg p-6 shadow-md hover:shadow-xl transition-all duration-300 transform hover:-translate-y-1">
            <div className="w-12 h-12 bg-[#F5F7FF] text-[#3253DC] rounded-md flex items-center justify-center mb-5 border border-[#3253DC]/20">
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg>
            </div>
            <h3 className="font-bold text-lg text-[#00205B] mb-4 border-b border-gray-100 pb-3">Model Control & Guardrails</h3>
            <ul className="space-y-4 text-sm text-gray-600">
              <li className="flex items-start"><span className="text-[#3253DC] mr-2 font-bold">✓</span> AI Gateway Model Routing</li>
              <li className="flex items-start"><span className="text-[#3253DC] mr-2 font-bold">✓</span> Zero-Downtime A/B Testing</li>
              <li className="flex items-start"><span className="text-[#3253DC] mr-2 font-bold">✓</span> Input Guardrails (CCI, PII, Jailbreak)</li>
              <li className="flex items-start"><span className="text-[#3253DC] mr-2 font-bold">✓</span> Output Guardrails (Hallucination)</li>
              <li className="flex items-start"><span className="text-[#3253DC] mr-2 font-bold">✓</span> Centralized Rate Limits & Costing</li>
            </ul>
          </div>

          {/* Column 4: Observability & Evaluation */}
          <div className="bg-white border border-gray-200 rounded-lg p-6 shadow-md hover:shadow-xl transition-all duration-300 transform hover:-translate-y-1">
            <div className="w-12 h-12 bg-[#F5F7FF] text-[#3253DC] rounded-md flex items-center justify-center mb-5 border border-[#3253DC]/20">
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path></svg>
            </div>
            <h3 className="font-bold text-lg text-[#00205B] mb-4 border-b border-gray-100 pb-3">Observability & Evaluation</h3>
            <ul className="space-y-4 text-sm text-gray-600">
              <li className="flex items-start"><span className="text-[#3253DC] mr-2 font-bold">✓</span> MLflow ResponsesAgent Contract</li>
              <li className="flex items-start"><span className="text-[#3253DC] mr-2 font-bold">✓</span> Automatic Multi-Step Tracing</li>
              <li className="flex items-start"><span className="text-[#3253DC] mr-2 font-bold">✓</span> Inference Tables (Delta Logging)</li>
              <li className="flex items-start"><span className="text-[#3253DC] mr-2 font-bold">✓</span> Active UI Feedback (Thumbs Up/Down)</li>
              <li className="flex items-start"><span className="text-[#3253DC] mr-2 font-bold">✓</span> Automated LLM-as-a-Judge Scoring</li>
            </ul>
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
            The Supply Chain Agent is built on the Databricks North Star Architecture. It moves beyond isolated PoCs by integrating directly into the Data Intelligence Platform, ensuring that security, governance, and observability are built-in from day one.
          </p>
        </div>
        
        {/* High level visual */}
        <div className="flex items-center justify-center space-x-4 w-full max-w-6xl">
          {/* Node 1 */}
          <div className="flex-1 bg-white border border-gray-200 rounded-md p-6 text-center shadow-lg hover:shadow-xl transition-all duration-300 transform hover:-translate-y-1 relative overflow-hidden group h-80 flex flex-col">
            <div className="absolute top-0 left-0 w-full h-1 bg-[#3253DC] transform origin-left scale-x-0 group-hover:scale-x-100 transition-transform duration-300"></div>
            <div className="w-14 h-14 bg-[#F5F7FF] text-[#3253DC] rounded-md flex items-center justify-center mx-auto mb-4 border border-[#3253DC]/20 shrink-0">
              <svg className="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"></path></svg>
            </div>
            <h3 className="font-semibold text-lg text-[#00205B] mb-0.5">Databricks Apps</h3>
            <p className="text-[10px] font-medium text-[#3253DC] uppercase tracking-wider mb-3">Secure, serverless hosting</p>
            <ul className="text-xs text-gray-600 text-left space-y-2 flex-1 overflow-y-auto">
              <li className="flex items-start"><span className="text-[#3253DC] mr-2">•</span> Zero-infrastructure serverless hosting</li>
              <li className="flex items-start"><span className="text-[#3253DC] mr-2">•</span> Native SSO & Identity propagation</li>
              <li className="flex items-start"><span className="text-[#3253DC] mr-2">•</span> Automatic Service Principal provisioning</li>
              <li className="flex items-start"><span className="text-[#3253DC] mr-2">•</span> Secure secrets management</li>
            </ul>
          </div>
          
          <ArrowRight className="w-8 h-8 text-[#3253DC]/40 shrink-0" />
          
          {/* Node 2 */}
          <div className="flex-1 bg-white border border-gray-200 rounded-md p-6 text-center shadow-lg hover:shadow-xl transition-all duration-300 transform hover:-translate-y-1 relative overflow-hidden group h-80 flex flex-col">
            <div className="absolute top-0 left-0 w-full h-1 bg-[#3253DC] transform origin-left scale-x-0 group-hover:scale-x-100 transition-transform duration-300"></div>
            <div className="w-14 h-14 bg-[#F5F7FF] text-[#3253DC] rounded-md flex items-center justify-center mx-auto mb-4 border border-[#3253DC]/20 shrink-0">
              <svg className="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z"></path></svg>
            </div>
            <h3 className="font-semibold text-lg text-[#00205B] mb-0.5">AI Gateway</h3>
            <p className="text-[10px] font-medium text-[#3253DC] uppercase tracking-wider mb-3">Centralized routing & guardrails</p>
            <ul className="text-xs text-gray-600 text-left space-y-2 flex-1 overflow-y-auto">
              <li className="flex items-start"><span className="text-[#3253DC] mr-2">•</span> Decoupled model routing (no hardcoded models)</li>
              <li className="flex items-start"><span className="text-[#3253DC] mr-2">•</span> Centralized rate limiting & cost attribution</li>
              <li className="flex items-start"><span className="text-[#3253DC] mr-2">•</span> Zero-downtime A/B testing</li>
              <li className="flex items-start"><span className="text-[#3253DC] mr-2">•</span> Built-in guardrails (PII/Toxicity filtering)</li>
            </ul>
          </div>
          
          <ArrowRight className="w-8 h-8 text-[#3253DC]/40 shrink-0" />
          
          {/* Node 3 */}
          <div className="flex-1 bg-white border border-gray-200 rounded-md p-6 text-center shadow-lg hover:shadow-xl transition-all duration-300 transform hover:-translate-y-1 relative overflow-hidden group h-80 flex flex-col">
            <div className="absolute top-0 left-0 w-full h-1 bg-[#3253DC] transform origin-left scale-x-0 group-hover:scale-x-100 transition-transform duration-300"></div>
            <div className="w-14 h-14 bg-[#F5F7FF] text-[#3253DC] rounded-md flex items-center justify-center mx-auto mb-4 border border-[#3253DC]/20 shrink-0">
              <svg className="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4"></path></svg>
            </div>
            <h3 className="font-semibold text-lg text-[#00205B] mb-0.5">Unity Catalog</h3>
            <p className="text-[10px] font-medium text-[#3253DC] uppercase tracking-wider mb-3">Govern skills & tools like data</p>
            <ul className="text-xs text-gray-600 text-left space-y-2 flex-1 overflow-y-auto">
              <li className="flex items-start"><span className="text-[#3253DC] mr-2">•</span> Centralized registry for data AND functions</li>
              <li className="flex items-start"><span className="text-[#3253DC] mr-2">•</span> On-Behalf-Of (OBO) execution context</li>
              <li className="flex items-start"><span className="text-[#3253DC] mr-2">•</span> Fine-grained SQL GRANT access controls</li>
              <li className="flex items-start"><span className="text-[#3253DC] mr-2">•</span> Reusable tools across multiple agents</li>
            </ul>
          </div>
        </div>
      </div>
    )
  },
  {
    title: "Runtime & Orchestration",
    subtitle: "Databricks Apps + MLflow + LangGraph",
    content: (
      <div className="flex flex-col h-full space-y-8 animate-in fade-in slide-in-from-bottom-8 duration-700">
        <div className="flex-1 flex items-center justify-center">
          {/* Visual representation of the stack */}
          <div className="w-full max-w-4xl bg-white border border-gray-200 rounded-lg p-8 shadow-xl relative overflow-hidden flex space-x-8">
            <div className="absolute top-0 left-0 w-full h-2 bg-[#00205B]"></div>
            
            {/* Left side: The Stack */}
            <div className="flex-1">
              <h3 className="text-xl font-bold text-[#00205B] mb-1 relative z-10">Application Stack</h3>
              <p className="text-sm text-gray-500 mb-6 relative z-10">How the agent is executed and served</p>
              
              <div className="space-y-4">
                <div className="border border-gray-200 rounded-md p-4 bg-gray-50 shadow-sm relative">
                  <div className="absolute -left-3 top-1/2 -translate-y-1/2 w-6 h-6 bg-[#00205B] text-white rounded-md flex items-center justify-center text-xs font-bold">1</div>
                  <h4 className="font-semibold text-[#00205B] ml-4">Databricks Apps (FastAPI)</h4>
                  <p className="text-xs text-gray-600 ml-4 mt-1">Provides the ASGI web server (Uvicorn), handles HTTP requests, SSE streaming, and extracts the `X-Forwarded-Access-Token` for auth.</p>
                </div>
                
                <div className="border border-[#3253DC]/30 rounded-md p-4 bg-[#F5F7FF] shadow-sm relative">
                  <div className="absolute -left-3 top-1/2 -translate-y-1/2 w-6 h-6 bg-[#3253DC] text-white rounded-md flex items-center justify-center text-xs font-bold">2</div>
                  <h4 className="font-semibold text-[#3253DC] ml-4">MLflow ResponsesAgent</h4>
                  <p className="text-xs text-gray-600 ml-4 mt-1">Standardized PyFunc model contract. Automatically traces inputs, outputs, and tool calls without manual instrumentation. Ready for Model Serving.</p>
                </div>
                
                <div className="border border-orange-200 rounded-md p-4 bg-orange-50 shadow-sm relative">
                  <div className="absolute -left-3 top-1/2 -translate-y-1/2 w-6 h-6 bg-orange-500 text-white rounded-md flex items-center justify-center text-xs font-bold">3</div>
                  <h4 className="font-semibold text-orange-700 ml-4">LangGraph State Machine</h4>
                  <p className="text-xs text-gray-600 ml-4 mt-1">The core cognitive engine. Manages conversation state, decides when to call tools, and processes tool outputs in a cyclic graph.</p>
                </div>
              </div>
            </div>
            
            {/* Right side: LangGraph Flow */}
            <div className="flex-1 border-l border-gray-200 pl-8 flex flex-col justify-center">
              <h3 className="text-lg font-bold text-gray-800 mb-6 text-center">LangGraph Execution Flow</h3>
              
              <div className="flex flex-col items-center space-y-3">
                <div className="bg-gray-100 border border-gray-300 px-4 py-2 rounded-lg text-sm font-medium text-gray-700 w-48 text-center shadow-sm">User Input</div>
                <ArrowDown className="w-5 h-5 text-gray-400" />
                
                <div className="bg-blue-50 border-2 border-[#3253DC] px-4 py-3 rounded-md text-sm font-bold text-[#00205B] w-56 text-center shadow-md relative">
                  Agent Node (LLM)
                  <div className="absolute -right-10 top-1/2 -translate-y-1/2">
                    <svg className="w-8 h-8 text-[#3253DC]" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path></svg>
                  </div>
                </div>
                
                <div className="flex space-x-8 my-2">
                  <div className="flex flex-col items-center">
                    <span className="text-[10px] text-gray-500 font-bold mb-1">Needs Tool</span>
                    <ArrowDown className="w-5 h-5 text-gray-400" />
                  </div>
                  <div className="flex flex-col items-center">
                    <span className="text-[10px] text-gray-500 font-bold mb-1">Finished</span>
                    <ArrowDown className="w-5 h-5 text-gray-400" />
                  </div>
                </div>
                
                <div className="flex space-x-4">
                  <div className="bg-emerald-50 border-2 border-emerald-500 px-4 py-3 rounded-md text-sm font-bold text-emerald-800 w-40 text-center shadow-md">
                    Tool Node
                  </div>
                  <div className="bg-gray-100 border border-gray-300 px-4 py-3 rounded-md text-sm font-medium text-gray-700 w-40 text-center shadow-sm flex items-center justify-center">
                    Final Output
                  </div>
                </div>
              </div>
            </div>
            
          </div>
        </div>
      </div>
    )
  },
  {
    title: "Tool Plane & Governance",
    subtitle: "Unity Catalog as the Agent's Operating System",
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
              <h3 className="font-bold text-xl text-[#00205B] mb-2">Agent</h3>
              <p className="text-xs text-gray-500 leading-relaxed">Passes the user's <code className="bg-gray-100 px-1 rounded">X-Forwarded-Access-Token</code> to execute tools securely.</p>
            </div>
            
            {/* Connection */}
            <div className="flex-1 flex flex-col items-center justify-center px-6">
              <span className="text-xs font-bold text-[#3253DC] tracking-wider mb-3 bg-[#F5F7FF] px-4 py-1.5 rounded-lg border border-[#3253DC]/20 shadow-sm">UCFunctionToolkit</span>
              <div className="w-full flex items-center">
                <div className="h-1 w-full bg-[#3253DC]/30 rounded-md"></div>
                <svg className="w-8 h-8 text-[#3253DC] -ml-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5l7 7-7 7"></path></svg>
              </div>
              <p className="text-[10px] text-gray-400 mt-2 text-center">Wraps UC Functions as LangChain Tools</p>
            </div>
            
            {/* UC Node */}
            <div className="w-80 bg-white border border-gray-200 rounded-lg shadow-xl overflow-hidden z-10">
              <div className="bg-[#00205B] py-4 px-6 flex items-center justify-center">
                <svg className="w-6 h-6 text-white mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4"></path></svg>
                <span className="font-bold text-white text-lg tracking-wide">Unity Catalog</span>
              </div>
              <div className="p-5 space-y-3 bg-gray-50">
                <div className="bg-white border border-gray-200 rounded-md p-3 flex flex-col shadow-sm hover:border-[#3253DC] transition-colors">
                  <div className="flex items-center mb-1">
                    <span className="w-2 h-2 rounded-md bg-emerald-500 mr-2"></span>
                    <span className="font-mono font-bold text-sm text-gray-800">get_inventory()</span>
                  </div>
                  <span className="text-[10px] text-gray-500 ml-4">Read-only ERP data access</span>
                </div>
                
                <div className="bg-white border border-gray-200 rounded-md p-3 flex flex-col shadow-sm hover:border-[#3253DC] transition-colors">
                  <div className="flex items-center mb-1">
                    <span className="w-2 h-2 rounded-md bg-[#E32029] mr-2"></span>
                    <span className="font-mono font-bold text-sm text-gray-800">manage_safety_stock()</span>
                  </div>
                  <span className="text-[10px] text-gray-500 ml-4">Write-operation with Human-in-the-Loop</span>
                </div>
                
                <div className="bg-white border border-gray-200 rounded-md p-3 flex flex-col shadow-sm hover:border-[#3253DC] transition-colors">
                  <div className="flex items-center mb-1">
                    <span className="w-2 h-2 rounded-md bg-[#3253DC] mr-2"></span>
                    <span className="font-mono font-bold text-sm text-gray-800">skills/ (Volume)</span>
                  </div>
                  <span className="text-[10px] text-gray-500 ml-4">Dynamic guidelines and instructions (.md files)</span>
                </div>
              </div>
            </div>
            
          </div>
        </div>
        
        <div className="bg-white border-t border-gray-200 pt-6 mt-2">
          <div className="grid grid-cols-2 gap-x-12 gap-y-6 max-w-5xl mx-auto">
            <div>
              <span className="flex items-center font-bold text-[#00205B] text-sm mb-2 uppercase tracking-wide">
                <svg className="w-5 h-5 mr-2 text-[#3253DC]" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"></path></svg>
                Governance & Security
              </span>
              <p className="text-xs text-gray-600 leading-relaxed">Admins control who can execute which tool via standard SQL <code className="bg-gray-100 px-1 rounded">GRANT EXECUTE ON FUNCTION</code> or <code className="bg-gray-100 px-1 rounded">GRANT READ ON VOLUME</code>, eliminating the need to manage API keys in code or duplicate access controls.</p>
            </div>
            <div>
              <span className="flex items-center font-bold text-[#00205B] text-sm mb-2 uppercase tracking-wide">
                <svg className="w-5 h-5 mr-2 text-[#3253DC]" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z"></path></svg>
                On-Behalf-Of (OBO) Execution
              </span>
              <p className="text-xs text-gray-600 leading-relaxed">The agent becomes <strong>YOU</strong>. It doesn't use a generic service principal. It can only discover tools, take actions, and see data that you are explicitly allowed to access in Unity Catalog.</p>
            </div>
            <div>
              <span className="flex items-center font-bold text-[#00205B] text-sm mb-2 uppercase tracking-wide">
                <svg className="w-5 h-5 mr-2 text-[#3253DC]" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path></svg>
                Dynamic Discovery
              </span>
              <p className="text-xs text-gray-600 leading-relaxed">Because the agent queries Unity Catalog as YOU, the tools and skills loaded into the LLM context are <strong>100% personalized to your specific access level</strong>. Two different users will see a completely different set of capabilities.</p>
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
    title: "Dynamic Tool Discovery",
    subtitle: "Personalized Agent Capabilities via OBO",
    content: (
      <div className="flex flex-col h-full space-y-8 animate-in fade-in slide-in-from-bottom-8 duration-700">
        <div className="flex-1 flex items-center justify-center">
          <div className="w-full max-w-5xl bg-white border border-gray-200 rounded-lg p-8 shadow-xl relative overflow-hidden">
            <div className="absolute top-0 left-0 w-full h-2 bg-[#3253DC]"></div>
            
            <div className="flex items-center mb-8">
              <div className="w-16 h-16 bg-[#F5F7FF] text-[#3253DC] rounded-md flex items-center justify-center mr-6 border border-[#3253DC]/20">
                <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z"></path></svg>
              </div>
              <div>
                <h3 className="text-2xl font-bold text-[#00205B]">Per-Session Capability Loading</h3>
                <p className="text-gray-500 mt-1">The agent only knows what you know.</p>
              </div>
            </div>
            
            <div className="grid grid-cols-2 gap-8">
              {/* Left Side */}
              <div className="space-y-6">
                <div className="bg-gray-50 border border-gray-200 rounded-md p-5">
                  <h4 className="font-bold text-[#00205B] mb-2 flex items-center">
                    <span className="bg-[#3253DC] text-white w-6 h-6 rounded-md flex items-center justify-center text-xs mr-2">1</span>
                    User Authenticates
                  </h4>
                  <p className="text-sm text-gray-600">The Databricks App passes your <code className="bg-white px-1 py-0.5 rounded border border-gray-200">X-Forwarded-Access-Token</code> to the backend.</p>
                </div>
                
                <div className="bg-gray-50 border border-gray-200 rounded-md p-5">
                  <h4 className="font-bold text-[#00205B] mb-2 flex items-center">
                    <span className="bg-[#3253DC] text-white w-6 h-6 rounded-md flex items-center justify-center text-xs mr-2">2</span>
                    Agent Queries Unity Catalog
                  </h4>
                  <p className="text-sm text-gray-600">Using Databricks SQL, the agent queries <code className="bg-white px-1 py-0.5 rounded border border-gray-200">system.information_schema</code> using your identity.</p>
                </div>
                
                <div className="bg-gray-50 border border-gray-200 rounded-md p-5">
                  <h4 className="font-bold text-[#00205B] mb-2 flex items-center">
                    <span className="bg-[#3253DC] text-white w-6 h-6 rounded-md flex items-center justify-center text-xs mr-2">3</span>
                    Dynamic Tool Injection
                  </h4>
                  <p className="text-sm text-gray-600">The agent is injected with only the UC Functions you have <code className="bg-white px-1 py-0.5 rounded border border-gray-200">EXECUTE</code> on, and SOPs from volumes you can <code className="bg-white px-1 py-0.5 rounded border border-gray-200">READ</code>.</p>
                </div>
              </div>
              
              {/* Right Side */}
              <div className="bg-[#00205B] rounded-md p-6 text-white relative overflow-hidden flex flex-col justify-center">
                <div className="absolute top-0 right-0 w-32 h-32 bg-[#3253DC] rounded-md blur-3xl opacity-30 -mr-10 -mt-10"></div>
                
                <h4 className="font-bold text-lg mb-4 flex items-center">
                  <svg className="w-5 h-5 mr-2 text-yellow-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg>
                  Why this matters
                </h4>
                
                <ul className="space-y-4 text-sm text-gray-300">
                  <li className="flex items-start">
                    <span className="text-[#3253DC] mr-3 font-bold">✓</span> 
                    <div>
                      <strong className="text-white block">No Hardcoded Tools</strong>
                      As new tools are added to Unity Catalog, the agent automatically discovers them without code changes.
                    </div>
                  </li>
                  <li className="flex items-start">
                    <span className="text-[#3253DC] mr-3 font-bold">✓</span> 
                    <div>
                      <strong className="text-white block">Strict Data Governance</strong>
                      Two users interacting with the exact same agent might have completely different capabilities based on their UC grants.
                    </div>
                  </li>
                  <li className="flex items-start">
                    <span className="text-[#3253DC] mr-3 font-bold">✓</span> 
                    <div>
                      <strong className="text-white block">Cross-Catalog Discovery</strong>
                      The agent can pull tools and skills from any catalog or schema in the workspace, provided the user has access.
                    </div>
                  </li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      </div>
    )
  },
  {
    title: "Model Access & Control",
    subtitle: "AI Gateway for Routing and Guardrails",
    content: (
      <div className="flex flex-col h-full space-y-6 animate-in fade-in slide-in-from-bottom-8 duration-700">
        <div className="flex-1 flex flex-col items-center justify-center">
          
          <div className="w-full max-w-4xl relative flex flex-col items-center">
            {/* Agent */}
            <div className="w-64 bg-white border border-gray-200 rounded-lg p-4 text-center shadow-md z-10">
              <h3 className="font-bold text-lg text-[#00205B]">LangGraph Agent</h3>
              <p className="text-xs text-gray-500 mt-1">Requests Chat Completion</p>
            </div>
            
            {/* Arrow down */}
            <ArrowDown className="w-6 h-6 text-[#3253DC]/40 my-1" />
            
            {/* Gateway */}
            <div className="w-[550px] bg-[#F5F7FF] border-2 border-[#3253DC] rounded-lg p-5 text-center z-10 shadow-xl relative">
              <div className="flex items-center justify-center mb-2 text-[#3253DC]">
                <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4"></path></svg>
                <h3 className="font-bold text-lg text-[#00205B]">AI Gateway Route</h3>
              </div>
              <p className="text-xs text-[#3253DC] font-mono bg-white py-1.5 px-3 rounded-lg border border-[#3253DC]/20 inline-block shadow-sm mb-4">supply_chain_agent_endpoint</p>
              
              {/* Guardrails inside Gateway */}
              <div className="bg-white border border-[#3253DC]/20 rounded-md p-4 text-left shadow-sm">
                <h4 className="font-bold text-[#00205B] text-sm mb-3 flex items-center border-b border-gray-100 pb-2">
                  <svg className="w-4 h-4 mr-2 text-[#E32029]" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"></path></svg>
                  Active Guardrails
                </h4>
                
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wider mb-2 block">Input (Before LLM)</span>
                    <div className="space-y-2">
                      <div className="bg-gray-50 px-2.5 py-1.5 rounded text-xs font-medium text-gray-700 border border-gray-200 flex items-center">
                        <span className="w-2 h-2 rounded-md bg-purple-500 mr-2"></span> PII Redaction
                      </div>
                      <div className="bg-gray-50 px-2.5 py-1.5 rounded text-xs font-medium text-gray-700 border border-gray-200 flex items-center">
                        <span className="w-2 h-2 rounded-md bg-slate-500 mr-2"></span> Jailbreak Detection
                      </div>
                    </div>
                  </div>
                  
                  <div>
                    <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wider mb-2 block">Output (After LLM)</span>
                    <div className="space-y-2">
                      <div className="bg-gray-50 px-2.5 py-1.5 rounded text-xs font-medium text-gray-700 border border-gray-200 flex items-center">
                        <span className="w-2 h-2 rounded-md bg-emerald-500 mr-2"></span> Unsafe Content
                      </div>
                      <div className="bg-gray-50 px-2.5 py-1.5 rounded text-xs font-medium text-gray-700 border border-gray-200 flex items-center">
                        <span className="w-2 h-2 rounded-md bg-blue-500 mr-2"></span> Hallucination Check
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            
            {/* Split paths using SVG */}
            <svg className="w-80 h-12 text-[#3253DC]/40 my-1" viewBox="0 0 320 48" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M160 0 V15 Q160 24 140 24 H40 Q20 24 20 32 V48" stroke="currentColor" strokeWidth="3" fill="none" />
              <path d="M160 0 V15 Q160 24 180 24 H280 Q300 24 300 32 V48" stroke="currentColor" strokeWidth="3" fill="none" />
              <polygon points="15,43 20,48 25,43" fill="currentColor" />
              <polygon points="295,43 300,48 305,43" fill="currentColor" />
              
              <rect x="40" y="9" width="60" height="24" rx="4" fill="white" stroke="#3253DC" strokeWidth="1.5" />
              <text x="70" y="25" fontSize="11" fontWeight="bold" fill="#3253DC" textAnchor="middle">80%</text>
              
              <rect x="220" y="9" width="60" height="24" rx="4" fill="white" stroke="#3253DC" strokeWidth="1.5" />
              <text x="250" y="25" fontSize="11" fontWeight="bold" fill="#3253DC" textAnchor="middle">20%</text>
            </svg>
            
            {/* Models */}
            <div className="flex justify-between w-full max-w-2xl">
              <div className="w-64 bg-white border border-gray-200 rounded-lg p-4 text-center shadow-md hover:shadow-lg transition-shadow">
                <h3 className="font-bold text-base text-[#00205B]">Claude 3.5 Sonnet</h3>
                <span className="inline-block mt-2 px-2 py-0.5 bg-gray-100 text-gray-600 text-[10px] uppercase font-bold tracking-wider rounded">Target A (Control)</span>
              </div>
              <div className="w-64 bg-white border border-gray-200 rounded-lg p-4 text-center shadow-md hover:shadow-lg transition-shadow">
                <h3 className="font-bold text-base text-[#00205B]">Llama 3.1 8B</h3>
                <span className="inline-block mt-2 px-2 py-0.5 bg-[#F5F7FF] text-[#3253DC] text-[10px] uppercase font-bold tracking-wider rounded border border-[#3253DC]/20">Target B (Experiment)</span>
              </div>
            </div>
          </div>
          
        </div>
        
        <div className="bg-white border-t border-gray-200 pt-5 mt-2">
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
              <span className="block font-bold text-[#00205B] text-sm mb-1.5 uppercase tracking-wide">Centralized Guardrails</span>
              <p className="text-xs text-gray-600 leading-relaxed">Enforce safety at the gateway level. Input guardrails (like PII Redaction and Jailbreak detection) run before the LLM, while Output guardrails (like Hallucination and Unsafe Content checks) run after.</p>
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
      <div className="flex flex-col h-full space-y-8 animate-in fade-in slide-in-from-bottom-8 duration-700">
        
        <div className="flex-1 bg-white border border-gray-200 rounded-lg p-10 shadow-xl relative overflow-hidden flex flex-col justify-center">
          {/* Background pattern */}
          <div className="absolute inset-0 opacity-[0.02]" style={{ backgroundImage: 'radial-gradient(#00205B 1px, transparent 1px)', backgroundSize: '24px 24px' }}></div>
          
          <div className="relative z-10 w-full max-w-5xl mx-auto">
            
            {/* Top Row: The Flow */}
            <div className="flex justify-between items-center w-full mb-8">
              <div className="bg-white border border-gray-200 shadow-md rounded-lg p-5 text-center w-56 transform transition-transform hover:-translate-y-1 duration-300">
                <div className="w-12 h-12 bg-[#F5F7FF] text-[#3253DC] rounded-md flex items-center justify-center mx-auto mb-3 border border-[#3253DC]/20">
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M14 10h4.764a2 2 0 011.789 2.894l-3.5 7A2 2 0 0115.263 21h-4.017c-.163 0-.326-.02-.485-.06L7 20m7-10V5a2 2 0 00-2-2h-.095c-.5 0-.905.405-.905.905 0 .714-.211 1.412-.608 2.006L7 11v9m7-10h-2M7 20H5a2 2 0 01-2-2v-6a2 2 0 012-2h2.5"></path></svg>
                </div>
                <span className="text-sm font-bold text-[#00205B] block">User Chat Feedback</span>
                <span className="text-[10px] text-gray-500 mt-1 block">Thumbs Up/Down sent to backend</span>
              </div>
              
              <ArrowRight className="w-8 h-8 text-gray-300" />
              
              <div className="bg-white border border-gray-200 shadow-md rounded-lg p-5 text-center w-56 transform transition-transform hover:-translate-y-1 duration-300">
                <div className="w-12 h-12 bg-[#F5F7FF] text-[#3253DC] rounded-md flex items-center justify-center mx-auto mb-3 border border-[#3253DC]/20">
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path></svg>
                </div>
                <span className="text-sm font-bold text-[#00205B] block">MLflow Tracing</span>
                <span className="text-[10px] text-gray-500 mt-1 block">Captures prompts, tools, & latency</span>
              </div>
              
              <ArrowRight className="w-8 h-8 text-gray-300" />
              
              <div className="bg-white border border-gray-200 shadow-md rounded-lg p-5 text-center w-56 transform transition-transform hover:-translate-y-1 duration-300">
                <div className="w-12 h-12 bg-[#F5F7FF] text-[#3253DC] rounded-md flex items-center justify-center mx-auto mb-3 border border-[#3253DC]/20">
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4"></path></svg>
                </div>
                <span className="text-sm font-bold text-[#00205B] block">Inference Tables</span>
                <span className="text-[10px] text-gray-500 mt-1 block">Payloads logged to Delta via Gateway</span>
              </div>
            </div>
            
            {/* Connection down to Job */}
            <div className="flex justify-end pr-28 mb-3">
              <svg className="w-8 h-12 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 48">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 0v40m0 0l-4-4m4 4l4-4"></path>
              </svg>
            </div>
            
            {/* Bottom: The Job */}
            <div className="bg-[#00205B] rounded-lg p-8 text-white w-full shadow-2xl relative overflow-hidden flex">
              <div className="absolute top-0 right-0 w-32 h-32 bg-[#3253DC] rounded-md blur-3xl opacity-30 -mr-10 -mt-10"></div>
              
              <div className="flex-1 pr-8 border-r border-white/10">
                <div className="flex items-center justify-between mb-4 relative z-10">
                  <h4 className="font-bold text-lg flex items-center">
                    <svg className="w-6 h-6 mr-3 text-yellow-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg>
                    Databricks Job: LLM-as-a-Judge
                  </h4>
                  <span className="text-[10px] bg-white/10 border border-white/20 px-2 py-1 rounded font-bold text-white uppercase tracking-wider">Runs Daily</span>
                </div>
                <div className="text-xs text-gray-300 space-y-2 font-mono bg-black/30 p-4 rounded-md border border-white/5 relative z-10">
                  <p><span className="text-pink-400">SELECT</span> trace_id, request, response <span className="text-pink-400">FROM</span> inference_tables</p>
                  <p><span className="text-pink-400">EVALUATE USING</span> databricks-meta-llama-3-70b-instruct</p>
                  <p className="text-[#3253DC] border-l-4 border-[#3253DC] pl-3 ml-2 my-3 py-1.5 bg-[#3253DC]/10 font-bold">
                    Metrics: Relevance, Professionalism, Tool Accuracy
                  </p>
                  <p><span className="text-pink-400">INSERT INTO</span> agent_metrics_dashboard</p>
                </div>
              </div>
              
              <div className="w-1/3 pl-8 flex flex-col justify-center relative z-10">
                <h4 className="font-bold text-white mb-3 text-sm uppercase tracking-wider">The Improvement Cycle</h4>
                <ol className="text-xs text-gray-300 space-y-3 list-decimal pl-4">
                  <li>Identify traces with low Judge scores or User Thumbs Downs.</li>
                  <li>Analyze MLflow trace to find root cause (e.g., bad tool output vs bad prompt).</li>
                  <li>Update UC <code className="bg-white/10 px-1 rounded">skills_volume</code> SOPs to correct behavior.</li>
                </ol>
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