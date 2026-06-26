/**
 * Client API SmartCheckout — axios avec intercepteurs auth et gestion d'erreur
 */

import axios, { AxiosError, AxiosInstance } from "axios";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const api: AxiosInstance = axios.create({
  baseURL: `${API_URL}/api/v1`,
  timeout: 15000,
  headers: { "Content-Type": "application/json" },
});

// Injecter le token JWT à chaque requête
api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("access_token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    const companyId = localStorage.getItem("company_id");
    if (companyId) {
      config.headers["X-Company-ID"] = companyId;
    }
  }
  return config;
});

// Auto-refresh du token si 401
let isRefreshing = false;
let failedQueue: Array<{ resolve: Function; reject: Function }> = [];

const processQueue = (error: Error | null, token: string | null) => {
  failedQueue.forEach(({ resolve, reject }) => {
    if (error) reject(error);
    else resolve(token);
  });
  failedQueue = [];
};

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as any;

    if (error.response?.status === 401 && !originalRequest._retry) {
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        }).then((token) => {
          originalRequest.headers.Authorization = `Bearer ${token}`;
          return api(originalRequest);
        });
      }

      originalRequest._retry = true;
      isRefreshing = true;

      const refreshToken = localStorage.getItem("refresh_token");
      if (!refreshToken) {
        isRefreshing = false;
        window.location.href = "/login";
        return Promise.reject(error);
      }

      try {
        const { data } = await axios.post(`${API_URL}/api/v1/auth/refresh`, {
          refresh_token: refreshToken,
        });
        localStorage.setItem("access_token", data.access_token);
        localStorage.setItem("refresh_token", data.refresh_token);
        api.defaults.headers.common.Authorization = `Bearer ${data.access_token}`;
        processQueue(null, data.access_token);
        originalRequest.headers.Authorization = `Bearer ${data.access_token}`;
        return api(originalRequest);
      } catch (refreshError) {
        processQueue(refreshError as Error, null);
        localStorage.clear();
        window.location.href = "/login";
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
  }
);

// Helpers typés
export const authApi = {
  register: (data: { phone: string; email: string; password: string; first_name: string; last_name: string; account_type?: "customer" | "company"; company_name?: string; company_type?: string }) =>
    api.post("/auth/register", data),
  requestOTP: (email: string, password: string) => api.post("/auth/login/request-otp", { email, password }),
  verifyOTP: (email: string, code: string) =>
    api.post("/auth/login/verify-otp", { email, code }),
  staffLogin: (email: string, password: string) =>
    api.post("/auth/staff/login", { email, password }),
  refresh: (token: string) => api.post("/auth/refresh", { refresh_token: token }),
  logout: (token: string) => api.post("/auth/logout", { refresh_token: token }),
  me: () => api.get("/auth/me"),
  updateMe: (data: object) => api.patch("/auth/me", data),
  forgotPassword: (email: string) => api.post("/auth/forgot-password", { email }),
  requestEmailVerification: () => api.post("/auth/request-email-verification"),
  verifyEmail: (token: string) => api.post("/auth/verify-email", { token }),
  resetPassword: (token: string, newPassword: string) =>
    api.post("/auth/reset-password", { token, new_password: newPassword }),
  getStaff: () => api.get("/auth/staff"),
  inviteStaff: (data: object) => api.post("/auth/staff/invite", data),
  removeStaff: (userId: string) => api.delete(`/auth/staff/${userId}`),
};

export const storesApi = {
  getNearby: () => api.get("/stores/nearby"),
  getById: (id: string) => api.get(`/stores/${id}`),
  getMyStore: () => api.get("/stores/me"),
  updateMyStore: (data: object) => api.patch("/stores/me", data),
  getAllCompanies: (params?: Record<string, any>) =>
    api.get("/superadmin/companies", { params }),
  getPlatformStats: () => api.get("/superadmin/stats"),
  suspendCompany: (companyId: string, suspend: boolean) =>
    api.patch(`/superadmin/companies/${companyId}/suspend`, { suspend }),
};

