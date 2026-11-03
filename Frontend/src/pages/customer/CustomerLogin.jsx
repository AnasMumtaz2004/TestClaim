import { useState } from "react";
import { Navigate, useNavigate, Link } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import LoginForm from "../../components/LoginForm";

export default function CustomerLogin() {
  const { user, customerLogin, customerRegister } = useAuth();
  const navigate = useNavigate();
  const [mode, setMode] = useState("signin");
  const [localError, setLocalError] = useState("");
  
  if (user && user.role === "customer") {
    return <Navigate to="/customer" replace />;
  }
  
  function switchMode(newMode) {
    setMode(newMode);
    setLocalError("");
  }
  
  async function handleSignIn(values) {
    await customerLogin(values.email, values.password);
    navigate("/customer");
  }
  
  async function handleSignUp(values) {
    if (values.password.length < 8) {
      setLocalError("Password must be at least 8 characters.");
      throw new Error("Password must be at least 8 characters.");
    }
    
    setLocalError("");
    await customerRegister(values.fullName, values.email, values.password);
    navigate("/customer");
  }
  
  const signInFields = [
    { name: "email", label: "Email", type: "email", autoComplete: "email", placeholder: "you@domain.com" },
    { name: "password", label: "Password", type: "password", autoComplete: "current-password" },
  ];
  
  const signUpFields = [
    { name: "fullName", label: "Full name", type: "text", autoComplete: "name" },
    { name: "email", label: "Email", type: "email", autoComplete: "email", placeholder: "you@domain.com" },
    { name: "password", label: "Password", type: "password", autoComplete: "new-password" },
  ];
  
  return (
    <div className="min-h-screen w-full bg-primary flex flex-col md:flex-row">
      <div className="w-full md:w-1/2 flex flex-col justify-center px-8 sm:px-16 md:px-20 lg:px-28 py-12 md:py-0">
        <h1 className="font-display text-4xl sm:text-5xl lg:text-6xl tracking-tight text-secondary leading-none uppercase">
          ClaimPilot
        </h1>
       
      </div>
      
      <div className="w-full md:w-1/2 flex items-center justify-start md:justify-center px-8 sm:px-12 md:px-16 lg:px-20 py-8 md:py-12">
        <div className="w-full max-w-sm bg-white border-2 border-secondary rounded-none p-8">
          <div className="flex border-b-2 border-secondary mb-8">
            <button
              onClick={() => switchMode("signin")}
              className={`py-2 px-4 font-body text-sm tracking-wider text-left text-secondary cursor-pointer focus:outline-none focus-visible:outline-2 focus-visible:outline-secondary ${mode === "signin" ? "border-b-2 border-accent font-semibold" : "border-b-2 border-transparent font-normal"}`}
            >
              Sign in
            </button>
            <button
              onClick={() => switchMode("signup")}
              className={`py-2 px-4 font-body text-sm tracking-wider text-left text-secondary cursor-pointer focus:outline-none focus-visible:outline-2 focus-visible:outline-secondary ${mode === "signup" ? "border-b-2 border-accent font-semibold" : "border-b-2 border-transparent font-normal"}`}
            >
              Create account
            </button>
          </div>
          
          {mode === "signin" ? (
            <LoginForm
              key="signin"
              fields={signInFields}
              submitLabel="Sign in"
              busyLabel="Signing in..."
              onSubmit={handleSignIn}
            />
          ) : (
            <LoginForm
              key="signup"
              fields={signUpFields}
              submitLabel="Create account"
              busyLabel="Creating account..."
              onSubmit={handleSignUp}
            />
          )}
          
          <div className="mt-8 pt-4 border-t border-secondary text-left">
            <Link to="/staff/login" className="font-body text-xs text-secondary underline underline-offset-4">
              Staff sign in →
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
