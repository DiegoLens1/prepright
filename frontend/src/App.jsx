import { useState } from "react";
import Categories from "./pages/Categories";
import Products from "./pages/Products";
import Ingredients from "./pages/Ingredients";
import Events from "./pages/Events";
import SettingsPage from "./pages/Settings";
import Templates from "./pages/Templates";
import Predictions from "./pages/Predictions";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000/api";

export default function App() {
  const [page, setPage] = useState("products");

  const navItems = [
    { id: "products", label: "Products" },
    { id: "categories", label: "Categories" },
    { id: "ingredients", label: "Ingredients" },
    { id: "events", label: "Events" },
    { id: "templates", label: "Templates" },
    { id: "predictions", label: "Predictions" },
    { id: "settings", label: "Settings" },
  ];

  return (
    <div className="min-h-screen bg-surface">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-4 py-3 no-print">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <h1 className="text-xl font-semibold text-primary">PrepRight</h1>
          <nav className="flex gap-1">
            {navItems.map((item) => (
              <button
                key={item.id}
                onClick={() => setPage(item.id)}
                className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                  page === item.id
                    ? "bg-primary text-white"
                    : "text-gray-600 hover:bg-gray-100"
                }`}
              >
                {item.label}
              </button>
            ))}
          </nav>
        </div>
      </header>

      {/* Main content */}
      <main className="max-w-6xl mx-auto p-4">
        {page === "products" && <Products API={API} />}
        {page === "categories" && <Categories API={API} />}
        {page === "ingredients" && <Ingredients API={API} />}
        {page === "events" && <Events API={API} />}
        {page === "templates" && <Templates API={API} />}
        {page === "predictions" && <Predictions API={API} />}
        {page === "settings" && <SettingsPage API={API} />}
      </main>
    </div>
  );
}
