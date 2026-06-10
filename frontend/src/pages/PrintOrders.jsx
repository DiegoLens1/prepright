import { useState, useEffect } from "react";
import axios from "axios";

const ORDER_WIDTH = 40;

function ReceiptPreview({ receipt, orderNumber, timestamp, onClose }) {
  return (
    <div
      className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-xl shadow-2xl max-w-md w-full overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="bg-gray-800 px-4 py-3 flex items-center justify-between">
          <h3 className="text-white font-semibold text-sm">Print Preview</h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white transition-colors text-lg"
          >
            x
          </button>
        </div>

        {/* Receipt */}
        <div className="p-4 bg-[#f5f2eb]">
          <pre
            className="font-mono text-xs leading-[1.35] whitespace-pre"
            style={{ color: "#1a1a1a" }}
          >
            {receipt}
          </pre>
        </div>

        {/* Actions */}
        <div className="px-4 py-3 bg-gray-50 border-t border-gray-200 flex items-center justify-between">
          <div className="text-xs text-gray-500">
            Order: {orderNumber}
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => {
                navigator.clipboard.writeText(receipt);
              }}
              className="px-3 py-1.5 bg-gray-200 text-gray-700 rounded-lg text-xs font-medium hover:bg-gray-300 transition-colors"
            >
              Copy
            </button>
            <button
              onClick={() => window.print()}
              className="px-3 py-1.5 bg-blue-600 text-white rounded-lg text-xs font-medium hover:bg-blue-700 transition-colors"
            >
              Print
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function PrintOrders({ API }) {
  const [products, setProducts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);

  // Order state
  const [addedIds, setAddedIds] = useState({});
  const [receipt, setReceipt] = useState(null);
  const [orderNumber, setOrderNumber] = useState("");
  const [timestamp, setTimestamp] = useState("");
  const [sending, setSending] = useState(false);
  const [customerName, setCustomerName] = useState("");

  useEffect(() => {
    Promise.all([
      axios.get(`${API}/products`),
      axios.get(`${API}/categories`),
    ]).then(([pRes, cRes]) => {
      setProducts(pRes.data);
      setCategories(cRes.data);
      setLoading(false);
    });
  }, [API]);

  const generateOrderNumber = () => {
    const now = new Date();
    const y = String(now.getFullYear()).slice(-2);
    const m = String(now.getMonth() + 1).padStart(2, "0");
    const d = String(now.getDate()).padStart(2, "0");
    const h = String(now.getHours()).padStart(2, "0");
    const min = String(now.getMinutes()).padStart(2, "0");
    const s = String(now.getSeconds()).padStart(2, "0");
    return `ORD-${y}${m}${d}-${h}${min}${s}`;
  };

  const formatTimestamp = () => {
    const now = new Date();
    return now.toLocaleString();
  };

  const addProduct = (productId) => {
    if (!productId) return;
    setAddedIds((prev) => ({
      ...prev,
      [productId]: prev[productId] || 1,
    }));
  };

  const removeProduct = (productId) => {
    setAddedIds((prev) => {
      const next = { ...prev };
      delete next[productId];
      return next;
    });
  };

  const updateQuantity = (productId, value) => {
    const qty = parseFloat(value);
    if (isNaN(qty) || qty < 0.01) return;
    setAddedIds((prev) => ({ ...prev, [productId]: qty }));
  };

  const getProductName = (id) => {
    const p = products.find((p) => p.id === id);
    return p ? p.name : `Product #${id}`;
  };

  const getProductPrice = (id) => {
    const p = products.find((p) => p.id === id);
    return p && p.margin_pct ? p.margin_pct : 5.0;
  };

  const getOrderItems = () => {
    return Object.entries(addedIds).map(([id, qty]) => ({
      product_id: Number(id),
      quantity: qty,
    }));
  };

  const sendOrder = async () => {
    const items = getOrderItems();
    if (items.length === 0) return;

    setSending(true);
    try {
      const res = await axios.post(`${API}/print-orders/simulate`, {
        items,
        customer_name: customerName,
      });
      setReceipt(res.data.receipt_text);
      setOrderNumber(res.data.order_number);
      setTimestamp(res.data.timestamp);
    } catch (err) {
      alert(err.response?.data?.detail || "Failed to send order");
    } finally {
      setSending(false);
    }
  };

  const sendDemoOrder = () => {
    // Use first 3 active products as demo
    const active = products.filter((p) => p.active).slice(0, 3);
    if (active.length === 0) {
      alert("Add some products first to send a demo order.");
      return;
    }
    const demo = {};
    active.forEach((p, i) => {
      demo[p.id] = i === 0 ? 2 : i === 1 ? 3 : 1;
    });
    setAddedIds(demo);
  };

  if (loading) return <p className="text-gray-500">Loading...</p>;

  const orderItems = getOrderItems();
  const subtotal = orderItems.reduce(
    (sum, item) => sum + getProductPrice(item.product_id) * item.quantity,
    0
  );
  const tax = subtotal * 0.1;
  const total = subtotal + tax;

  return (
    <div>
      <div className="flex items-center justify-between mb-6 no-print">
        <div>
          <h2 className="text-2xl font-bold text-gray-800">Print Orders</h2>
          <p className="text-sm text-gray-500 mt-1">
            Compose orders and simulate printing to a thermal receipt printer
          </p>
        </div>
        <button
          onClick={sendDemoOrder}
          className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 text-sm font-medium transition-colors"
        >
          ⚡ Send Demo Order
        </button>
      </div>

      {/* Compose Order */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Product Selector */}
        <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
          <div className="px-4 py-3 bg-gray-50 border-b border-gray-200">
            <h3 className="font-semibold text-gray-800 text-sm">
              Add Products
            </h3>
          </div>

          <div className="p-4 space-y-3 max-h-[480px] overflow-y-auto">
            {categories.map((cat) => {
              const catProducts = products.filter(
                (p) => p.category_id === cat.id && p.active
              );
              if (catProducts.length === 0) return null;
              return (
                <div key={cat.id}>
                  <p className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-2">
                    {cat.name}
                  </p>
                  <div className="space-y-1">
                    {catProducts.map((p) => (
                      <div
                        key={p.id}
                        className="flex items-center justify-between px-3 py-2 rounded-lg border border-gray-100 hover:border-gray-300 transition-colors"
                      >
                        <div>
                          <p className="text-sm font-medium text-gray-800">
                            {p.name}
                          </p>
                          <p className="text-xs text-gray-400">
                            ${getProductPrice(p.id).toFixed(2)}
                          </p>
                        </div>
                        <button
                          onClick={() => addProduct(p.id)}
                          disabled={!!addedIds[p.id]}
                          className={`text-sm font-medium px-3 py-1 rounded-lg transition-colors ${
                            addedIds[p.id]
                              ? "text-gray-300 cursor-not-allowed"
                              : "text-blue-600 hover:bg-blue-50"
                          }`}
                        >
                          {addedIds[p.id] ? "Added" : "+ Add"}
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
            {products.filter((p) => p.active).length === 0 && (
              <p className="text-sm text-gray-400 text-center py-6">
                No active products. Add some in the Products tab first.
              </p>
            )}
          </div>
        </div>

        {/* Current Order */}
        <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
          <div className="px-4 py-3 bg-gray-50 border-b border-gray-200">
            <h3 className="font-semibold text-gray-800 text-sm">
              Current Order
            </h3>
          </div>

          <div className="p-4">
            <div className="mb-3">
              <label className="block text-xs text-gray-500 mb-1">
                Customer Name (optional)
              </label>
              <input
                type="text"
                value={customerName}
                onChange={(e) => setCustomerName(e.target.value)}
                placeholder="Walk-in customer"
                className="w-full border rounded-lg px-3 py-2 text-sm"
              />
            </div>

            {/* Order items */}
            {orderItems.length === 0 ? (
              <div className="text-center py-12">
                <p className="text-gray-400 text-sm">
                  No items added yet.
                </p>
                <p className="text-gray-300 text-xs mt-1">
                  Select products from the left to start.
                </p>
              </div>
            ) : (
              <div className="space-y-2 mb-4">
                {orderItems.map(({ product_id, quantity }) => (
                  <div
                    key={product_id}
                    className="flex items-center justify-between px-3 py-2 bg-gray-50 rounded-lg border border-gray-100"
                  >
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-800 truncate">
                        {getProductName(product_id)}
                      </p>
                      <p className="text-xs text-gray-400">
                        ${getProductPrice(product_id).toFixed(2)} each
                      </p>
                    </div>
                    <div className="flex items-center gap-2 ml-3">
                      <input
                        type="number"
                        min="0.01"
                        step="0.1"
                        value={quantity}
                        onChange={(e) => updateQuantity(product_id, e.target.value)}
                        className="w-16 border rounded px-2 py-1 text-sm text-center"
                      />
                      <button
                        onClick={() => removeProduct(product_id)}
                        className="text-red-400 hover:text-red-600 text-sm font-medium px-1"
                      >
                        x
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Summary */}
            {orderItems.length > 0 && (
              <div className="border-t border-gray-200 pt-3 mb-4">
                <div className="flex justify-between text-sm text-gray-500">
                  <span>Subtotal</span>
                  <span>${subtotal.toFixed(2)}</span>
                </div>
                <div className="flex justify-between text-sm text-gray-500 mt-1">
                  <span>Tax (10%)</span>
                  <span>${tax.toFixed(2)}</span>
                </div>
                <div className="flex justify-between font-bold text-gray-800 mt-2 pt-2 border-t border-gray-200">
                  <span>Total</span>
                  <span>${total.toFixed(2)}</span>
                </div>
              </div>
            )}

            <button
              onClick={sendOrder}
              disabled={orderItems.length === 0 || sending}
              className="w-full py-2.5 bg-blue-600 text-white rounded-lg font-medium text-sm hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
            >
              {sending ? (
                <>
                  <span className="animate-spin">⟳</span> Sending...
                </>
              ) : (
                <>
                  <span>🖨️</span> Simulate Print
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Receipt Preview Modal */}
      {receipt && (
        <ReceiptPreview
          receipt={receipt}
          orderNumber={orderNumber}
          timestamp={timestamp}
          onClose={() => setReceipt(null)}
        />
      )}
    </div>
  );
}