export const superadminApi = {
  getCompanies: (params?: Record<string, any>) => api.get("/superadmin/companies", { params }),
  getStats: () => api.get("/superadmin/stats"),
  getUsers: (params?: Record<string, any>) => api.get("/superadmin/users", { params }),
  deactivateUser: (userId: string) => api.patch(`/users/${userId}/deactivate`),
  reactivateUser: (userId: string) => api.patch(`/users/${userId}/reactivate`),
  getRegistrationRequests: (params?: Record<string, any>) =>
    api.get("/companies/registration-requests", { params }),
  approveRegistrationRequest: (requestId: string) =>
    api.post(`/companies/registration-requests/${requestId}/approve`),
  rejectRegistrationRequest: (requestId: string, reason?: string) =>
    api.post(`/companies/registration-requests/${requestId}/reject`, { reason }),
  getAuditLogs: (params?: { company_id?: string; action?: string; limit?: number }) =>
    api.get("/superadmin/audit-logs", { params }),
  createPlan: (data: { code: string; name: string; billing_cycle: string; amount_xof: number; commission_rate: number; features?: Record<string, any> }) =>
    api.post("/superadmin/plans", data),
  activateCompany: (companyId: string) =>
    api.post(`/superadmin/companies/${companyId}/activate`),
};

export const companiesApi = {
  create: (data: object) => api.post("/companies/", data),
  getById: (companyId: string) => api.get(`/companies/${companyId}`),
  getMySettings: () => api.get("/companies/me/settings"),
  updateMySettings: (data: object) => api.patch("/companies/me/settings", data),
  getMyCatalog: (storeId?: string) => api.get("/companies/me/catalog", { params: { store_id: storeId } }),
  updateMyCatalog: (data: object) => api.put("/companies/me/catalog", data),
  getMyFeatureFlags: () => api.get("/companies/me/feature-flags"),
  upsertMyFeatureFlag: (data: object) => api.put("/companies/me/feature-flags", data),
  getPlans: () => api.get("/companies/plans"),
  getMySubscription: () => api.get("/companies/me/subscription"),
  changeSubscription: (planCode: string) =>
    api.post("/companies/me/subscription/change", { plan_code: planCode }),
  getMySubscriptionInvoices: () => api.get("/companies/me/subscription/invoices"),
  getMySubscriptionRenewals: () => api.get("/companies/me/subscription/renewals"),
  cancelMySubscription: () => api.post("/companies/me/subscription/cancel"),
  payMySubscriptionInvoice: (invoiceId: string) =>
    api.post(`/companies/me/subscription/invoices/${invoiceId}/pay`),
};

export const catalogApi = {
  getCategories: (storeIdOrParams?: string | Record<string, any>, companyId?: string) => {
    if (typeof storeIdOrParams === "string") {
      return api.get(`/catalog/stores/${storeIdOrParams}/categories`, {
        params: { company_id: companyId },
      });
    }
    return api.get("/catalog/categories", { params: storeIdOrParams });
  },
  getProducts: (storeIdOrParams?: string | Record<string, any>, companyId?: string, extra?: Record<string, any>) => {
    if (typeof storeIdOrParams === "string") {
      return api.get(`/catalog/stores/${storeIdOrParams}/products`, {
        params: { company_id: companyId, ...extra },
      });
    }
    return api.get("/catalog/products", { params: storeIdOrParams });
  },
  getByBarcode: (barcode: string, storeId?: string) =>
    api.get(`/catalog/products/barcode/${barcode}`, { params: { store_id: storeId } }),
  createProduct: (data: object) => api.post("/catalog/products", data),
  updateProduct: (productId: string, data: object) => api.patch(`/catalog/products/${productId}`, data),
  deleteProduct: (id: string) => api.delete(`/catalog/products/${id}`),
  adjustStock: (productId: string, data: object) =>
    api.post(`/catalog/products/${productId}/stock`, data),
  importCSV: (formData: FormData) =>
    api.post("/catalog/products/import", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    }),
  getImportJobs: () => api.get("/catalog/import-jobs"),
  getImportErrors: (jobId: string) => api.get(`/catalog/import-jobs/${jobId}/errors`),
};

