export type UserRole = "CLIENT" | "ORGANIZER" | "GATEKEEPER";

export interface User {
  id: string;
  name: string;
  email: string;
  role: UserRole;
  created_at?: string;
}

export interface Event {
  id: string;
  title: string;
  description?: string;
  poster_url?: string;
  event_date: string;
  venue_name: string;
  type: "SEATED" | "PISTA";
  capacity: number;
  price: number;
  external_tmdb_id?: string;
  genre?: string;
  director?: string;
  age_rating?: string;
  release_date?: string;
  vote_average?: number;
  cast?: TmdbCastMember[];
  created_at?: string;
}

export interface TmdbCastMember {
  name: string;
  character?: string;
  profile_path?: string;
}

export interface TmdbMovie {
  id: number;
  title: string;
  overview?: string;
  poster_path?: string;
  release_date?: string;
  genres?: string[];
  vote_average?: number;
  popularity?: number;
  director?: string;
  age_rating?: string;
  cast?: TmdbCastMember[];
}

export interface TmdbTrendingResponse {
  results: TmdbMovie[];
  time_window: string;
}

export interface EventAnalytics {
  event_id: string;
  title: string;
  capacity: number;
  total_sold: number;
  available_seats: number;
  revenue: number;
  occupied_seats: string[];
}

export interface Seat {
  id: string;
  event_id: string;
  seat_number: string;
  status: "AVAILABLE" | "PENDING" | "RESERVED";
}

export interface Ticket {
  id: string;
  event_id: string;
  client_id: string;
  seat_id?: string;
  purchase_price: number;
  qr_code_token: string;
  share_link_hash: string;
  status: "VALID" | "USED" | "CANCELLED";
  created_at: string;
  event?: Event;
  seat?: Seat;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
}

export interface PaginatedEvents {
  events: Event[];
  total: number;
  page: number;
  page_size: number;
}
