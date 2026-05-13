import { useState, useEffect } from "react";

export default function Templates({ API }) {
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState(null);
  const [formData, setFormData] = useState({
    name: "",
    description: "",
    active: true,
    source_keyword: "",
    line_pattern: "",
    product_name_group: "name",
    quantity_group: "qty",
    price_group: "price",
    line_prefix: "",
    line_suffix: "",
    name_normalize: "",
    config: "",
  });

  const fetchTemplates = async () => {
    try {
      const res = await fetch(`${API}/templates`);
      const data = await res.json();
      setTemplates(data);
    } catch (e) {
      console.error("Failed to fetch templates:", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTemplates();
  }, []);

  const handleSave = async () => {
    const payload = {
      ...formData,
      source_keyword: formData.source_keyword || null,
      line_prefix: formData.line_prefix || null,
      line_suffix: formData.line_suffix || null,
      name_normalize: formData.name_normalize || null,
      config: formData.config || null,
    };

    try {
      if (editing) {
        const res = await fetch(`${API}/templates/${editing.id}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        if (res.ok) fetchTemplates();
      } else {
        const res = await fetch(`${API}/templates`, {
          method: "POST",
          headers: { "Content-Type" : "application/json" },
          body: JSON.stringify(payload),
        });
        if (res.ok) fetchTemplates();
      }
      setShowForm(false);
      setEditing(null);
      resetForm();
    } catch (e) {
      console.error("Failed to save template:", e);
    }
  };

  const handleDelete = async (id) => {
    if (!confirm("Delete this template?")) return;
    try {
      await fetch(`${API}/templates/${id}`, { method: "DELETE" });
      fetchTemplates();
    } catch (e) {
      console.error("Failed to delete:", e);
    }
  };

  const resetForm = () => {
    setFormData({
      name: "",
      description: "",
      active: true,
      source_keyword: "",
      line_pattern: "",
      product_name_group: "name",
      quantity_group: "qty",
      price_group: "price",
      line_prefix: "",
      line_suffix: "",
      name_normalize: "",
      config: "",
    });
  };

  const startEdit = (t) => {
    setEditing(t);
    setFormData({
      name: t.name,
      description: t.description || "",
      active: t.active,
      source_keyword: t.source_keyword || "",
      line_pattern: t.line_pattern,
      product_name_group: t.product_name_group,
      quantity_group: t.quantity_group,
      price_group: t.price_group,
      line_prefix: t.line_prefix || "",
      line_suffix: t.line_suffix || "",
      name_normalize: t.name_normalize || "",
      config: t.config || "",
    });
    setShowForm(true);
  };

  const toggleActive = async (t) => {
    await fetch(`${API}/templates/${t.id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ active: !t.active }),
    });
    fetchTemplates();
  };

  if (loading) return <div className="text-center py-12 text-gray-400">Loading...</div>;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold text-gray-800">Receipt Templates</h2>
          <p className="text-sm text-gray-500 mt-1">
            Define how to parse receipts from different POS systems
          </p>
        </div>
        <button
          onClick={() => { setShowForm(true); setEditing(null); resetForm(); }}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium"
        >
          + New Template
        </button>
      </div>

      {/* Form Modal */}
      {showForm && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <div className="p-6 border-b border-gray-200">
              <h3 className="text-lg font-semibold text-gray-800">
                {editing ? "Edit Template" : "New Template"}
              </h3>
            </div>
            <div className="p-6 space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Template Name <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    placeholder="e.g., HEMA, Cow Hills POS"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary/20 focus:border-primary"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Description
                  </label>
                  <input
                    type="text"
                    value={formData.description}
                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                    placeholder="e.g., HEMA thermal printer receipts"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary/20 focus:border-primary"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Source Keyword (auto-detect)
                </label>
                <input
                  type="text"
                  value={formData.source_keyword}
                  onChange={(e) => setFormData({ ...formData, source_keyword: e.target.value })}
                  placeholder="e.g., HEMA — will auto-match if this word appears in receipt"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary/20 focus:border-primary"
                />
                <p className="text-xs text-gray-500 mt-1">
                  Leave empty to skip auto-detection. The first active template will be used.
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Line Pattern (regex) <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={formData.line_pattern}
                  onChange={(e) => setFormData({ ...formData, line_pattern: e.target.value })}
                  placeholder='e.g., ^\\d{8}\\s+(.+?)\\s+(\\d+\\.\\d+)$'
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary/20 focus:border-primary font-mono text-sm"
                />
                <p className="text-xs text-gray-400 mt-1">
                  Regex pattern to match a product line. Use named groups: (?P&lt;name&gt;...), (?P&lt;qty&gt;...), (?P&lt;price&gt;...)
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Name Group
                  </label>
                  <input
                    type="text"
                    value={formData.product_name_group}
                    onChange={(e) => setFormData({ ...formData, product_name_group: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary/20 focus:border-primary font-mono text-sm"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Quantity Group
                  </label>
                  <input
                    type="text"
                    value={formData.quantity_group}
                    onChange={(e) => setFormData({ ...formData, quantity_group: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary/20 focus:border-primary font-mono text-sm"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Price Group
                  </label>
                  <input
                    type="text"
                    value={formData.price_group}
                    onChange={(e) => setFormData({ ...formData, price_group: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary/20 focus:border-primary font-mono text-sm"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Line Prefix (strip before matching)
                  </label>
                  <input
                    type="text"
                    value={formData.line_prefix}
                    onChange={(e) => setFormData({ ...formData, line_prefix: e.target.value })}
                    placeholder="e.g., '  '"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary/20 focus:border-primary"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Line Suffix (strip before matching)
                  </label>
                  <input
                    type="text"
                    value={formData.line_suffix}
                    onChange={(e) => setFormData({ ...formData, line_suffix: e.target.value })}
                    placeholder="e.g., '\\n'"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary/20 focus:border-primary"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Name Normalize (replace rules)
                </label>
                <input
                  type="text"
                  value={formData.name_normalize}
                  onChange={(e) => setFormData({ ...formData, name_normalize: e.target.value })}
                  placeholder='e.g., BD:Bak, klein:klein, normaal:normaal'
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary/20 focus:border-primary"
                />
                <p className="text-xs text-gray-400 mt-1">
                  Comma-separated replace rules: old:new,old2:new2. Applied after matching.
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Config (JSON)
                </label>
                <textarea
                  value={formData.config}
                  onChange={(e) => setFormData({ ...formData, config: e.target.value })}
                  placeholder='e.g., {"product_code_length": 8}'
                  rows={2}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary/20 focus:border-primary font-mono text-sm"
                />
              </div>

              <div className="flex items-center gap-3 pt-2">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={formData.active}
                    onChange={(e) => setFormData({ ...formData, active: e.target.checked })}
                    className="w-4 h-4 text-primary border-gray-300 rounded focus:ring-primary"
                  />
                  <span className="text-sm text-gray-700">Active</span>
                </label>
              </div>
            </div>
            <div className="p-6 border-t border-gray-200 flex justify-end gap-3">
              <button
                onClick={() => { setShowForm(false); setEditing(null); resetForm(); }}
                className="px-4 py-2 text-gray-700 hover:bg-gray-200 rounded-lg transition-colors text-sm"
              >
                Cancel
              </button>
              <button
                onClick={handleSave}
                disabled={!formData.name || !formData.line_pattern}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium disabled:opacity-50"
              >
                {editing ? "Update" : "Create"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Templates List */}
      <div className="space-y-3">
        {templates.map((t) => (
          <div
            key={t.id}
            className={`bg-white rounded-xl border p-5 transition-all ${
              t.active ? "border-gray-200 shadow-sm" : "border-gray-100 opacity-60"
            }`}
          >
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-2">
                  <h3 className="text-lg font-semibold text-gray-800">{t.name}</h3>
                  <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                    t.active ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"
                  }`}>
                    {t.active ? "Active" : "Inactive"}
                  </span>
                </div>
                {t.description && (
                  <p className="text-sm text-gray-500 mb-2">{t.description}</p>
                )}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-2 text-xs text-gray-500">
                  <div>
                    <span className="font-medium text-gray-500">Keyword:</span>{" "}
                    {t.source_keyword || "—"}
                  </div>
                  <div>
                    <span className="font-medium text-gray-500">Pattern:</span>{" "}
                    <code className="bg-gray-50 px-1 rounded">{t.line_pattern}</code>
                  </div>
                  <div>
                    <span className="font-medium text-gray-500">Groups:</span>{" "}
                    name={t.product_name_group} qty={t.quantity_group} price={t.price_group}
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-2 ml-4">
                <button
                  onClick={() => toggleActive(t)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                    t.active
                      ? "bg-gray-100 text-gray-600 hover:bg-gray-200"
                      : "bg-green-100 text-green-700 hover:bg-green-200"
                  }`}
                >
                  {t.active ? "Disable" : "Enable"}
                </button>
                <button
                  onClick={() => startEdit(t)}
                  className="px-3 py-1.5 bg-primary/10 text-primary rounded-lg hover:bg-primary/20 transition-colors text-xs font-medium"
                >
                  Edit
                </button>
                <button
                  onClick={() => handleDelete(t.id)}
                  className="px-3 py-1.5 bg-red-50 text-red-600 rounded-lg hover:bg-red-100 transition-colors text-xs font-medium"
                >
                  Delete
                </button>
              </div>
            </div>
          </div>
        ))}

        {templates.length === 0 && (
          <div className="text-center py-12 bg-white rounded-xl border border-gray-200">
            <p className="text-gray-400">No templates yet. Create your first one!</p>
          </div>
        )}
      </div>

      {/* Help section */}
      <div className="mt-8 bg-amber-50 border border-amber-200 rounded-xl p-5">
        <h4 className="font-semibold text-amber-800 mb-2">Quick Start: HEMA Template</h4>
        <p className="text-sm text-amber-700 mb-3">
          For HEMA receipts, use these settings:
        </p>
        <div className="bg-white rounded-lg p-4 font-mono text-xs text-gray-700 overflow-x-auto">
          <pre>{`Name: HEMA
Source Keyword: HEMA
Line Pattern: ^\\d{8}\\s+(.+?)\\s+(\\d+\\.\\d+)$
Name Group: name
Quantity Group: qty (defaults to 1 if not found)
Price Group: price`}</pre>
        </div>
        <p className="text-sm text-amber-700 mt-3">
          <strong>How it works:</strong> Each product line in a HEMA receipt looks like:<br/>
          <code>28102360 Koffie klein 2.59</code><br/>
          The regex captures: <code>28102360</code> (code), <code>Koffie klein</code> (name), <code>2.59</code> (price)
        </p>
      </div>
    </div>
  );
}
