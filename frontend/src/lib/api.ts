
const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000"
).replace(/\/$/, "");

const API_PREFIX = `${API_BASE_URL}/api/v1`;
const TOKEN_KEY = "mediflow_access_token";

export type UserRole = "customer" | "pharmacist" | "admin";

export interface User {
  id: number;
  full_name: string;
  email: string;
  phone: string | null;
  role: UserRole;
  is_active: boolean;
  created_at: string;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export interface RegisterPayload {
  full_name: string;
  email: string;
  phone?: string;
  password: string;
}

interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export type PrescriptionStatus =
  | "uploaded"
  | "processing"
  | "reupload_required"
  | "approved"
  | "rejected";

export interface Prescription {
  id: number;
  original_filename: string;
  mime_type: string;
  status: PrescriptionStatus;
  ai_extraction_json: Record<string, unknown> | null;
  created_at: string;
}

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export function getToken(): string | null {
  return sessionStorage.getItem(TOKEN_KEY);
}

export function saveToken(token: string): void {
  sessionStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  sessionStorage.removeItem(TOKEN_KEY);
}

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const headers = new Headers(options.headers);

  if (
    options.body &&
    !(options.body instanceof FormData) &&
    !headers.has("Content-Type")
  ) {
    headers.set("Content-Type", "application/json");
  }

  const token = getToken();

  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  let response: Response;

  try {
    response = await fetch(`${API_PREFIX}${path}`, {
      ...options,
      headers,
    });
  } catch {
    throw new ApiError(
      "Unable to connect to MediFlow. Please check whether the backend is running.",
      0,
    );
  }

