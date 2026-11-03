const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export async function apiRequest(path, options = {}) {
  const token = localStorage.getItem("claimpilot_token");
  
  const headers = {
    ...options.headers,
  };
  
  if (options.body && !(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }
  
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
  });
  
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    let errorMessage = "Something went wrong.";
    
    if (data.detail) {
      if (Array.isArray(data.detail)) {
        errorMessage = data.detail.map(err => err.msg).join(", ");
      } else {
        errorMessage = data.detail;
      }
    }
    
    throw new Error(errorMessage);
  }
  
  return response.json();
}

export function uploadFile(path, formData, onProgress) {
  return new Promise((resolve, reject) => {
    const token = localStorage.getItem("claimpilot_token");
    const xhr = new XMLHttpRequest();
    
    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable && onProgress) {
        const percent = Math.round((event.loaded / event.total) * 100);
        onProgress(percent);
      }
    };
    
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          const data = JSON.parse(xhr.responseText);
          resolve(data);
        } catch (e) {
          reject(new Error("Something went wrong."));
        }
      } else {
        try {
          const data = JSON.parse(xhr.responseText);
          let errorMessage = "Something went wrong.";
          
          if (data.detail) {
            if (Array.isArray(data.detail)) {
              errorMessage = data.detail.map(err => err.msg).join(", ");
            } else {
              errorMessage = data.detail;
            }
          }
          
          reject(new Error(errorMessage));
        } catch (e) {
          reject(new Error("Something went wrong."));
        }
      }
    };
    
    xhr.onerror = () => {
      reject(new Error("Something went wrong."));
    };
    
    xhr.open("POST", `${API_BASE_URL}${path}`);
    
    if (token) {
      xhr.setRequestHeader("Authorization", `Bearer ${token}`);
    }
    
    xhr.send(formData);
  });
}
