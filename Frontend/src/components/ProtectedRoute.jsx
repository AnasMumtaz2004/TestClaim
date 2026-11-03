import { Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function ProtectedRoute({ area, children }) {
  const { user, loading } = useAuth();
  
  if (loading) {
    return null;
  }
  
  if (!user) {
    return <Navigate to={`/${area}/login`} replace />;
  }
  
  const isStaff = user.role !== "customer";
  
  if (area === "customer" && isStaff) {
    return <Navigate to="/staff/login" replace />;
  }
  
  if (area === "staff" && !isStaff) {
    return <Navigate to="/customer/login" replace />;
  }
  
  return children;
}
