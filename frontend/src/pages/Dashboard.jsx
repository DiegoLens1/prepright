import { useState, useEffect } from "react";
import axios from "axios";

export default function Dashboard({ API, setPage }) {
  const [stats, setStats] = useState({ products: 0, categories: 0, ingredients: 0, predictions: 0 });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      axios.get(`${API}/products`),
      axios.get(`${API}/categories`),
      axios.get(`${API}/ingredients`),
      axios.get(`${API}/predictions`),
    ]).then(([p, c, i, pred]) => {
      setStats({
        products: p.data.length,
        categories: c.data.length,
        ingredients: i.data.length,
        predictions: pred.data.length,
      });
      setLoading(false);
    });
  }, [API]);

  if (loading) return <p className="text-gray-500">Loading...</p>;

  return (
    <div>
      <div className="mb-8">
        <h2 className="text-2xl font-bold text-gray-800">Dashboard</h2>
        <p className="text-sm text-gray-500 mt-1">
          Overview of your shop and quick actions
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <p className="text-xs text-gray-400 uppercase tracking-wider">Products</p>
          <p className="text-3xl font-bold text-gray-800 mt-1">{stats.products}</p>
        </div>
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <p className="text-xs text-gray-400 uppercase tracking-wider">Categories</p>
          <p className="text-3xl font-bold text-gray-800 mt-1">{stats.categories}</p>
          <p className="text-xs text-gray-400 mt-1">Product groups</p>
        </div>
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <p className="text-xs text-gray-400 uppercase tracking-wider">Ingredients</p>
          <p className="text-3xl font-bold text-gray-800 mt-1">{stats.ingredients}</p>
          <p className="text-xs text-gray-400 mt-1">Trackable items</p>
        </div>
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <p className="text-xs text-gray-400 uppercase tracking-wider">Predictions</p>
          <p className="text-3xl font-bold text-gray-800 mt-1">{stats.predictions}</p>
          <p className="text-xs text-gray-400 mt-1">Forecast entries</p>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="mb-8">
        <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-3">Quick Actions</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <button
            onClick={() => setPage("print-orders")}
            className="bg-gradient-to-br from-blue-500 to-blue-600 text-white rounded-xl p-6 text-left hover:from-blue-600 hover:to-blue-700 transition-all shadow-sm hover:shadow-md"
          >
            <div className="text-2xl mb-2">🖨️</div>
            <h4 className="font-semibold text-lg">Print Orders</h4>
            <p className="text-blue-100 text-sm mt-1">
              Compose and simulate print orders for demo
            </p>
          </button>
          <button
            onClick={() => setPage("predictions")}
            className="bg-gradient-to-br from-green-500 to-green-600 text-white rounded-xl p-6 text-left hover:from-green-600 hover:to-green-700 transition-all shadow-sm hover:shadow-md"
          >
            <div className="text-2xl mb-2">📊</div>
            <h4 className="font-semibold text-lg">View Predictions</h4>
            <p className="text-green-100 text-sm mt-1">
              Check demand forecasts for the week
            </p>
          </button>
          <button
            onClick={() => setPage("products")}
            className="bg-gradient-to-br from-purple-500 to-purple-600 text-white rounded-xl p-6 text-left hover:from-purple-600 hover:to-purple-700 transition-all shadow-sm hover:shadow-md"
          >
            <div className="text-2xl mb-2">📦</div>
            <h4 className="font-semibold text-lg">Manage Products</h4>
            <p className="text-purple-100 text-sm mt-1">
              Add or edit your product catalog
            </p>
          </button>
        </div>
      </div>
    </div>
  );
}
