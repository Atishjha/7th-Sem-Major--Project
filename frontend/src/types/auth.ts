export type UserRole = "ADMIN" | "SOC_ANALYST" | "VIEWER";

export interface User {
  id: string;
  username: string;
  role: UserRole;
  is_active: boolean;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  role: UserRole;
}
