import { createContext, useContext, useState, useEffect } from "react";
import { apiRequest } from "../api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    const token = localStorage.getItem("claimpilot_token");
    
    if (token) {
      apiRequest("/auth/me")
        .then((userData) => {
          setUser(userData);
        })
        .catch(() => {
          localStorage.removeItem("claimpilot_token");
          setUser(null);
        })
        .finally(() => {
          setLoading(false);
        });
    } else {
      setLoading(false);
    }
  }, []);
  
  async function customerRegister(fullName, email, password) {
    const data = await apiRequest("/auth/register", {
      method: "POST",
      body: JSON.stringify({
        full_name: fullName,
        email,
        password,
      }),
    });
    
    localStorage.setItem("claimpilot_token", data.access_token);
    setUser(data.user);
    return data.user;
  }
  
  async function customerLogin(email, password) {
    const data = await apiRequest("/auth/login", {
      method: "POST",
      body: JSON.stringify({
        email,
        password,
      }),
    });
    
    if (data.user.role !== "customer") {
      throw new Error("Staff accounts sign in on the staff page.");
    }
    
    localStorage.setItem("claimpilot_token", data.access_token);
    setUser(data.user);
    return data.user;
  }
  
  async function staffLogin(email, password) {
    const data = await apiRequest("/auth/staff/login", {
      method: "POST",
      body: JSON.stringify({
        email,
        password,
      }),
    });
    
    if (data.user.role === "customer") {
      throw new Error("This account is not a staff account.");
    }
    
    localStorage.setItem("claimpilot_token", data.access_token);
    setUser(data.user);
    return data.user;
  }
  
  function logout() {
    localStorage.removeItem("claimpilot_token");
    setUser(null);
  }
  
  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        customerRegister,
        customerLogin,
        staffLogin,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}
