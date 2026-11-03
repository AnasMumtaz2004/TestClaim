import { useState, useEffect } from "react";
import { uploadFile } from "../api";

export default function FileUpload({ claimId, onUploaded }) {
  const [items, setItems] = useState([]);
  const [uploadError, setUploadError] = useState("");
  
  const docTypes = [
    { value: "photo_front", label: "Photo: front" },
    { value: "photo_rear", label: "Photo: rear" },
    { value: "photo_left", label: "Photo: left side" },
    { value: "photo_right", label: "Photo: right side" },
    { value: "photo_closeup", label: "Photo: close-up of damage" },
    { value: "estimate", label: "Repair estimate" },
    { value: "police_report", label: "Police report" },
    { value: "discharge_summary", label: "Discharge summary" },
    { value: "bill", label: "Bill" },
    { value: "other", label: "Other" },
  ];
  
  useEffect(() => {
    return () => {
      items.forEach(item => {
        if (item.previewUrl) {
          URL.revokeObjectURL(item.previewUrl);
        }
      });
    };
  }, []);
  
  function handleFiles(fileList) {
    const newItems = [];
    
    for (let i = 0; i < fileList.length; i++) {
      const file = fileList[i];
      const id = Math.random().toString(36).substring(7);
      
      let status = "ready";
      let message = "";
      let previewUrl = null;
      
      const ext = file.name.split(".").pop().toLowerCase();
      const isImage = ext === "jpg" || ext === "jpeg" || ext === "png";
      const isPdf = ext === "pdf";
      
      if (!isImage && !isPdf) {
        status = "error";
        message = "Only JPG, PNG and PDF files are allowed.";
      } else if (file.size > 10 * 1024 * 1024) {
        status = "error";
        message = "File is larger than 10 MB.";
      } else if (isImage) {
        previewUrl = URL.createObjectURL(file);
      }
      
      newItems.push({
        id,
        file,
        previewUrl,
        docType: "",
        status,
        progress: 0,
        message,
        retake: false,
      });
    }
    
    setItems(prev => [...prev, ...newItems]);
  }
  
  function removeItem(id) {
    setItems(prev => {
      const item = prev.find(i => i.id === id);
      if (item && item.previewUrl) {
        URL.revokeObjectURL(item.previewUrl);
      }
      return prev.filter(i => i.id !== id);
    });
  }
  
  function updateDocType(id, docType) {
    setItems(prev => prev.map(item => item.id === id ? { ...item, docType } : item));
  }
  
  async function uploadAll() {
    setUploadError("");
    
    const readyItems = items.filter(i => i.status === "ready");
    
    if (readyItems.length === 0) {
      return;
    }
    
    for (const item of readyItems) {
      if (!item.docType) {
        setUploadError("Choose a type for every file.");
        return;
      }
    }
    
    for (const item of readyItems) {
      setItems(prev => prev.map(i => i.id === item.id ? { ...i, status: "uploading", progress: 0 } : i));
      
      const formData = new FormData();
      formData.append("doc_type", item.docType);
      formData.append("file", item.file);
      
      try {
        const result = await uploadFile(
          `/customer/claims/${claimId}/documents`,
          formData,
          (progress) => {
            setItems(prev => prev.map(i => i.id === item.id ? { ...i, progress } : i));
          }
        );
        
        setItems(prev => prev.map(i => i.id === item.id ? { ...i, status: "done", retake: result.retake || false } : i));
        
        if (onUploaded) {
          onUploaded(result);
        }
      } catch (error) {
        setItems(prev => prev.map(i => i.id === item.id ? { ...i, status: "error", message: error.message } : i));
      }
    }
  }
  
  return (
    <div className="space-y-4">
      <div className="flex gap-4">
        <label className="border-2 border-secondary px-4 py-2 font-body text-sm bg-white hover:bg-secondary hover:text-white cursor-pointer transition-colors">
          Take photo
          <input
            type="file"
            accept="image/*"
            capture="environment"
            className="hidden"
            onChange={(e) => handleFiles(e.target.files)}
          />
        </label>
        
        <label className="border-2 border-secondary px-4 py-2 font-body text-sm bg-white hover:bg-secondary hover:text-white cursor-pointer transition-colors">
          Choose files
          <input
            type="file"
            accept="image/jpeg,image/png,application/pdf"
            multiple
            className="hidden"
            onChange={(e) => handleFiles(e.target.files)}
          />
        </label>
      </div>
      
      {uploadError && (
        <div className="bg-accent border-l-2 border-secondary p-3 font-mono text-xs text-black">
          {uploadError}
        </div>
      )}
      
      {items.length > 0 && (
        <div className="space-y-4">
          {items.map(item => (
            <div key={item.id} className="border-2 border-secondary p-4 bg-white">
              <div className="flex items-start gap-4">
                {item.previewUrl ? (
                  <img
                    src={item.previewUrl}
                    alt="Preview"
                    className="w-16 h-16 object-cover border-2 border-secondary"
                  />
                ) : (
                  <div className="w-16 h-16 border-2 border-secondary flex items-center justify-center font-mono text-xs">
                    PDF
                  </div>
                )}
                
                <div className="flex-1 space-y-2">
                  <div className="font-body text-sm">{item.file.name}</div>
                  <div className="font-mono text-xs">{Math.round(item.file.size / 1024)} KB</div>
                  
                  {(item.status === "ready" || item.status === "error") && (
                    <select
                      value={item.docType}
                      onChange={(e) => updateDocType(item.id, e.target.value)}
                      className="w-full bg-white text-black font-body text-sm border-2 border-black rounded-none px-3 py-2"
                    >
                      <option value="">Select type</option>
                      {docTypes.map(type => (
                        <option key={type.value} value={type.value}>{type.label}</option>
                      ))}
                    </select>
                  )}
                  
                  {item.status === "uploading" && (
                    <div className="h-2 border-2 border-secondary">
                      <div
                        className="h-full bg-secondary transition-all"
                        style={{ width: `${item.progress}%` }}
                      />
                    </div>
                  )}
                  
                  {item.message && (
                    <div className="font-mono text-xs text-black">{item.message}</div>
                  )}
                  
                  {item.status === "done" && item.retake && (
                    <div className="bg-accent border-l-2 border-secondary p-3 font-mono text-xs text-black">
                      This photo looks blurry. Please retake it.
                    </div>
                  )}
                  
                  {(item.status === "ready" || item.status === "error") && (
                    <button
                      onClick={() => removeItem(item.id)}
                      className="border-2 border-secondary px-3 py-1 font-body text-sm hover:bg-secondary hover:text-white"
                    >
                      Remove
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
          
          <button
            onClick={uploadAll}
            disabled={items.filter(i => i.status === "ready").length === 0}
            className="bg-secondary text-white hover:bg-black font-body font-semibold text-sm px-4 py-3 rounded-none disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Upload all
          </button>
        </div>
      )}
    </div>
  );
}
