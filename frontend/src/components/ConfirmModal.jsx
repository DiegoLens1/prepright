import { useState, useEffect, useRef } from "react";

export default function ConfirmModal({ isOpen, title, message, onConfirm, confirmLabel = "Confirm" }) {
  const overlayRef = useRef(null);

  useEffect(() => {
    if (isOpen) {
      const handler = (e) => {
        if (e.key === "Escape") {
          onConfirm(null);
        }
      };
      window.addEventListener("keydown", handler);
      return () => window.removeEventListener("keydown", handler);
    }
  }, [isOpen, onConfirm]);

  if (!isOpen) return null;

  return (
    <div
      ref={overlayRef}
      className="fixed inset-0 bg-black/40 flex items-center justify-center z-[100] p-4"
      onClick={(e) => {
        if (e.target === overlayRef.current) onConfirm(null);
      }}
    >
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6">
        <h3 className="text-lg font-semibold text-gray-800 mb-2">{title}</h3>
        <p className="text-sm text-gray-600 mb-6">{message}</p>
        <div className="flex justify-end gap-3">
          <button
            onClick={() => onConfirm(null)}
            className="px-4 py-2 text-gray-700 hover:bg-gray-200 rounded-lg transition-colors text-sm font-medium"
          >
            Cancel
          </button>
          <button
            onClick={() => onConfirm(true)}
            className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors text-sm font-medium"
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
