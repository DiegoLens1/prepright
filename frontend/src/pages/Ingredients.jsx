import { useState, useEffect } from "react";
import axios from "axios";
import ConfirmModal from "../components/ConfirmModal";

export default function Ingredients({ API }) {
  const [ingredients, setIngredients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [confirmState, setConfirmState] = useState(null);

  const [name, setName] = useState("");
  const [unit, setUnit] = useState("units");

  useEffect(() => {
    axios.get(`${API}/ingredients`).then((res) => {
      setIngredients(res.data);
      setLoading(false);
    });
  }, [API]);

  const openCreate = () => {
    setEditing(null);
    setName("");
    setUnit("units");
    setShowForm(true);
  };

  const openEdit = (ing) => {
    setEditing(ing);
    setName(ing.name);
    setUnit(ing.unit);
    setShowForm(true);
  };

  const saveIngredient = async () => {
    const data = { name, unit };
    if (editing) {
      const res = await axios.put(`${API}/ingredients/${editing.id}`, data);
      setIngredients((prev) => prev.map((i) => (i.id === res.data.id ? res.data : i)));
    } else {
      const res = await axios.post(`${API}/ingredients`, data);
      setIngredients((prev) => [...prev, res.data]);
    }
    setShowForm(false);
  };

  const toggleActive = async (ing) => {
    await axios.put(`${API}/ingredients/${ing.id}`, { active: !ing.active });
    setIngredients((prev) =>
      prev.map((i) => (i.id === ing.id ? { ...i, active: !i.active } : i))
    );
  };

  const deleteIngredient = (id) => {
    setConfirmState({ id, message: "Delete this ingredient?" });
  };

  const confirmDelete = async (confirmed) => {
    setConfirmState(null);
    if (!confirmed) return;
    await axios.delete(`${API}/ingredients/${confirmState.id}`);
    setIngredients((prev) => prev.filter((i) => i.id !== confirmState.id));
  };

  if (loading) return <p className="text-gray-500">Loading...</p>;

  return (
    <div>
      <div className="flex items-center justify-between mb-4 no-print">
        <h2 className="text-lg font-semibold">Ingredients</h2>
        <button
          onClick={openCreate}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700"
        >
          + Add Ingredient
        </button>
      </div>

      {showForm && (
        <div className="bg-white border border-gray-200 rounded-lg p-4 mb-4 no-print">
          <h3 className="font-medium mb-3">{editing ? "Edit" : "Add"} Ingredient</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-gray-500 mb-1">Name *</label>
              <input
                className="w-full border rounded px-3 py-2 text-sm"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. bread"
              />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Unit</label>
              <select
                className="w-full border rounded px-3 py-2 text-sm"
                value={unit}
                onChange={(e) => setUnit(e.target.value)}
              >
                <option value="units">units</option>
                <option value="kg">kg</option>
                <option value="g">g</option>
                <option value="liters">liters</option>
                <option value="ml">ml</option>
                <option value="pieces">pieces</option>
              </select>
            </div>
          </div>
          <div className="flex gap-2 mt-4">
            <button
              onClick={saveIngredient}
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
              <th className="text-left px-4 py-2 font-medium text-gray-600">Unit</th>
              <th className="text-center px-4 py-2 font-medium text-gray-600">Active</th>
              <th className="text-right px-4 py-2 font-medium text-gray-600 no-print">Actions</th>
            </tr>
          </thead>
          <tbody>
            {ingredients.map((ing) => (
              <tr key={ing.id} className="border-b border-gray-100 hover:bg-gray-50">
                <td className="px-4 py-2 font-medium">{ing.name}</td>
                <td className="px-4 py-2 text-gray-600">{ing.unit}</td>
                <td className="px-4 py-2 text-center">
                  <button
                    onClick={() => toggleActive(ing)}
                    className={`w-8 h-5 rounded-full text-xs font-medium transition-colors ${
                      ing.active ? "bg-green-500 text-white" : "bg-gray-200 text-gray-600"
                    }`}
                  >
                    {ing.active ? "ON" : "OFF"}
                  </button>
                </td>
                <td className="px-4 py-2 text-right no-print">
                  <button
                    onClick={() => openEdit(ing)}
                    className="text-blue-600 hover:underline text-sm mr-3"
                  >
                    Edit
                  </button>
                  <button
                    onClick={() => deleteIngredient(ing.id)}
                    className="text-red-600 hover:underline text-sm"
                  >
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {ingredients.length === 0 && (
          <p className="text-center text-gray-500 py-8">No ingredients yet.</p>
        )}
      </div>

      {/* Confirmation modal */}
      <ConfirmModal
        isOpen={!!confirmState}
        title="Confirm Delete"
        message={confirmState?.message || "Are you sure?"}
        confirmLabel="Delete"
        onConfirm={confirmDelete}
      />
    </div>
  );
}
