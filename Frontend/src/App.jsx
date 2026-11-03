import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext";
import ProtectedRoute from "./components/ProtectedRoute";
import CustomerLogin from "./pages/customer/CustomerLogin";
import StaffLogin from "./pages/staff/StaffLogin";
import CustomerDashboard from "./pages/customer/CustomerDashboard";
import ReviewerQueue from "./pages/staff/ReviewerQueue";

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Navigate to="/customer/login" replace />} />
          <Route path="/customer/login" element={<CustomerLogin />} />
          <Route path="/staff/login" element={<StaffLogin />} />
          <Route
            path="/customer"
            element={
              <ProtectedRoute area="customer">
                <CustomerDashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/staff"
            element={
              <ProtectedRoute area="staff">
                <ReviewerQueue />
              </ProtectedRoute>
            }
          />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}