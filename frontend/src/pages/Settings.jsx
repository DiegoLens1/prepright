import { useState, useEffect } from "react";
import axios from "axios";

export default function SettingsPage({ API }) {
  const [settings, setSettings] = useState({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    axios.get(`${API}/settings`).then((res) => {
      setSettings(res.data);
      setLoading(false);
    });
  }, [API]);

  const update = async (key, value) => {
    await axios.put(`${API}/settings/${key}`, { value });
    setSettings((prev) => ({ ...prev, [key]: value }));
  };

  if (loading) return <p className="text-gray-500">Loading...</p>;

  return (
    <div>
      <h2 className="text-lg font-semibold mb-4">Settings</h2>

      <div className="space-y-4">
        {/* Weather condition */}
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <h3 className="font-medium mb-2">Current Weather</h3>
          <select
            className="border rounded px-3 py-2 text-sm"
            value={settings.weather_condition || "normal"}
            onChange={(e) => update("weather_condition", e.target.value)}
          >
            <option value="normal">☀️ Normal</option>
            <option value="rainy">🌧️ Rainy</option>
            <option value="cold">❄️ Cold</option>
            <option value="hot">🌞 Hot</option>
          </select>
          <p className="text-xs text-gray-500 mt-2">
            This affects predictions per category weather sensitivity.
          </p>
        </div>

        {/* Default margin */}
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <h3 className="font-medium mb-2">Default Margin %</h3>
          <input
            className="border rounded px-3 py-2 text-sm w-32"
            type="number"
            value={settings.default_margin_pct || 20}
            onChange={(e) => update("default_margin_pct", e.target.value)}
          />
          <p className="text-xs text-gray-500 mt-2">
            Used as default when creating new products.
          </p>
        </div>

        {/* Prediction weeks */}
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <h3 className="font-medium mb-2">Prediction Lookback Weeks</h3>
          <input
            className="border rounded px-3 py-2 text-sm w-32"
            type="number"
            value={settings.prediction_weeks || 4}
            onChange={(e) => update("prediction_weeks", e.target.value)}
          />
          <p className="text-xs text-gray-500 mt-2">
            How many weeks of history to use for predictions.
          </p>
        </div>
      </div>
    </div>
  );
}
