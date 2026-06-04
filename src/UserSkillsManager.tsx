import React, { useState, useEffect, useCallback } from 'react';

interface UserSkill {
  name: string;
  description: string;
}

const NEW_SKILL_TEMPLATE = `---
description: One line describing when the agent should use this skill
---

# Skill name

Write the step-by-step instructions the agent should follow here.
`;

const UserSkillsManager: React.FC = () => {
  const [skills, setSkills] = useState<UserSkill[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [mode, setMode] = useState<'list' | 'edit'>('list');
  const [editName, setEditName] = useState('');
  const [editContent, setEditContent] = useState('');
  const [isNew, setIsNew] = useState(false);
  const [saving, setSaving] = useState(false);
  const [busyName, setBusyName] = useState<string | null>(null);

  const loadSkills = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch('/user-skills');
      if (!res.ok) throw new Error(`Failed to load (${res.status})`);
      const data = await res.json();
      setSkills(data.skills || []);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to load personal skills.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadSkills();
  }, [loadSkills]);

  const startCreate = () => {
    setIsNew(true);
    setEditName('');
    setEditContent(NEW_SKILL_TEMPLATE);
    setError(null);
    setMode('edit');
  };

  const startEdit = async (name: string) => {
    setBusyName(name);
    setError(null);
    try {
      const res = await fetch(`/user-skills/${encodeURIComponent(name)}`);
      if (!res.ok) throw new Error(`Failed to open '${name}' (${res.status})`);
      const data = await res.json();
      setIsNew(false);
      setEditName(data.name);
      setEditContent(data.content || '');
      setMode('edit');
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to open skill.');
    } finally {
      setBusyName(null);
    }
  };

  const saveSkill = async () => {
    const name = editName.trim();
    if (!name) {
      setError('Please give the skill a name.');
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const res = await fetch('/user-skills', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, content: editContent }),
      });
      if (!res.ok) {
        const detail = await res.json().catch(() => null);
        throw new Error(detail?.detail || `Failed to save (${res.status})`);
      }
      setMode('list');
      await loadSkills();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to save skill.');
    } finally {
      setSaving(false);
    }
  };

  const deleteSkill = async (name: string) => {
    if (!window.confirm(`Delete personal skill "${name}"? This cannot be undone.`)) return;
    setBusyName(name);
    setError(null);
    try {
      const res = await fetch(`/user-skills/${encodeURIComponent(name)}`, { method: 'DELETE' });
      if (!res.ok) throw new Error(`Failed to delete '${name}' (${res.status})`);
      await loadSkills();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to delete skill.');
    } finally {
      setBusyName(null);
    }
  };

  return (
    <div className="mt-8 bg-white border border-gray-200 rounded-lg p-6 shadow-sm shrink-0">
      <div className="flex items-center mb-4 border-b border-gray-100 pb-4">
        <div className="w-10 h-10 bg-[#F5F7FF] text-[#3253DC] rounded-md flex items-center justify-center mr-3 border border-[#3253DC]/20">
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"></path></svg>
        </div>
        <div>
          <h3 className="font-bold text-lg text-[#00205B]">My Personal Skills</h3>
          <p className="text-xs text-gray-500">Private SOPs stored in your workspace folder &middot; always available to the agent</p>
        </div>
        <span className="ml-auto bg-gray-100 text-gray-600 font-bold px-2 py-0.5 rounded text-xs mr-3">{skills.length}</span>
        {mode === 'list' && (
          <button
            onClick={startCreate}
            className="inline-flex items-center gap-1 bg-[#3253DC] hover:bg-[#00205B] text-white text-sm font-semibold px-3 py-1.5 rounded-md transition-colors focus:outline-none"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 4v16m8-8H4"></path></svg>
            New Skill
          </button>
        )}
      </div>

      {error && (
        <div className="mb-4 text-sm text-[#E32029] bg-red-50 border border-red-200 rounded-md px-3 py-2">{error}</div>
      )}

      {mode === 'edit' ? (
        <div className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-gray-600 mb-1">Skill name</label>
            <input
              type="text"
              value={editName}
              onChange={(e) => setEditName(e.target.value)}
              disabled={!isNew}
              placeholder="e.g. analyze_safety_stock"
              className="w-full px-3 py-2 border border-gray-200 rounded-md focus:outline-none focus:ring-2 focus:ring-[#3253DC] focus:border-transparent text-sm font-mono disabled:bg-gray-100 disabled:text-gray-500"
            />
            <p className="text-[11px] text-gray-400 mt-1">Letters, numbers, dashes and underscores. Saved as <code>&lt;name&gt;.md</code> in your workspace folder.</p>
          </div>
          <div>
            <label className="block text-xs font-semibold text-gray-600 mb-1">Instructions (Markdown)</label>
            <textarea
              value={editContent}
              onChange={(e) => setEditContent(e.target.value)}
              rows={14}
              className="w-full px-3 py-2 border border-gray-200 rounded-md focus:outline-none focus:ring-2 focus:ring-[#3253DC] focus:border-transparent text-sm font-mono resize-y"
            />
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={saveSkill}
              disabled={saving}
              className="bg-[#3253DC] hover:bg-[#00205B] text-white text-sm font-semibold px-4 py-2 rounded-md transition-colors focus:outline-none disabled:opacity-60"
            >
              {saving ? 'Saving…' : 'Save Skill'}
            </button>
            <button
              onClick={() => { setMode('list'); setError(null); }}
              className="text-gray-500 hover:text-[#00205B] text-sm font-medium px-4 py-2 rounded-md hover:bg-gray-100 transition-colors focus:outline-none"
            >
              Cancel
            </button>
          </div>
        </div>
      ) : loading ? (
        <div className="flex items-center justify-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#3253DC]"></div>
        </div>
      ) : skills.length === 0 ? (
        <div className="text-center py-8">
          <p className="text-gray-400 text-sm">You haven't created any personal skills yet.</p>
          <p className="text-gray-400 text-xs mt-1">Click <span className="font-semibold text-[#3253DC]">New Skill</span> to add reusable instructions just for you.</p>
        </div>
      ) : (
        <div className="space-y-2">
          {skills.map((skill) => (
            <div key={skill.name} className="flex items-center bg-gray-50 border border-gray-100 rounded-md p-3 hover:border-[#3253DC]/30 transition-colors">
              <svg className="w-4 h-4 text-[#3253DC] mr-3 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg>
              <div className="flex-1 min-w-0">
                <div className="font-mono text-sm text-gray-800 truncate">{skill.name}</div>
                <div className="text-xs text-gray-500 truncate">{skill.description}</div>
              </div>
              <div className="flex items-center gap-1 shrink-0 ml-3">
                <button
                  onClick={() => startEdit(skill.name)}
                  disabled={busyName === skill.name}
                  className="text-xs font-medium text-[#3253DC] hover:bg-[#F5F7FF] px-3 py-1.5 rounded-md transition-colors focus:outline-none disabled:opacity-60"
                >
                  Edit
                </button>
                <button
                  onClick={() => deleteSkill(skill.name)}
                  disabled={busyName === skill.name}
                  className="text-xs font-medium text-gray-400 hover:text-[#E32029] hover:bg-red-50 px-3 py-1.5 rounded-md transition-colors focus:outline-none disabled:opacity-60"
                >
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default UserSkillsManager;
