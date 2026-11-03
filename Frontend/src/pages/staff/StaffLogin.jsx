import { Navigate, useNavigate, Link } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import LoginForm from "../../components/LoginForm";

export default function StaffLogin() {
  const { user, staffLogin } = useAuth();
  const navigate = useNavigate();
  
  if (user && user.role !== "customer") {
    return <Navigate to="/staff" replace />;
  }
  
  async function handleStaffSignIn(values) {
    await staffLogin(values.email, values.password);
    navigate("/staff");
  }
  
  const fields = [
    { name: "email", label: "Email", type: "email", autoComplete: "email", placeholder: "you@domain.com" },
    { name: "password", label: "Password", type: "password", autoComplete: "current-password" },
  ];
  
  return (
    <div className="min-h-screen w-full bg-accent flex flex-col md:flex-row">
      <div className="w-full md:w-1/2 flex flex-col justify-center px-8 sm:px-16 md:px-20 lg:px-28 py-12 md:py-0">
        <h1 className="font-display text-4xl sm:text-5xl lg:text-6xl tracking-tight text-secondary leading-none uppercase">
          ClaimPilot
        </h1>
        <p className="font-mono text-xs uppercase tracking-wider text-secondary mt-4">
          Staff
        </p>
      </div>
      
      <div className="w-full md:w-1/2 flex items-center justify-start md:justify-center px-8 sm:px-12 md:px-16 lg:px-20 py-8 md:py-12">
        <div className="w-full max-w-sm bg-white border-2 border-secondary rounded-none p-8">
          <div className="flex border-b-2 border-secondary mb-8">
            <div className="py-2 px-4 font-body text-sm tracking-wider text-left text-secondary font-semibold border-b-2 border-accent">
              Staff sign in
            </div>
          </div>
          
          <LoginForm
            fields={fields}
            submitLabel="Sign in"
            busyLabel="Signing in..."
            onSubmit={handleStaffSignIn}
          />
          
          <div className="mt-8 pt-4 border-t border-secondary text-left">
            <Link to="/customer/login" className="font-body text-xs text-secondary underline underline-offset-4">
              Customer? Sign in here.
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
