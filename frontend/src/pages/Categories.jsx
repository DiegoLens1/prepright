import { useState, useEffect } from "react";
import axios from "axios";

export default function Categories({ API }) {
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(null);
  const [showForm, setShowForm] = useState(false);

  const [name, setName] = useState("");
  const [sensitivity, setSensitivity] = useState(1.0);

  useEffect(() => {
    axios.get(`${API}/categories`).then((res) => {
      setCategories(res.data);
      setLoading(false);
    });
  }, [API]);

  const openCreate = () => {
    setEditing(null);
    setName("");
    setSensitivity(1.0);
    setShowForm(true);
  };

  const openEdit = (cat) => {
    setEditing(cat);
    setName(cat.name);
    setSensitivity(cat.weather_sensitivity);
    setShowForm(true);
  };

  const saveCategory = async () => {
    const data = { name, weather_sensitivity: sensitivity };
    if (editing) {
      const res = await axios.put(`${API}/categories/${editing.id}`, data);
      setCategories((prev) => prev.map((c) => (c.id === res.data.id ? res.data : c)));
    } else {
      const res = await axios.post(`${API}/categories`, data);
      setCategories((prev) => [...prev, res.data]);
    }
    setShowForm(false);
  };

  const toggleActive = async (cat) => {
    await axios.put(`${API}/categories/${cat.id}`, { active: !cat.active });
    setCategories((prev) =>
      prev.map((c) => (c.id === cat.id ? { ...c, active: !c.active } : c))
    );
  };

  const deleteCategory = async (id) => {
    if (!confirm("Delete this category? Products in it will become inactive.")) return;
    await axios.delete(`${API}/categories/${id}`);
    setCategories((prev) => prev.filter((c) => c.id !== id));
  };

  // Sensitivity explanation
  const sensitivityHelp = {
    0.5: "50% reduction in bad weather",
    0.75: "25% reduction in bad weather",
    0.85: "15% reduction in bad weather",
    1.0: "No weather adjustment",
    1.15: "15% increase in good weather",
    1.5: "50% increase in good weather",
  };

  if (loading) return <p className="text-gray-500">Loading...</p>;

  return (
    <div>
      <div className="flex items-center justify-between mb-4 no-print">
        <h2 className="text-lg font-semibold">Categories</h2>
        <button
          onClick={openCreate}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700"
        >
          + Add Category
        </button>
      </div>

      {showForm && (
        <div className="bg-white border border-gray-200 rounded-lg p-4 mb-4 no-print">
          <h3 className="font-medium mb-3">{editing ? "Edit" : "Add"} Category</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-gray-500 mb-1">Name *</label>
              <input
                className="w-full border rounded px-3 py-2 text-sm"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Baked Goods"
              />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">
                Weather Sensitivity ({sensitivityHelp[sensitivity] || "Custom"})
              </label>
              <input
                className="w-full border rounded px-3 py-2 text-sm"
                type="range"
                min="0.1"
                max="2.0"
                step="0.05"
                value={sensitivity}
                onChange={(e) => setSensitivity(Number(e.target.value))}
              />
              <div className="flex justify-between text-xs text-gray-400 mt-1">
                <span>0.1 (−90%)</span>
                <span className="font-medium text-gray-600">{sensitivity}</span>
                <span>2.0 (+100%)</span>
              </div>
            </div>
          </div>
          <div className="flex gap-2 mt-4">
            <button
              onClick={saveCategory}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700"
            >
              {editing ? "Save" : "Create"}
            </button>
            <button
              onClick={() => setShowForm(false)}
              className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-300"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th className="text-left px-4 py-2 font-medium text-gray-600">Name</th>
              <th className="text-left px-4 py-2 font-medium text-gray-600">Weather Effect</th>
              <th className="text-center px-4 py-2 font-medium text-gray-600">Active</th>
              <th className="text-right px-4 py-2 font-medium text-gray-600 no-print">Actions</th>
            </tr>
          </thead>
          <tbody>
            {categories.map((c) => (
              <tr key={c.id} className="border-b border-gray-100 hover:bg-gray-50">
                <td className="px-4 py-2 font-medium">{c.name}</td>
                <td className="px-4 py-2">
                  <span
                    className={`text-xs px-2 py-0.5 rounded ${
                      c.weather_sensitivity < 1
                        ? "bg-orange-50 text-orange-700"
                        : c.weather_sensitivity > 1
                        ? "bg-green-50 text-green-700"
                        : "bg-gray-100 text-gray-600"
                    }`}
                  >
                    ×{c.weather_sensitivity.toFixed(2)}
                  </span>
                </td>
                <td className="px-4 py-2 text-center">
                  <button
                    onClick={() => toggleActive(c)}
                    className={`w-8 h-5 rounded-full text-xs font-medium transition-colors ${
                      c.active ? "bg-green-500 text-white" : "bg-gray-200 text-gray-600"
                    }`}
                  >
                    {c.active ? "ON" : "OFF"}
                  </button>
                </td>
                <td className="px-4 py-2 text-right no-print">
                  <button
                    onClick={() => openEdit(c)}
                    className="text-primary hover:underline text-sm mr-3"
                  >
                    Edit
                  </button>
                  <button
                    onClick={() => deleteCategory(c.id)}
                    className="text-danger hover:underline text-sm"
                  >
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {categories.length === 0 && (
          <p className="text-center text-gray-400 py-8">No categories yet.</p>
        )}
      </div>
    </div>
  );
}
