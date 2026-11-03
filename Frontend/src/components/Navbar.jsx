import { useAuth } from "../context/AuthContext";
import { useNavigate } from "react-router-dom";

export default function Navbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  
  if (!user) {
    return null;
  }
  
  function handleLogout() {
    const wasCustomer = user.role === "customer";
    logout();
    if (wasCustomer) {
      navigate("/customer/login");
    } else {
      navigate("/staff/login");
    }
  }
  
  const displayRole = user.role.replace(/_/g, " ");
  
  return (
    <header className="w-full bg-secondary text-white">
      <div className="flex items-center justify-between gap-4 px-6 sm:px-8 py-4">
        <span className="font-display text-xl tracking-tight uppercase">
          ClaimPilot
        </span>
        
        <div className="flex items-center gap-4">
          <span className="font-body text-sm hidden sm:inline">
            {user.full_name}
          </span>
          
          <span className="font-mono text-xs uppercase tracking-wider bg-accent text-black px-2 py-1">
            {displayRole}
          </span>
          
          <button
            onClick={handleLogout}
            className="border-2 border-white text-white font-body font-semibold text-sm px-4 py-2 rounded-none hover:bg-white hover:text-secondary transition-colors cursor-pointer"
          >
            Log out
          </button>
        </div>
      </div>
    </header>
  );
}