export const ordersApi = {
  getCart: (storeId: string, companyId: string) =>
    api.get("/orders/cart", { params: { store_id: storeId, company_id: companyId } }),
  addToCart: (storeId: string, companyId: string, productId: string, quantity: number) =>
    api.post(`/orders/cart/items?store_id=${storeId}&company_id=${companyId}`, {
      product_id: productId,
      quantity,
    }),
  createOrder: (data: object) => api.post("/orders/", data),
  createScanGoOrder: (data: object) => api.post("/orders/scan-go", data),
  getMyOrders: (page = 1) => api.get("/orders/my", { params: { page } }),
  getOrderDetail: (id: string) => api.get(`/orders/${id}`),
  getOne: (id: string) => api.get(`/orders/${id}`),
  getMerchantOrders: (status?: string) =>
    api.get("/orders/merchant/pending", { params: { status } }),
  updateStatus: (id: string, status: string, reason?: string) =>
    api.patch(`/orders/${id}/status`, { status, reason }),
};

export const paymentsApi = {
  create: (data: object) => api.post("/payments/", data),
  submitProof: (paymentId: string, data: object) =>
    api.post(`/payments/${paymentId}/submit-proof`, data),
  confirm: (paymentId: string, confirmed: boolean, reason?: string) =>
    api.post(`/payments/${paymentId}/confirm`, { confirmed, reason }),
  getPending: () => api.get("/payments/pending"),
};

export const receiptsApi = {
  getMyReceipts: () => api.get("/receipts/my"),
  getMerchantReceipts: (params?: Record<string, any>) => api.get("/receipts/merchant", { params }),
  getByOrder: (orderId: string) => api.get(`/receipts/order/${orderId}`),
  generate: (paymentId: string) => api.post(`/receipts/generate/${paymentId}`),
  getOne: (id: string) => api.get(`/receipts/${id}`),
  getById: (id: string) => api.get(`/receipts/${id}`),
  getHtml: (id: string) => api.get(`/receipts/${id}/html`),
  getQr: (id: string) => api.get(`/receipts/${id}/qr`),
  verify: (code: string) => api.get(`/receipts/verify/${code}`),
};

export const reportsApi = {
  getDashboard: () => api.get("/reports/dashboard"),
  getSummary: (params: object) => api.get("/reports/summary", { params }),
  getSales: (dateFrom: string, dateTo: string) =>
    api.get("/reports/sales", { params: { date_from: dateFrom, date_to: dateTo } }),
  export: (format: "csv" | "excel" | "pdf", params: object) =>
    api.get(`/reports/export/${format}`, { params, responseType: "blob" }),
};

export const notificationsApi = {
  getAll: () => api.get("/notifications/"),
  getSummary: () => api.get("/notifications/summary"),
  markRead: (notificationId: string) => api.post(`/notifications/${notificationId}/read`),
  markAllRead: () => api.post("/notifications/mark-all-read"),
  getTemplates: () => api.get("/notifications/templates"),
  upsertTemplate: (data: object) => api.put("/notifications/templates", data),
  getEvents: (params?: Record<string, any>) => api.get("/notifications/events", { params }),
};

export const supportApi = {
  getTickets: (params?: Record<string, any>) => api.get("/support/tickets", { params }),
  getTicket: (ticketId: string) => api.get(`/support/tickets/${ticketId}`),
  createTicket: (data: object) => api.post("/support/tickets", data),
  replyTicket: (ticketId: string, data: object) => api.post(`/support/tickets/${ticketId}/reply`, data),
  updateTicket: (ticketId: string, data: object) => api.patch(`/support/tickets/${ticketId}`, data),
};