  if (!response.ok) {
    let message = "Something went wrong. Please try again.";

    try {
      const errorData = await response.json();

      if (typeof errorData.detail === "string") {
        message = errorData.detail;
      } else if (Array.isArray(errorData.detail)) {
        message = errorData.detail
          .map((item: { msg?: string }) => item.msg ?? "Invalid input")
          .join(", ");
      }
    } catch {
      // Keep the default error message.
    }

    throw new ApiError(message, response.status);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

export const authApi = {
  async login(payload: LoginPayload): Promise<TokenResponse> {
    return request<TokenResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  async devLogin(): Promise<TokenResponse> {
    return request<TokenResponse>("/auth/dev-login", {
      method: "POST",
    });
  },

  async register(payload: RegisterPayload): Promise<User> {
    return request<User>("/auth/register", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  async getCurrentUser(): Promise<User> {
    return request<User>("/auth/me");
  },
};

export const prescriptionApi = {
  async upload(file: File): Promise<Prescription> {
    const formData = new FormData();
    formData.append("file", file);

    return request<Prescription>("/prescriptions/upload", {
      method: "POST",
      body: formData,
    });
  },

  async getMyPrescriptions(): Promise<Prescription[]> {
    return request<Prescription[]>("/prescriptions/my");
  },
};

export interface PharmacistQueueItem {
  id: number;
  customer_id: number;
  customer_name: string;
  customer_email: string;
  original_filename: string;
  mime_type: string;
  status: string;
  ai_extraction_json: Record<string, unknown> | null;
  created_at: string;
}

export interface PharmacistPrescriptionItem {
  id: number;
  medicine_id: number | null;
  extracted_name: string;
  dosage: string | null;
  quantity: number | null;
  pharmacist_approved: boolean;
  generic_substitution: boolean;
  customer_consent: boolean;
}

export interface PharmacistPrescriptionDetail
  extends PharmacistQueueItem {
  rejection_reason: string | null;
  items: PharmacistPrescriptionItem[];
}

export interface PharmacistMedicine {
  id: number;
  name: string;
  generic_name: string | null;
  brand_name: string | null;
  strength: string | null;
  dosage_form: string | null;
  schedule_category: string;
  requires_prescription: boolean;
}

export interface PrescriptionReviewPayload {
  decision: "approved" | "rejected";
  medicines?: Array<{
    medicine_id: number;
    quantity: number;
    dosage?: string;
    generic_substitution?: boolean;
    customer_consent?: boolean;
  }>;
  rejection_reason?: string;
}

export interface PrescriptionReviewResponse {
  id: number;
  status: string;
  pharmacist_id: number;
  rejection_reason: string | null;
  reviewed_at: string;
}

export const pharmacistApi = {
  async getQueue(): Promise<PharmacistQueueItem[]> {
    return request<PharmacistQueueItem[]>(
      "/pharmacist/prescriptions/queue",
    );
  },

  async getPrescription(
    prescriptionId: number,
  ): Promise<PharmacistPrescriptionDetail> {
    return request<PharmacistPrescriptionDetail>(
      `/pharmacist/prescriptions/${prescriptionId}`,
    );
  },

  async getMedicines(): Promise<PharmacistMedicine[]> {
    return request<PharmacistMedicine[]>("/pharmacist/medicines");
  },

  async reviewPrescription(
    prescriptionId: number,
    payload: PrescriptionReviewPayload,
  ): Promise<PrescriptionReviewResponse> {
    return request<PrescriptionReviewResponse>(
      `/pharmacist/prescriptions/${prescriptionId}/review`,
      {
        method: "POST",
        body: JSON.stringify(payload),
      },
    );
  },
};

export interface OrderItemResponse {
  id: number;
  medicine_id: number;
  quantity: number;
  unit_price: number;
}

export type OrderStatus =
  | "pending_review"
  | "confirmed"
  | "preparing"
  | "ready"
  | "dispatched"
  | "delivered"
  | "cancelled";

export type OrderStatusUpdate =
  | "preparing"
  | "ready"
  | "dispatched"
  | "delivered"
  | "cancelled";

export interface OrderResponse {
  id: number;
  order_number: string;
  customer_id: number;
  store_id: number | null;
  prescription_id: number | null;
  status: OrderStatus;
  total_amount: number;
  created_at: string;
  items: OrderItemResponse[];
}

export interface OrderCreatePayload {
  prescription_id: number;
  customer_latitude?: number;
  customer_longitude?: number;
}

export const orderApi = {
  async createOrder(
    payload: OrderCreatePayload,
  ): Promise<OrderResponse> {
    return request<OrderResponse>("/orders", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  async getMyOrders(): Promise<OrderResponse[]> {
    return request<OrderResponse[]>("/orders");
  },

  async getOrder(orderId: number): Promise<OrderResponse> {
    return request<OrderResponse>(`/orders/${orderId}`);
  },

  async getAllOrders(): Promise<OrderResponse[]> {
    return request<OrderResponse[]>("/orders/manage");
  },

  async updateOrderStatus(
    orderId: number,
    newStatus: OrderStatusUpdate,
  ): Promise<OrderResponse> {
    return request<OrderResponse>(`/orders/${orderId}/status`, {
      method: "PATCH",
      body: JSON.stringify({ status: newStatus }),
    });
  },
};


export interface AdminUserListResponse {
  users: User[];
  total: number;
}

export interface AdminUserUpdatePayload {
  role?: UserRole;
  is_active?: boolean;
}

export interface AdminStore {
  id: number;
  name: string;
  address: string;
  city: string;
  pincode: string;
  latitude: number | null;
  longitude: number | null;
  is_active: boolean;
  created_at: string;
}

export interface AdminStoreListResponse {
  stores: AdminStore[];
  total: number;
}

export interface AdminStoreUpdatePayload {
  name?: string;
  address?: string;
  city?: string;
  pincode?: string;
  latitude?: number | null;
  longitude?: number | null;
  is_active?: boolean;
}

export interface AdminPlatformOverview {
  users: Record<string, number>;
  stores: Record<string, number>;
  orders: Record<string, number>;
  prescriptions: Record<string, number>;
  inventory: Record<string, number>;
}

export const adminApi = {
  async getUsers(params: {
    search?: string;
    role?: UserRole;
    is_active?: boolean;
    skip?: number;
    limit?: number;
  } = {}): Promise<AdminUserListResponse> {
    const query = new URLSearchParams();

    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== "") {
        query.set(key, String(value));
      }
    });

    const suffix = query.toString() ? `?${query.toString()}` : "";
    return request<AdminUserListResponse>(`/admin/users${suffix}`);
  },

  async updateUser(
    userId: number,
    payload: AdminUserUpdatePayload,
  ): Promise<User> {
    return request<User>(`/admin/users/${userId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
  },

  async getStores(params: {
    search?: string;
    is_active?: boolean;
    skip?: number;
    limit?: number;
  } = {}): Promise<AdminStoreListResponse> {
    const query = new URLSearchParams();

    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== "") {
        query.set(key, String(value));
      }
    });

    const suffix = query.toString() ? `?${query.toString()}` : "";
    return request<AdminStoreListResponse>(`/admin/stores${suffix}`);
  },

  async getStore(storeId: number): Promise<AdminStore> {
    return request<AdminStore>(`/admin/stores/${storeId}`);
  },

  async updateStore(
    storeId: number,
    payload: AdminStoreUpdatePayload,
  ): Promise<AdminStore> {
    return request<AdminStore>(`/admin/stores/${storeId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
  },

  async getOverview(): Promise<AdminPlatformOverview> {
    return request<AdminPlatformOverview>("/admin/overview");
  },
};


export type RefillPlanStatus =
  | "pending_review"
  | "active"
  | "paused"
  | "rejected"
  | "cancelled";

export type RefillRequestStatus =
  | "pending_review"
  | "approved"
  | "rejected"
  | "cancelled";

export interface RefillPlan {
  id: number;
  customer_id: number;
  prescription_id: number;
  interval_days: number;
  status: RefillPlanStatus;
  next_refill_at: string | null;
  reviewed_by: number | null;
  reviewed_at: string | null;
  review_note: string | null;
  created_at: string;
}

export interface RefillRequest {
  id: number;
  plan_id: number;
  status: RefillRequestStatus;
  reviewed_by: number | null;
  reviewed_at: string | null;
  review_note: string | null;
  order_id: number | null;
  created_at: string;
}

export interface RefillPlanCreatePayload {
  prescription_id: number;
  interval_days: number;
}

export interface RefillReviewPayload {
  decision: "approved" | "rejected";
  review_note?: string;
}

export interface RefillRequestReviewResponse {
  refill_request: RefillRequest;
  order: {
    id: number;
    status: string;
    [key: string]: unknown;
  } | null;
}

export const refillApi = {
  // Customer: create a refill plan.
  async createPlan(
    payload: RefillPlanCreatePayload,
  ): Promise<RefillPlan> {
    return request<RefillPlan>("/refills/plans", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  // Customer: view personal refill plans.
  async getMyPlans(): Promise<RefillPlan[]> {
    return request<RefillPlan[]>("/refills/plans/my");
  },

  // Customer: pause, resume, or cancel a refill plan.
  async updatePlanStatus(
    planId: number,
    newStatus: "paused" | "active" | "cancelled",
  ): Promise<RefillPlan> {
    const query = new URLSearchParams({
      new_status: newStatus,
    });

    return request<RefillPlan>(
      `/refills/plans/${planId}/status?${query.toString()}`,
      {
        method: "PATCH",
      },
    );
  },

  // Pharmacist/admin: view plans awaiting review.
  async getPlanQueue(): Promise<RefillPlan[]> {
    return request<RefillPlan[]>("/refills/plans/queue");
  },

  // Pharmacist/admin: approve or reject a refill plan.
  async reviewPlan(
    planId: number,
    payload: RefillReviewPayload,
  ): Promise<RefillPlan> {
    return request<RefillPlan>(
      `/refills/plans/${planId}/review`,
      {
        method: "PATCH",
        body: JSON.stringify(payload),
      },
    );
  },

  // Customer: request a refill when the plan is due.
  async createRequest(planId: number): Promise<RefillRequest> {
    return request<RefillRequest>(
      `/refills/plans/${planId}/requests`,
      {
        method: "POST",
      },
    );
  },

  // Customer: view personal refill requests.
  async getMyRequests(): Promise<RefillRequest[]> {
    return request<RefillRequest[]>("/refills/requests/my");
  },

  // Pharmacist/admin: view requests awaiting review.
  async getRequestQueue(): Promise<RefillRequest[]> {
    return request<RefillRequest[]>("/refills/requests/queue");
  },

  // Pharmacist/admin: approve or reject a refill request.
  async reviewRequest(
    requestId: number,
    payload: RefillReviewPayload,
  ): Promise<RefillRequestReviewResponse> {
    return request<RefillRequestReviewResponse>(
      `/refills/requests/${requestId}/review`,
      {
        method: "PATCH",
        body: JSON.stringify(payload),
      },
    );
  },
};
