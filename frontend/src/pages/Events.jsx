import { useState, useEffect } from "react";
import axios from "axios";

export default function Events({ API }) {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(null);
  const [showForm, setShowForm] = useState(false);

  const [date, setDate] = useState("");
  const [name, setName] = useState("");
  const [impact, setImpact] = useState(0);

  useEffect(() => {
    axios.get(`${API}/events`).then((res) => {
      setEvents(res.data);
      setLoading(false);
    });
  }, [API]);

  const openCreate = () => {
    setEditing(null);
    setDate("");
    setName("");
    setImpact(0);
    setShowForm(true);
  };

  const openEdit = (evt) => {
    setEditing(evt);
    setDate(evt.date);
    setName(evt.name);
    setImpact(evt.impact_factor);
    setShowForm(true);
  };

  const saveEvent = async () => {
    const data = { date, name, impact_factor: impact };
    if (editing) {
      const res = await axios.put(`${API}/events/${editing.id}`, data);
      setEvents((prev) => prev.map((e) => (e.id === res.data.id ? res.data : e)));
    } else {
      const res = await axios.post(`${API}/events`, data);
      setEvents((prev) => [...prev, res.data]);
    }
    setShowForm(false);
  };

  const deleteEvent = async (id) => {
    if (!confirm("Remove this event?")) return;
    await axios.delete(`${API}/events/${id}`);
    setEvents((prev) => prev.filter((e) => e.id !== id));
  };

  if (loading) return <p className="text-gray-500">Loading...</p>;

  return (
    <div>
      <div className="flex items-center justify-between mb-4 no-print">
        <h2 className="text-lg font-semibold">Special Events</h2>
        <button
          onClick={openCreate}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700"
        >
          + Add Event
        </button>
      </div>

      {showForm && (
        <div className="bg-white border border-gray-200 rounded-lg p-4 mb-4 no-print">
          <h3 className="font-medium mb-3">{editing ? "Edit" : "Add"} Event</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div>
              <label className="block text-xs text-gray-500 mb-1">Date *</label>
              <input
                className="w-full border rounded px-3 py-2 text-sm"
                type="date"
                value={date}
                onChange={(e) => setDate(e.target.value)}
              />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Event Name *</label>
              <input
                className="w-full border rounded px-3 py-2 text-sm"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. School Fair"
              />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">
                Impact ({impact >= 0 ? "+" : ""}
                {Math.round(impact * 100)}%)
              </label>
              <input
                className="w-full border rounded px-3 py-2 text-sm"
                type="range"
                min="-0.5"
                max="0.5"
                step="0.05"
                value={impact}
                onChange={(e) => setImpact(Number(e.target.value))}
              />
              <div className="flex justify-between text-xs text-gray-500 mt-1">
                <span>−50%</span>
                <span>0%</span>
                <span>+50%</span>
              </div>
            </div>
          </div>
          <div className="flex gap-2 mt-4">
            <button
              onClick={saveEvent}
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
              <th className="text-left px-4 py-2 font-medium text-gray-600">Date</th>
              <th className="text-left px-4 py-2 font-medium text-gray-600">Event</th>
              <th className="text-left px-4 py-2 font-medium text-gray-600">Impact</th>
              <th className="text-right px-4 py-2 font-medium text-gray-600 no-print">Actions</th>
            </tr>
          </thead>
          <tbody>
            {events.map((evt) => (
              <tr key={evt.id} className="border-b border-gray-100 hover:bg-gray-50">
                <td className="px-4 py-2 font-mono text-gray-600">{evt.date}</td>
                <td className="px-4 py-2 font-medium">{evt.name}</td>
                <td className="px-4 py-2">
                  <span
                    className={`text-xs px-2 py-0.5 rounded ${
                      evt.impact_factor > 0
                        ? "bg-green-50 text-green-700"
                        : evt.impact_factor < 0
                        ? "bg-red-50 text-red-700"
                        : "bg-gray-100 text-gray-600"
                    }`}
                  >
                    {evt.impact_factor >= 0 ? "+" : ""}
                    {Math.round(evt.impact_factor * 100)}%
                  </span>
                </td>
                <td className="px-4 py-2 text-right no-print">
                  <button
                    onClick={() => openEdit(evt)}
                    className="text-primary hover:underline text-sm mr-3"
                  >
                    Edit
                  </button>
                  <button
                    onClick={() => deleteEvent(evt.id)}
                    className="text-danger hover:underline text-sm"
                  >
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {events.length === 0 && (
          <p className="text-center text-gray-400 py-8">No events yet. Add special days that will impact sales.</p>
        )}
      </div>
    </div>
  );
}
