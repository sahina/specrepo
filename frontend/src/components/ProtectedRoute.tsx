import { ReactNode } from "react";
import { useAuthStore } from "../store/authStore";
import { Login } from "./Login";

interface ProtectedRouteProps {
  children: ReactNode;
}

export function ProtectedRoute({ children }: ProtectedRouteProps) {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);

  if (!isAuthenticated) {
    return <Login />;
  }

  return <>{children}</>;
}
