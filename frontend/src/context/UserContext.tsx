"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  ReactNode,
} from "react";
import { User, fetchUsers } from "@/lib/api";

const STORAGE_KEY = "da-selected-user-id";

type UserContextValue = {
  userId: string | null;
  user: User | null;
  setUserId: (id: string | null) => void;
  refreshUser: () => Promise<void>;
};

const UserContext = createContext<UserContextValue | undefined>(undefined);

export function UserProvider({ children }: { children: ReactNode }) {
  const [userId, setUserIdState] = useState<string | null>(null);
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) setUserIdState(stored);
  }, []);

  const refreshUser = useCallback(async () => {
    if (!userId) {
      setUser(null);
      return;
    }
    try {
      const users = await fetchUsers();
      const found = users.find((u) => u.id === userId);
      setUser(found || null);
    } catch {
      setUser(null);
    }
  }, [userId]);

  useEffect(() => {
    refreshUser();
  }, [refreshUser]);

  const setUserId = (id: string | null) => {
    setUserIdState(id);
    if (id) localStorage.setItem(STORAGE_KEY, id);
    else localStorage.removeItem(STORAGE_KEY);
  };

  return (
    <UserContext.Provider value={{ userId, user, setUserId, refreshUser }}>
      {children}
    </UserContext.Provider>
  );
}

export function useUserContext() {
  const ctx = useContext(UserContext);
  if (!ctx) throw new Error("useUserContext must be used within UserProvider");
  return ctx;
}
