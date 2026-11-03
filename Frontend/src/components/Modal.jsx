import { useEffect } from "react";

export default function Modal({ open, title, onClose, children }) {
  useEffect(() => {
    if (!open) {
      return;
    }
    
    function handleKeyDown(event) {
      if (event.key === "Escape") {
        onClose();
      }
    }
    
    document.addEventListener("keydown", handleKeyDown);
    
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [open, onClose]);
  
  if (!open) {
    return null;
  }
  
  return (
    <div className="fixed inset-0 z-50 bg-secondary flex items-center justify-center p-4">
      <div className="w-full max-w-lg max-h-full overflow-y-auto bg-white border-2 border-secondary rounded-none p-6">
        <div className="flex items-center justify-between mb-6">
          <h2 className="font-display text-xl uppercase text-secondary">
            {title}
          </h2>
          <button
            onClick={onClose}
            className="border-2 border-secondary px-3 py-1 font-body text-sm hover:bg-secondary hover:text-white transition-colors"
          >
            Close
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}
