export type Surface = "phone" | "dayform" | "stride" | "desktop";
export type Product = {
  id: string;
  app: "dayform" | "stride";
  name: string;
  color: string;
  price: number;
  fit: string;
  cushioning: string;
  arrival: string;
  sizes: number[];
  image: string;
  description: string;
};
export type Message = {
  id: string;
  role: string;
  content: string;
  source: Surface;
  at: string;
  kind?: string;
  quoteId?: string;
  orderId?: string;
  modelFallback?: boolean;
  context?: { productId?: string; size?: number; sessionId?: string };
};
export type Quote = {
  id: string;
  product: Product;
  size: number;
  subtotal: number;
  shipping: number;
  tax: number;
  total: number;
  source: Surface;
  expiresAt: number;
  status: string;
};
export type Order = Quote & { quoteId: string; at: string };
export type Snapshot = {
  id: string;
  revision: number;
  preferences: { budget: number; size: number; priority: string };
  grants: Record<
    "dayform" | "stride",
    { connected: boolean; shareBudget: boolean }
  >;
  messages: Message[];
  candidates: string[];
  quote: Quote | null;
  orders: Order[];
  products: Product[];
  taskStatus: string;
  stock: Record<string, number>;
  events: {
    id: string;
    type: string;
    source: string;
    description: string;
    details: Record<string, unknown>;
    at: string;
  }[];
  mode: "demo" | "live";
};