export const walletApi = {
  getMyMethods: () => api.get("/wallet/methods"),
  createMethod: (data: object) => api.post("/wallet/methods", data),
  updateMethod: (methodId: string, data: object) => api.patch(`/wallet/methods/${methodId}`, data),
  deleteMethod: (methodId: string) => api.delete(`/wallet/methods/${methodId}`),
  getCompanyMethods: () => api.get("/wallet/company-methods"),
};

export const loyaltyApi = {
  // Client — cartes
  getMyCards: () => api.get("/loyalty/cards/mine"),
  getCardTransactions: (cardId: string) => api.get(`/loyalty/cards/${cardId}/transactions`),
  importExternalCard: (data: object) => api.post("/loyalty/cards/import", data),

  // Client — coupons
  getMyCoupons: (customerId: string) => api.get(`/loyalty/coupons/customer/${customerId}`),
  applyCoupon: (code: string, orderId: string) =>
    api.post(`/loyalty/coupons/${code}/apply?order_id=${orderId}`),

  // Client — récompenses (rachat de points)
  redeemPoints: (cardId: string, data: object) => api.post(`/loyalty/cards/${cardId}/redeem`, data),

  // Marchand — programmes
  getPrograms: () => api.get("/loyalty/programs"),
  createProgram: (data: object) => api.post("/loyalty/programs", data),
  updateProgram: (id: string, data: object) => api.patch(`/loyalty/programs/${id}`, data),
  activateProgram: (id: string) => api.post(`/loyalty/programs/${id}/activate`),
  deactivateProgram: (id: string) => api.post(`/loyalty/programs/${id}/deactivate`),

  // Marchand — niveaux
  getTiers: (programId: string) => api.get(`/loyalty/programs/${programId}/tiers`),
  createTier: (programId: string, data: object) => api.post(`/loyalty/programs/${programId}/tiers`, data),

  // Marchand — récompenses
  getRewards: (programId: string) => api.get(`/loyalty/programs/${programId}/rewards`),
  createReward: (programId: string, data: object) => api.post(`/loyalty/programs/${programId}/rewards`, data),

  // Marchand — templates de cartes
  getCardTemplates: () => api.get("/loyalty/card-templates"),
  createCardTemplate: (data: object) => api.post("/loyalty/card-templates", data),

  // Marchand — cartes clients
  getCustomerCards: (customerId: string) => api.get(`/loyalty/customers/${customerId}/cards`),
  issueCard: (data: object) => api.post("/loyalty/cards/issue", data),
  importCard: (data: object) => api.post("/loyalty/cards/import", data),
  earnPoints: (cardId: string, data: object) => api.post(`/loyalty/cards/${cardId}/earn`, data),

  // Marchand — coupons
  getCoupons: (customerId: string) => api.get(`/loyalty/coupons/customer/${customerId}`),
  issueCoupon: (data: object) => api.post("/loyalty/coupons/issue", data),

  // Marchand — intelligence RFM
  getCustomerScores: (params?: { segment?: string; limit?: number }) =>
    api.get("/loyalty/intelligence/customers", { params }),
  recomputeScores: () => api.post("/loyalty/intelligence/recompute"),
  getCustomerProfile: (customerId: string) =>
    api.get(`/loyalty/customers/${customerId}/profile`),
};

export const integrationsApi = {
  getWebhooks: () => api.get("/integrations/webhooks"),
  createWebhook: (data: object) => api.post("/integrations/webhooks", data),
  updateWebhook: (webhookId: string, data: object) => api.patch(`/integrations/webhooks/${webhookId}`, data),
  deleteWebhook: (webhookId: string) => api.delete(`/integrations/webhooks/${webhookId}`),
  getWebhookDeliveries: () => api.get("/integrations/webhooks/deliveries"),
  testWebhook: (webhookId: string) => api.post(`/integrations/webhooks/${webhookId}/test`),
  getApiKey: () => api.get("/integrations/api-key"),
  regenerateApiKey: () => api.post("/integrations/api-key/regenerate"),
};
