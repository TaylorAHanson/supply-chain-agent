import React, { useState, useEffect } from 'react';

interface AvailableTool {
  name: string;
  type: string;
}

interface ToolsAndSkillsModalProps {
  onClose: () => void;
  availableTools: AvailableTool[];
  availableSkills: string[];
  selectedTools: string[];
  selectedSkills: string[];
  onToolsChange: (tools: string[]) => void;
  onSkillsChange: (skills: string[]) => void;
  isLoading: boolean;
}

const QC_BLUE = '#3253DC';
const QC_DARK = '#00205B';

const ToolsAndSkillsModal: React.FC<ToolsAndSkillsModalProps> = ({ 
  onClose,
  availableTools,
  availableSkills,
  selectedTools,
  selectedSkills,
  onToolsChange,
  onSkillsChange,
  isLoading
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [showExplanation, setShowExplanation] = useState(false);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };
    
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  const filteredTools = availableTools.filter(t => 
    t.name.toLowerCase().includes(searchQuery.toLowerCase()) || 
    t.type.toLowerCase().includes(searchQuery.toLowerCase())
  );
  const filteredSkills = availableSkills.filter(s => s.toLowerCase().includes(searchQuery.toLowerCase()));

  const handleToolToggle = (tool: string) => {
    if (selectedTools.includes(tool)) {
      onToolsChange(selectedTools.filter(t => t !== tool));
    } else {
      onToolsChange([...selectedTools, tool]);
    }
  };

  const handleSkillToggle = (skill: string) => {
    if (selectedSkills.includes(skill)) {
      onSkillsChange(selectedSkills.filter(s => s !== skill));
    } else {
      onSkillsChange([...selectedSkills, skill]);
    }
  };

  return (
    <div className="fixed inset-0 bg-[#00205B]/80 z-50 flex justify-center items-center p-4 sm:p-8 backdrop-blur-md animate-in fade-in duration-300">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-7xl h-[90vh] flex flex-col overflow-hidden border border-white/20">
        
        {/* Header */}
        <div className="bg-white border-b border-gray-100 px-10 py-6 flex justify-between items-center shrink-0 z-20 shadow-sm">
          <div>
            <h2 className="text-2xl font-bold text-[#00205B] tracking-tight">My Tools & Skills</h2>
            <p className="text-base text-gray-500 mt-1 font-light">Dynamically loaded based on your Unity Catalog permissions</p>
          </div>
          <button 
            onClick={onClose}
            className="text-gray-400 hover:text-[#E32029] bg-gray-50 hover:bg-red-50 rounded-md p-2 transition-colors focus:outline-none"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12"></path>
            </svg>
          </button>
        </div>
        
        {/* Content */}
        <div className="flex-1 overflow-y-auto p-10 bg-gray-50/30 flex flex-col">
          
          {/* Search Bar */}
          <div className="mb-8 relative">
            <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
              <svg className="h-5 w-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path>
              </svg>
            </div>
            <input
              type="text"
              placeholder="Search tools and skills..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-12 pr-4 py-3 border border-gray-200 rounded-md focus:outline-none focus:ring-2 focus:ring-[#3253DC] focus:border-transparent shadow-sm"
            />
          </div>

          {isLoading ? (
            <div className="flex-1 flex items-center justify-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#3253DC]"></div>
            </div>
          ) : (
            <div className="flex-1 grid grid-cols-1 md:grid-cols-2 gap-8">
              {/* Tools Column */}
              <div className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm flex flex-col">
                <div className="flex items-center mb-4 border-b border-gray-100 pb-4">
                  <div className="w-10 h-10 bg-[#F5F7FF] text-[#3253DC] rounded-md flex items-center justify-center mr-3 border border-[#3253DC]/20">
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"></path><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path></svg>
                  </div>
                  <div>
                    <h3 className="font-bold text-lg text-[#00205B]">Unity Catalog Tools</h3>
                    <p className="text-xs text-gray-500">Functions you have EXECUTE permission on</p>
                  </div>
                  <span className="ml-auto bg-gray-100 text-gray-600 font-bold px-2 py-0.5 rounded text-xs">{filteredTools.length}</span>
                </div>
                
                <div className="flex-1 overflow-y-auto pr-2 space-y-2">
                  {filteredTools.length > 0 ? (
                    filteredTools.map((tool, idx) => (
                      <label key={idx} className="flex items-start bg-gray-50 border border-gray-100 rounded-md p-3 hover:border-[#3253DC]/30 transition-colors cursor-pointer">
                        <div className="flex items-center h-5 mr-3">
                          <input
                            type="checkbox"
                            className="w-4 h-4 text-[#3253DC] bg-white border-gray-300 rounded focus:ring-[#3253DC] focus:ring-2"
                            checked={selectedTools.includes(tool.name)}
                            onChange={() => handleToolToggle(tool.name)}
                          />
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center justify-between mb-1">
                            <span className="font-mono text-sm text-gray-800 break-all pr-2">{tool.name}</span>
                            <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium bg-[#F5F7FF] text-[#3253DC] border border-[#3253DC]/20 shrink-0">
                              {tool.type}
                            </span>
                          </div>
                        </div>
                      </label>
                    ))
                  ) : (
                    <p className="text-gray-400 text-sm text-center py-8">No tools found matching your search.</p>
                  )}
                </div>
              </div>

              {/* Skills Column */}
              <div className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm flex flex-col">
                <div className="flex items-center mb-4 border-b border-gray-100 pb-4">
                  <div className="w-10 h-10 bg-[#F5F7FF] text-[#3253DC] rounded-md flex items-center justify-center mr-3 border border-[#3253DC]/20">
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"></path></svg>
                  </div>
                  <div>
                    <h3 className="font-bold text-lg text-[#00205B]">Agent Skills</h3>
                    <p className="text-xs text-gray-500">SOPs loaded from 'skills' volumes</p>
                  </div>
                  <span className="ml-auto bg-gray-100 text-gray-600 font-bold px-2 py-0.5 rounded text-xs">{filteredSkills.length}</span>
                </div>
                
                <div className="flex-1 overflow-y-auto pr-2 space-y-2">
                  {filteredSkills.length > 0 ? (
                    filteredSkills.map((skill, idx) => (
                      <label key={idx} className="flex items-center bg-gray-50 border border-gray-100 rounded-md p-3 hover:border-[#3253DC]/30 transition-colors cursor-pointer">
                        <div className="flex items-center h-5 mr-3">
                          <input
                            type="checkbox"
                            className="w-4 h-4 text-[#3253DC] bg-white border-gray-300 rounded focus:ring-[#3253DC] focus:ring-2"
                            checked={selectedSkills.includes(skill)}
                            onChange={() => handleSkillToggle(skill)}
                          />
                        </div>
                        <svg className="w-4 h-4 text-[#3253DC] mr-2 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg>
                        <span className="font-medium text-sm text-gray-800">{skill}</span>
                      </label>
                    ))
                  ) : (
                    <p className="text-gray-400 text-sm text-center py-8">No skills found matching your search.</p>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Explanation Section */}
          <div className="mt-8 border border-gray-200 rounded-lg bg-white overflow-hidden shadow-sm shrink-0">
            <button 
              onClick={() => setShowExplanation(!showExplanation)}
              className="w-full px-6 py-4 flex items-center justify-between bg-gray-50 hover:bg-gray-100 transition-colors focus:outline-none"
            >
              <div className="flex items-center">
                <svg className="w-5 h-5 text-[#3253DC] mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                <span className="font-bold text-[#00205B]">What is this?</span>
              </div>
              <svg 
                className={`w-5 h-5 text-gray-400 transform transition-transform duration-300 ${showExplanation ? 'rotate-180' : ''}`} 
                fill="none" stroke="currentColor" viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7"></path>
              </svg>
            </button>
            
            <div className={`transition-all duration-300 ease-in-out ${showExplanation ? 'max-h-96 opacity-100' : 'max-h-0 opacity-0'}`}>
              <div className="p-6 border-t border-gray-200 text-sm text-gray-600 leading-relaxed space-y-4">
                <p>
                  This agent dynamically discovers its capabilities based on <strong>your specific permissions</strong> in Unity Catalog, using the On-Behalf-Of (OBO) token passed from your browser.
                </p>
                <div className="grid grid-cols-2 gap-6">
                  <div className="bg-[#F5F7FF] p-4 rounded-md border border-[#3253DC]/20">
                    <h4 className="font-bold text-[#00205B] mb-2 flex items-center">
                      <svg className="w-4 h-4 mr-2 text-[#3253DC]" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z"></path></svg>
                      Discovery Query
                    </h4>
                    <p className="text-xs">
                      When you open this session, the backend executes a Databricks SQL query against <code className="bg-white px-1 py-0.5 rounded border border-gray-200">system.information_schema</code>.
                    </p>
                  </div>
                  <div className="bg-[#F5F7FF] p-4 rounded-md border border-[#3253DC]/20">
                    <h4 className="font-bold text-[#00205B] mb-2 flex items-center">
                      <svg className="w-4 h-4 mr-2 text-[#3253DC]" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"></path></svg>
                      Governance
                    </h4>
                    <p className="text-xs">
                      Because the query runs as <strong>you</strong>, it only returns functions you have <code className="bg-white px-1 py-0.5 rounded border border-gray-200">EXECUTE</code> permission on, and volumes you have <code className="bg-white px-1 py-0.5 rounded border border-gray-200">READ VOLUME</code> permission on.
                    </p>
                  </div>
                </div>
                <p className="text-xs bg-yellow-50 text-yellow-800 p-3 rounded-md border border-yellow-200">
                  <strong>Note:</strong> This means two different users interacting with this exact same agent might have completely different tools and skills available to them, ensuring strict data governance and security!
                </p>
              </div>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
};

export default ToolsAndSkillsModal;