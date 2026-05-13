import { useState, useEffect } from "react";
import axios from "axios";

const DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

function getMonday(d) {
  const date = new Date(d);
  const day = date.getDay();
  const diff = date.getDate() - day + (day === 0 ? -6 : 1);
  return new Date(date.setDate(diff));
}

function addDays(d, n) {
  const date = new Date(d);
  date.setDate(date.getDate() + n);
  return date;
}

function fmt(d) {
  return d.toISOString().split("T")[0];
}

function fmtShort(d) {
  return `${d.getMonth() + 1}/${d.getDate()}`;
}



export default function Predictions({ API }) {
  const [predictions, setPredictions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [products, setProducts] = useState([]);

  // Single source of truth: currentMonday
  const [currentMonday, setCurrentMonday] = useState(() =>
    getMonday(new Date())
  );

  // Filter
  const [productFilter, setProductFilter] = useState("");

  // Category order
  const [categories, setCategories] = useState([]);

  useEffect(() => {
    Promise.all([
      axios.get(`${API}/products`),
      axios.get(`${API}/predictions`),
      axios.get(`${API}/categories`),
    ]).then(([pRes, predRes, catRes]) => {
      setProducts(pRes.data);
      setPredictions(predRes.data);
      setCategories(catRes.data);
      setLoading(false);
    });
  }, [API]);

  const goPrev = () => setCurrentMonday(addDays(currentMonday, -7));
  const goNext = () => setCurrentMonday(addDays(currentMonday, 7));
  const goToday = () => setCurrentMonday(getMonday(new Date()));

  // Week range
  const weekStart = currentMonday;
  const weekEnd = addDays(currentMonday, 6);
  const weekDates = Array.from({ length: 7 }, (_, i) => addDays(weekStart, i));

  const generate = async () => {
    setGenerating(true);
    try {
      await axios.post(`${API}/predictions/generate`, {
        start_date: fmt(weekStart),
        end_date: fmt(weekEnd),
      });
      const res = await axios.get(
        `${API}/predictions?start_date=${fmt(weekStart)}&end_date=${fmt(weekEnd)}`
      );
      setPredictions(res.data);
    } catch (err) {
      alert(err.response?.data?.detail || "Failed to generate predictions");
    } finally {
      setGenerating(false);
    }
  };

  const exportPDF = async () => {
    setExporting(true);
    try {
      const res = await axios.get(`${API}/predictions/export/pdf`, {
        params: {
          start_date: fmt(weekStart),
          end_date: fmt(weekEnd),
        },
        responseType: "json",
      });

      const hex = res.data.pdf_base64;
      const bytes = new Uint8Array(hex.length / 2);
      for (let i = 0; i < hex.length; i += 2) {
        bytes[i / 2] = parseInt(hex.substr(i, 2), 16);
      }
      const blob = new Blob([bytes], { type: "application/pdf" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = res.data.filename;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      alert(err.response?.data?.error || "Failed to export PDF");
    } finally {
      setExporting(false);
    }
  };

  if (loading) return <p className="text-gray-500">Loading...</p>;

  // Build lookup: (date, product_id) -> prediction
  const predLookup = {};
  predictions.forEach((p) => {
    predLookup[`${p.date}-${p.product_id}`] = p;
  });



  // Group products by category
  const productsByCategory = {};
  categories.forEach((cat) => {
    productsByCategory[cat.name] = [];
  });
  products.forEach((prod) => {
    const catName = prod.category_name || "Other";
    if (!productsByCategory[catName]) productsByCategory[catName] = [];
    productsByCategory[catName].push(prod);
  });

  // Filter products
  const filteredByCategory = {};
  Object.entries(productsByCategory).forEach(([catName, prods]) => {
    const filtered = productFilter
      ? prods.filter((p) => p.id === Number(productFilter))
      : prods;
    if (filtered.length > 0) {
      filteredByCategory[catName] = filtered;
    }
  });

  return (
    <div>
      <div className="flex items-center justify-between mb-6 no-print">
        <div>
          <h2 className="text-2xl font-bold text-gray-800">Predictions</h2>
          <p className="text-sm text-gray-500 mt-1">
            Forecasted daily demand based on historical sales, weather, and events
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={generate}
            disabled={generating}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm font-medium disabled:opacity-50"
          >
            {generating ? "Generating..." : "Generate Predictions"}
          </button>
          <button
            onClick={exportPDF}
            disabled={exporting || predictions.length === 0}
            className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 text-sm font-medium disabled:opacity-50"
          >
            {exporting ? "Exporting..." : "Export PDF"}
          </button>
        </div>
      </div>

      {/* Week navigation */}
      <div className="bg-white border border-gray-200 rounded-lg p-4 mb-6 no-print">
        <div className="flex flex-wrap items-center gap-4">
          <div className="flex items-center gap-2">
            <button
              onClick={goPrev}
              className="px-3 py-1.5 bg-gray-200 text-gray-800 rounded text-sm font-medium hover:bg-gray-300"
            >
              ← Prev
            </button>
            <button
              onClick={goToday}
              className="px-3 py-1.5 bg-gray-200 text-gray-800 rounded text-sm font-medium hover:bg-gray-300"
            >
              Today
            </button>
            <button
              onClick={goNext}
              className="px-3 py-1.5 bg-gray-200 text-gray-800 rounded text-sm font-medium hover:bg-gray-300"
            >
              Next →
            </button>
          </div>
          <div className="flex items-center gap-2 text-sm text-gray-600">
            <input
              type="date"
              value={fmt(currentMonday)}
              onChange={(e) => setCurrentMonday(getMonday(new Date(e.target.value)))}
              className="border rounded px-2 py-1.5 text-sm"
            />
          </div>
          <div className="flex-1" />
          <div>
            <label className="block text-xs text-gray-500 mb-1">Filter Product</label>
            <select
              value={productFilter}
              onChange={(e) => setProductFilter(e.target.value)}
              className="border rounded px-3 py-2 text-sm"
            >
              <option value="">All Products</option>
              {products.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Tables grouped by category */}
      {Object.keys(filteredByCategory).length === 0 ? (
        <div className="bg-white border border-gray-200 rounded-lg p-12 text-center">
          <p className="text-gray-400">
            No predictions for this week. Click "Generate Predictions" to create forecasts.
          </p>
        </div>
      ) : (
        <div className="space-y-6">
          {Object.entries(filteredByCategory).map(([catName, prods]) => (
            <div key={catName} className="bg-white border border-gray-200 rounded-lg overflow-hidden">
              <div className="px-4 py-3 bg-gray-50 border-b border-gray-200">
                <h3 className="font-semibold text-gray-800">{catName}</h3>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-gray-100">
                      <th className="text-left px-3 py-2 font-medium text-gray-600 sticky left-0 bg-gray-100 z-10" style={{ minWidth: 140 }}>
                        Product
                      </th>
                      {weekDates.map((day, i) => (
                        <th
                          key={i}
                          className={`text-center px-2 py-2 font-medium ${
                            i >= 5 ? "text-red-400" : "text-gray-600"
                          }`}
                          style={{ minWidth: 60 }}
                        >
                          <div>{DAY_NAMES[i]}</div>
                          <div className="text-xs font-normal text-gray-500">{fmtShort(day)}</div>
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {prods.map((prod) => (
                      <tr key={prod.id} className="border-b border-gray-100 hover:bg-gray-50">
                        <td
                          className="px-3 py-2 font-medium sticky left-0 bg-white z-10"
                          style={{ minWidth: 140 }}
                        >
                          {prod.name}
                        </td>
                        {weekDates.map((day, i) => {
                          const key = `${fmt(day)}-${prod.id}`;
                          const pred = predLookup[key];
                          if (!pred) {
                            return (
                              <td key={i} className="text-center px-2 py-2 text-gray-400">
                                —
                              </td>
                            );
                          }
                          return (
                            <td key={i} className="text-center px-2 py-2">
                              <div className="font-mono font-semibold">{Math.ceil(pred.predicted_qty)}</div>
                            </td>
                          );
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Summary */}
      <div className="mt-6 text-sm text-gray-500">
        Showing {predictions.length} predictions for the week of {fmt(weekStart)}
      </div>

      {/* Help section */}
      <div className="mt-6 bg-blue-50 border border-blue-200 rounded-xl p-5">
        <h4 className="font-semibold text-blue-800 mb-2">How Predictions Work</h4>
        <div className="text-sm text-blue-700 space-y-2">
          <p>
            <strong>Base quantity</strong> — Average daily sales calculated from historical receipt data (configurable lookback weeks).
          </p>
          <p>
            <strong>Weather adjustment</strong> — Applied per category sensitivity (see Categories tab).
          </p>
          <p>
            <strong>Event adjustment</strong> — Special events with impact factors boost or reduce
            predictions.
          </p>
          <p>
            <strong>Day-of-week</strong> — All 7 days treated equally (restaurants open daily).
          </p>
        </div>
      </div>
    </div>
  );
}
