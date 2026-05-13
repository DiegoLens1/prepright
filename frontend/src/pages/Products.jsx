import { useState, useEffect } from "react";
import axios from "axios";

export default function Products({ API }) {
  const [products, setProducts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [ingredients, setIngredients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(null);
  const [showForm, setShowForm] = useState(false);

  // Form state
  const [name, setName] = useState("");
  const [categoryId, setCategoryId] = useState("");
  const [marginPct, setMarginPct] = useState(0);
  const [aliasesStr, setAliasesStr] = useState("");
  const [recipesStr, setRecipesStr] = useState("");

  useEffect(() => {
    Promise.all([
      axios.get(`${API}/products`),
      axios.get(`${API}/categories`),
      axios.get(`${API}/ingredients`),
    ]).then(([p, c, i]) => {
      setProducts(p.data);
      setCategories(c.data);
      setIngredients(i.data);
      setLoading(false);
    });
  }, [API]);

  const openCreate = () => {
    setEditing(null);
    setName("");
    setCategoryId("");
    setMarginPct(0);
    setAliasesStr("");
    setRecipesStr("");
    setShowForm(true);
  };

  const openEdit = (product) => {
    setEditing(product);
    setName(product.name);
    setCategoryId(product.category_id);
    setMarginPct(product.margin_pct);
    setAliasesStr(product.aliases.map((a) => a.alias_name).join(", "));
    setRecipesStr(
      product.recipes
        .map((r) => `${r.ingredient_name}:${r.quantity_per_unit}`)
        .join("\n")
    );
    setShowForm(true);
  };

  const saveProduct = async () => {
    if (!name.trim()) { alert("Product name is required."); return; }
    if (!categoryId) { alert("Please select a category."); return; }

    const aliases = aliasesStr
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean)
      .map((alias_name) => ({ alias_name }));

    const recipes = recipesStr
      .split("\n")
      .map((line) => line.trim())
      .filter(Boolean)
      .map((line) => {
        const [name, qty] = line.split(":");
        return {
          ingredient_name: name?.trim(),
          quantity_per_unit: parseFloat(qty?.trim()) || 0,
        };
      })
      .filter((r) => r.ingredient_name);

    // Map ingredient names to IDs
    const mappedRecipes = recipes.map((r) => {
      const ing = ingredients.find((i) => i.name === r.ingredient_name);
      if (!ing) throw new Error(`Ingredient "${r.ingredient_name}" not found. Add it in the Ingredients tab first.`);
      return { ingredient_id: ing.id, quantity_per_unit: r.quantity_per_unit };
    });

    const data = {
      name,
      category_id: Number(categoryId),
      margin_pct: marginPct,
      aliases,
      recipes: mappedRecipes,
    };

    if (editing) {
      try {
        const res = await axios.put(`${API}/products/${editing.id}`, data);
        setProducts((prev) => prev.map((p) => (p.id === res.data.id ? res.data : p)));
      } catch (err) {
        alert(err.response?.data?.detail || "Failed to save product");
        return;
      }
    } else {
      try {
        const res = await axios.post(`${API}/products`, data);
        setProducts((prev) => [...prev, res.data]);
      } catch (err) {
        alert(err.response?.data?.detail || "Failed to save product");
        return;
      }
    }
    setShowForm(false);
  };

  const deleteProduct = async (id) => {
    if (!confirm("Delete this product?")) return;
    await axios.delete(`${API}/products/${id}`);
    setProducts((prev) => prev.filter((p) => p.id !== id));
  };

  if (loading) return <p className="text-gray-500">Loading...</p>;

  return (
    <div>
      <div className="flex items-center justify-between mb-4 no-print">
        <h2 className="text-lg font-semibold">Products ({products.length})</h2>
        <button
          onClick={openCreate}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700"
        >
          + Add Product
        </button>
      </div>

      {/* Create/Edit form */}
      {showForm && (
        <div className="bg-white border border-gray-200 rounded-lg p-4 mb-4 no-print">
          <h3 className="font-medium mb-3">{editing ? "Edit" : "Add"} Product</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div>
              <label className="block text-xs text-gray-500 mb-1">Name *</label>
              <input
                className="w-full border rounded px-3 py-2 text-sm"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Chocolate Croissant"
              />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Category *</label>
              <select
                className="w-full border rounded px-3 py-2 text-sm"
                value={categoryId}
                onChange={(e) => setCategoryId(e.target.value)}
              >
                <option value="">Select category</option>
                {categories.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Margin %</label>
              <input
                className="w-full border rounded px-3 py-2 text-sm"
                type="number"
                value={marginPct}
                onChange={(e) => setMarginPct(Number(e.target.value))}
                placeholder="0"
              />
            </div>
          </div>

          <div className="mt-3">
            <label className="block text-xs text-gray-500 mb-1">
              Aliases (comma-separated, for matching receipt names)
            </label>
            <input
              className="w-full border rounded px-3 py-2 text-sm"
              value={aliasesStr}
              onChange={(e) => setAliasesStr(e.target.value)}
              placeholder="e.g. choc croissant, choc croiss, chocolate croissant"
            />
          </div>

          <div className="mt-3">
            <label className="block text-xs text-gray-500 mb-1">
              Recipe (ingredient:quantity per line)
            </label>
            <textarea
              className="w-full border rounded px-3 py-2 text-sm font-mono"
              rows={4}
              value={recipesStr}
              onChange={(e) => setRecipesStr(e.target.value)}
              placeholder={`bread:2\ncheese:1\nmeat:0.5`}
            />
            <p className="text-xs text-gray-400 mt-1">
              Use ingredient names from the Ingredients tab. Leave empty if no recipe.
            </p>
          </div>

          <div className="flex gap-2 mt-4">
            <button
              onClick={saveProduct}
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

      {/* Product table */}
      <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th className="text-left px-4 py-2 font-medium text-gray-600">Name</th>
              <th className="text-left px-4 py-2 font-medium text-gray-600">Category</th>
              <th className="text-right px-4 py-2 font-medium text-gray-600">Margin %</th>
              <th className="text-right px-4 py-2 font-medium text-gray-600">Recipes</th>
              <th className="text-right px-4 py-2 font-medium text-gray-600 no-print">Actions</th>
            </tr>
          </thead>
          <tbody>
            {products.map((p) => (
              <tr key={p.id} className="border-b border-gray-100 hover:bg-gray-50">
                <td className="px-4 py-2 font-medium">{p.name}</td>
                <td className="px-4 py-2 text-gray-600">{p.category_name}</td>
                <td className="px-4 py-2 text-right">{p.margin_pct}%</td>
                <td className="px-4 py-2 text-right">
                  {p.recipes.length > 0 ? (
                    <span className="text-xs bg-blue-50 text-blue-700 px-2 py-0.5 rounded">
                      {p.recipes.length} items
                    </span>
                  ) : (
                    <span className="text-gray-400">—</span>
                  )}
                </td>
                <td className="px-4 py-2 text-right no-print">
                  <button
                    onClick={() => openEdit(p)}
                    className="text-primary hover:underline text-sm mr-3"
                  >
                    Edit
                  </button>
                  <button
                    onClick={() => deleteProduct(p.id)}
                    className="text-danger hover:underline text-sm"
                  >
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {products.length === 0 && (
          <p className="text-center text-gray-400 py-8">No products yet. Add your first product above.</p>
        )}
      </div>
    </div>
  );
}
