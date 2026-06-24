/**
 * State management global — Zustand
 * Cart persisté dans localStorage pour PWA offline
 */

import { create } from "zustand";
import { persist } from "zustand/middleware";

interface CartItem {
  productId: string;
  name: string;
  price: number;
  quantity: number;
  imageUrl?: string;
}

interface CartState {
  items: CartItem[];
  storeId: string | null;
  companyId: string | null;
  orderType: "click_collect" | "delivery" | "scan_go";
  addItem: (item: CartItem) => void;
  removeItem: (productId: string) => void;
  updateQuantity: (productId: string, quantity: number) => void;
  clearCart: () => void;
  setStore: (storeId: string, companyId: string) => void;
  setOrderType: (type: "click_collect" | "delivery" | "scan_go") => void;
  total: () => number;
  itemCount: () => number;
}

export const useCartStore = create<CartState>()(
  persist(
    (set, get) => ({
      items: [],
      storeId: null,
      companyId: null,
      orderType: "click_collect",

      addItem: (item) => {
        set((state) => {
          const existing = state.items.find((i) => i.productId === item.productId);
          if (existing) {
            return {
              items: state.items.map((i) =>
                i.productId === item.productId
                  ? { ...i, quantity: i.quantity + item.quantity }
                  : i
              ),
            };
          }
          return { items: [...state.items, item] };
        });
      },

      removeItem: (productId) =>
        set((state) => ({
          items: state.items.filter((i) => i.productId !== productId),
        })),

      updateQuantity: (productId, quantity) => {
        if (quantity <= 0) {
          get().removeItem(productId);
          return;
        }
        set((state) => ({
          items: state.items.map((i) =>
            i.productId === productId ? { ...i, quantity } : i
          ),
        }));
      },

      clearCart: () => set({ items: [] }),

      setStore: (storeId, companyId) =>
        set({ storeId, companyId, items: [] }),

      setOrderType: (type) => set({ orderType: type }),

      total: () =>
        get().items.reduce((sum, item) => sum + item.price * item.quantity, 0),

      itemCount: () => get().items.reduce((sum, item) => sum + item.quantity, 0),
    }),
    {
      name: "smartcheckout-cart",
      partialize: (state) => ({
        items: state.items,
        storeId: state.storeId,
        companyId: state.companyId,
        orderType: state.orderType,
      }),
    }
  )
);

interface AuthState {
  user: {
    id: string;
    phone?: string;
    email?: string;
    firstName: string;
    lastName: string;
    role?: string;
    companyId?: string;
  } | null;
  isAuthenticated: boolean;
  setUser: (user: AuthState["user"]) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      isAuthenticated: false,
      setUser: (user) => set({ user, isAuthenticated: !!user }),
      logout: () => {
        set({ user: null, isAuthenticated: false });
        if (typeof window !== "undefined") {
          localStorage.removeItem("access_token");
          localStorage.removeItem("refresh_token");
        }
      },
    }),
    {
      name: "smartcheckout-auth",
    }
  )
);
