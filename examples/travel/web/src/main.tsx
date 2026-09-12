import React, { useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  ArrowRight,
  ArrowUp,
  Check,
  ChevronRight,
  Clock3,
  Compass,
  Hotel,
  MapPin,
  MessageCircle,
  Orbit,
  Plane,
  Plus,
  RotateCcw,
  ShieldCheck,
  Sparkles,
  Star,
  Wallet,
  X,
} from "lucide-react";
import "./style.css";

type AppId = "home" | "flights" | "hotels";
type Flight = {
  id: string;
  name: string;
  code: string;
  departure_airport: string;
  arrival_airport: string;
  departure_at: string;
  arrival_at: string;
  duration: string;
  price_cents: number;
  baggage: string;
  tag: string;
  description: string;
};
type Stay = {
  id: string;
  name: string;
  neighborhood: string;
  style: string;
  nightly_cents: number;
  rating: number;
  reviews: number;
  check_in_from: string;
  check_in_until: string;
  late_check_in: boolean;
  amenities: string[];
  quiet: boolean;
  description: string;
  image: string;
};
type Trip = {
  budget_cents: number;
  preferences: string;
  flight_id: string | null;
  hotel_id: string | null;
  flight: Flight | null;
  hotel: Stay | null;
  total_cents: number;
  remaining_cents: number;
  warnings: string[];
  nights: number;
  estimated_hotel_arrival?: string;
};
type Proposal = {
  name: string;
  arguments: { id?: string; budget_cents?: number; preferences?: string };
};
type Output = {
  id: string;
  in_reply_to: string;
  text: string;
  shared_context: Record<string, unknown>;
  proposal?: Proposal;
};
type Event = {
  event_id: string;
  message: { id: string; text: string };
  context: { selected_object?: { name: string } };
};
type Transcript = {
  messages: Event[];
  outputs: Output[];
  running: boolean;
  error: string | null;
};
type Bootstrap = {
  visitor: string;
  csrf: string;
  trip: Trip;
  catalog: { flights: Flight[]; hotels: Stay[] };
  mode: string;
};
let csrfToken = "";
const money = (cents: number) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(cents / 100);
const localTime = (iso: string) => iso.slice(11, 16);
const titles: Record<AppId, string> = {
  home: "Your trip",
  flights: "Airside",
  hotels: "Staywell",
};
const emptyTranscript: Transcript = {
  messages: [],
  outputs: [],
  running: false,
  error: null,
};
async function api<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch("/api/" + path, {
    method: body === undefined ? "GET" : "POST",
    credentials: "same-origin",
    headers:
      body === undefined
        ? {}
        : { "Content-Type": "application/json", "X-CSRF-Token": csrfToken },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "Request failed");
  return data;
}
const id = () => crypto.randomUUID();
function readSessions(): Partial<Record<AppId, string>> {
  try {
    return JSON.parse(sessionStorage.getItem("oneagent-sessions") || "{}");
  } catch {
    return {};
  }
}
function startingApp(): AppId {
  const route = location.pathname.slice(1);
  return route === "flights" || route === "hotels" ? route : "home";
}

function App() {
  const [boot, setBoot] = useState<Bootstrap | null>(null);
  const [trip, setTrip] = useState<Trip | null>(null);
  const [app, setApp] = useState<AppId>(startingApp);
  const appRef = useRef(app);
  appRef.current = app;
  const [sessions, setSessions] =
    useState<Partial<Record<AppId, string>>>(readSessions);
  const [selected, setSelected] = useState<Record<AppId, string | null>>({
    home: null,
    flights: null,
    hotels: null,
  });
  const [transcript, setTranscript] = useState<Transcript>(emptyTranscript);
  const [error, setError] = useState("");
  const [toast, setToast] = useState("");
  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);
  const [sharing, setSharing] = useState(false);
  const [mobileChat, setMobileChat] = useState(false);
  const [budget, setBudget] = useState("1500");
  const [preferences, setPreferences] = useState("");
  const [sort, setSort] = useState("recommended");
  const [quietOnly, setQuietOnly] = useState(false);
  const [actionPending, setActionPending] = useState(false);
  const logEnd = useRef<HTMLDivElement>(null);
  const sessionPromise = useRef<Partial<Record<AppId, Promise<string>>>>({});

  useEffect(() => {
    api<Bootstrap>("session")
      .then((data) => {
        csrfToken = data.csrf;
        if (sessionStorage.getItem("oneagent-visitor") !== data.visitor) {
          sessionStorage.removeItem("oneagent-sessions");
          setSessions({});
          sessionPromise.current = {};
          sessionStorage.setItem("oneagent-visitor", data.visitor);
        }
        setBoot(data);
        setTrip(data.trip);
        setBudget(String(data.trip.budget_cents / 100));
        setPreferences(data.trip.preferences);
      })
      .catch((e) => setError(e.message));
  }, []);
  useEffect(() => {
    const onPop = () => {
      setApp(startingApp());
      setTranscript(emptyTranscript);
    };
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, []);
  useEffect(() => {
    if (toast) {
      const timer = setTimeout(() => setToast(""), 4500);
      return () => clearTimeout(timer);
    }
  }, [toast]);
  useEffect(() => {
    const log = logEnd.current?.parentElement;
    if (log) log.scrollTo({ top: log.scrollHeight, behavior: "smooth" });
  }, [transcript.messages.length, transcript.outputs.length, sending]);

  async function ensureSession(target: AppId): Promise<string> {
    if (sessions[target]) return sessions[target]!;
    if (!sessionPromise.current[target])
      sessionPromise.current[target] = api<{ session_id: string }>("sessions", {
        app_id: target,
      })
        .then((data) => {
          setSessions((previous) => {
            const next = { ...previous, [target]: data.session_id };
            sessionStorage.setItem("oneagent-sessions", JSON.stringify(next));
            return next;
          });
          return data.session_id;
        })
        .catch((error) => {
          delete sessionPromise.current[target];
          throw error;
        });
    return sessionPromise.current[target]!;
  }

  useEffect(() => {
    if (!boot) return;
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout>;
    async function refresh() {
      try {
        const session = await ensureSession(app);
        const [messages, updated] = await Promise.all([
          api<Transcript>(`transcript?app_id=${app}&session_id=${session}`),
          api<Trip>("trip"),
        ]);
        if (!cancelled) {
          setTranscript(messages);
          setTrip(updated);
        }
      } catch (e) {
        if (!cancelled) setError((e as Error).message);
      } finally {
        if (!cancelled) timer = setTimeout(refresh, 1400);
      }
    }
    refresh();
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [app, boot]);

  function navigate(target: AppId) {
    setApp(target);
    setTranscript(emptyTranscript);
    setSharing(false);
    setSort("recommended");
    history.pushState({}, "", target === "home" ? "/" : "/" + target);
  }
  const current =
    app === "flights"
      ? boot?.catalog.flights.find((f) => f.id === selected.flights)
      : app === "hotels"
        ? boot?.catalog.hotels.find((h) => h.id === selected.hotels)
        : null;
  async function send(text = draft) {
    if (!text.trim() || sending) return;
    const target = app;
    const messageId = id();
    setSending(true);
    setDraft("");
    setError("");
    setMobileChat(true);
    try {
      const session = await ensureSession(target);
      await api("messages", {
        id: messageId,
        app_id: target,
        session_id: session,
        text: text.trim(),
        context: { selected_id: selected[target], revision: Date.now() },
        share: sharing ? ["budget_cents", "preferences"] : [],
      });
      if (appRef.current === target)
        setTranscript((previous) => ({
          ...previous,
          running: true,
          messages: [
            ...previous.messages,
            {
              event_id: messageId,
              message: { id: messageId, text: text.trim() },
              context: current
                ? { selected_object: { name: current.name } }
                : {},
            },
          ],
        }));
    } catch (e) {
      setError((e as Error).message);
      if (appRef.current === target) setDraft(text);
    } finally {
      setSending(false);
    }
  }
  async function save(kind: "flight" | "hotel", itemId: string) {
    setActionPending(true);
    try {
      const updated = await api<Trip>("action", {
        id: id(),
        kind,
        item_id: itemId,
      });
      setTrip(updated);
      setToast(`${kind === "flight" ? "Flight" : "Hotel"} saved to your trip`);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setActionPending(false);
    }
  }
  async function confirmProposal(proposal: Proposal) {
    if (proposal.name !== "trip.update_brief")
      return save(
        proposal.name.endsWith("flight") ? "flight" : "hotel",
        proposal.arguments.id!,
      );
    setActionPending(true);
    try {
      const updated = await api<Trip>("action", {
        id: id(),
        kind: "brief",
        changes: proposal.arguments,
      });
      setTrip(updated);
      setBudget(String(updated.budget_cents / 100));
      setPreferences(updated.preferences);
      setToast("Your trip brief is updated");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setActionPending(false);
    }
  }
  async function updateBrief() {
    const value = Number(budget);
    if (!Number.isFinite(value) || value < 100 || value > 50000) {
      setError("Enter a budget between $100 and $50,000.");
      return;
    }
    setActionPending(true);
    try {
      const updated = await api<Trip>("preferences", {
        id: id(),
        budget_cents: Math.round(value * 100),
        preferences,
      });
      setTrip(updated);
      setToast("Your trip brief is updated");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setActionPending(false);
    }
  }
  async function newTrip() {
    if (!window.confirm("Start a fresh demo trip and conversation?")) return;
    try {
      await api("new-trip", {});
      sessionStorage.removeItem("oneagent-sessions");
      location.assign("/");
    } catch (e) {
      setError((e as Error).message);
    }
  }
  if (!boot || !trip)
    return (
      <main className="loading">
        <Orbit size={38} />
        <h1>Opening your trip</h1>
        <p>{error || "Connecting your personal agent…"}</p>
        {error && <button onClick={() => location.reload()}>Try again</button>}
      </main>
    );
  const pending = transcript.messages.some(
    (message) =>
      !transcript.outputs.some(
        (output) => output.in_reply_to === message.message.id,
      ),
  );
  const prompts =
    app === "home"
      ? [
          "Help me plan a relaxed arrival day.",
          "What should I consider before choosing a flight?",
        ]
      : app === "flights"
        ? [
            "Would this flight work for my trip?",
            "How does this compare with the previous flight?",
          ]
        : [
            "Does this work with my saved flight?",
            "Is this better than the previous hotel?",
          ];
  const flights = [...boot.catalog.flights].sort((a, b) =>
    sort === "price"
      ? a.price_cents - b.price_cents
      : sort === "arrival"
        ? a.arrival_at.localeCompare(b.arrival_at)
        : 0,
  );
  const hotels = [...boot.catalog.hotels]
    .filter((h) => !quietOnly || h.quiet)
    .sort((a, b) => (sort === "price" ? a.nightly_cents - b.nightly_cents : 0));

  return (
    <div className={`shell theme-${app}`}>
      <header className="topbar">
        <button
          className="wordmark"
          onClick={() => navigate("home")}
          aria-label="OneAgent trip home"
        >
          <Orbit size={29} strokeWidth={1.7} />
          oneagent<span className="demo-label">TRAVEL DEMO</span>
        </button>
        <div className="top-right">
          <span className="trip-location">
            <MapPin size={15} /> Tokyo, Japan
          </span>
          <button className="text-button" onClick={newTrip}>
            <Plus size={17} /> New trip
          </button>
        </div>
      </header>
      <nav className="app-nav" aria-label="Connected applications">
        {(["home", "flights", "hotels"] as AppId[]).map((target, i) => (
          <React.Fragment key={target}>
            {i > 0 && <span className="nav-connector" />}
            <button
              className={target === app ? "nav-item active" : "nav-item"}
              aria-current={target === app ? "page" : undefined}
              onClick={() => navigate(target)}
            >
              {target === "home" ? (
                <Compass size={19} />
              ) : target === "flights" ? (
                <Plane size={19} />
              ) : (
                <Hotel size={19} />
              )}
              <span>
                {titles[target]}
                <small>
                  {target === "home"
                    ? "Plan & preferences"
                    : target === "flights"
                      ? "Find a flight"
                      : "Find a stay"}
                </small>
              </span>
            </button>
          </React.Fragment>
        ))}
        <span className="continuity">
          <Orbit size={16} /> One agent, every app
        </span>
      </nav>
      <div className="workspace">
        <main className="main-content">
          {app === "home" && (
            <>
              <section className="trip-hero">
                <img
                  src="/images/tokyo.jpg"
                  alt="Tokyo skyline with Tokyo Tower"
                />
                <div className="hero-shade" />
                <div className="hero-copy">
                  <span className="eyebrow light">YOUR NEXT CHAPTER</span>
                  <h1>
                    A few days
                    <br />
                    in Tokyo.
                  </h1>
                  <div className="hero-details">
                    <span>06 — 09 NOV 2026</span>
                    <span>3 NIGHTS</span>
                    <span>1 TRAVELER</span>
                  </div>
                </div>
                <span className="image-credit">
                  Tokyo photograph · Enes / Unsplash
                </span>
              </section>
              <div className="section-title">
                <div>
                  <span className="eyebrow">MAKE IT YOURS</span>
                  <h2>A little context goes a long way.</h2>
                </div>
                <span className="step-pill">01 / THE BRIEF</span>
              </div>
              <section className="brief-card">
                <div className="brief-intro">
                  <div className="icon-box">
                    <Wallet size={23} />
                  </div>
                  <h3>What matters to you?</h3>
                  <p>
                    Your agent carries these details into every connected app.
                  </p>
                </div>
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    updateBrief();
                  }}
                  className="brief-form"
                >
                  <label>
                    Flight + hotel budget{" "}
                    <span className="field-note">USD</span>
                    <div className="money-input">
                      <span>$</span>
                      <input
                        aria-label="Trip budget in dollars"
                        type="number"
                        min="100"
                        max="50000"
                        step="1"
                        value={budget}
                        onChange={(e) => setBudget(e.target.value)}
                      />
                    </div>
                  </label>
                  <label>
                    Travel preferences
                    <textarea
                      maxLength={2000}
                      value={preferences}
                      onChange={(e) => setPreferences(e.target.value)}
                      placeholder="Quiet neighborhoods, a relaxed first day, good coffee…"
                      rows={2}
                    />
                  </label>
                  <button className="primary" disabled={actionPending}>
                    Update trip brief <ArrowRight size={17} />
                  </button>
                </form>
              </section>
              <div className="section-title">
                <div>
                  <span className="eyebrow">PIECE BY PIECE</span>
                  <h2>Your trip is taking shape.</h2>
                </div>
              </div>
              <div className="saved-grid">
                <button
                  className="saved-card"
                  onClick={() => navigate("flights")}
                >
                  <span className="saved-icon flight-icon">
                    <Plane size={24} />
                  </span>
                  <span className="saved-copy">
                    <small>YOUR FLIGHT</small>
                    <strong>
                      {trip.flight
                        ? `${trip.flight.name} · ${trip.flight.code}`
                        : "Find your way there"}
                    </strong>
                    <span>
                      {trip.flight
                        ? `${localTime(trip.flight.arrival_at)} arrival · ${trip.flight.arrival_airport} · ${money(trip.flight.price_cents)}`
                        : "Explore 4 flights from San Francisco"}
                    </span>
                  </span>
                  {trip.flight ? <Check size={20} /> : <ArrowRight size={20} />}
                </button>
                <button
                  className="saved-card"
                  onClick={() => navigate("hotels")}
                >
                  <span className="saved-icon hotel-icon">
                    <Hotel size={24} />
                  </span>
                  <span className="saved-copy">
                    <small>YOUR STAY</small>
                    <strong>
                      {trip.hotel?.name || "Find your place in the city"}
                    </strong>
                    <span>
                      {trip.hotel
                        ? `${trip.hotel.neighborhood} · 3 nights · ${money(trip.hotel.nightly_cents * 3)}`
                        : "Explore 4 Tokyo neighborhood stays"}
                    </span>
                  </span>
                  {trip.hotel ? <Check size={20} /> : <ArrowRight size={20} />}
                </button>
              </div>
            </>
          )}
          {app === "flights" && (
            <>
              <div className="app-heading">
                <span className="app-brand">
                  <Plane size={24} /> airside
                  <span>FLIGHTS, WITHOUT THE FUSS.</span>
                </span>
                <span className="connected-badge">
                  <Check size={14} /> Connected to OneAgent
                </span>
              </div>
              <div className="page-heading">
                <span className="eyebrow">THE JOURNEY STARTS HERE</span>
                <h1>Find your way to Tokyo.</h1>
                <p>Choose a flight. Your agent can help with the trade-offs.</p>
              </div>
              <div className="search-bar">
                <div>
                  <small>FROM</small>
                  <strong>
                    San Francisco <span>SFO</span>
                  </strong>
                </div>
                <ArrowRight size={20} />
                <div>
                  <small>TO</small>
                  <strong>
                    Tokyo <span>HND / NRT</span>
                  </strong>
                </div>
                <div className="search-date">
                  <small>DEPARTURE</small>
                  <strong>Nov 5, 2026</strong>
                </div>
                <span className="one-way">One way · 1 adult</span>
              </div>
              <div className="results-heading">
                <span>
                  <strong>4 flights</strong> · All nonstop
                </span>
                <label>
                  Sort by{" "}
                  <select
                    value={sort}
                    onChange={(e) => setSort(e.target.value)}
                    aria-label="Sort flights"
                  >
                    <option value="recommended">Recommended</option>
                    <option value="price">Lowest price</option>
                    <option value="arrival">Earliest arrival</option>
                  </select>
                </label>
              </div>
              <div className="flight-list">
                {flights.map((flight, index) => (
                  <article
                    key={flight.id}
                    className={`flight-card ${selected.flights === flight.id ? "selected" : ""}`}
                  >
                    <button
                      className="flight-select"
                      onClick={() =>
                        setSelected((p) => ({ ...p, flights: flight.id }))
                      }
                      aria-pressed={selected.flights === flight.id}
                      aria-label={`View ${flight.name} ${flight.code}`}
                    >
                      <div className={`carrier-icon carrier-${index}`}>
                        <Plane size={22} />
                      </div>
                      <div className="carrier">
                        <strong>{flight.name}</strong>
                        <span>{flight.code} · Economy</span>
                      </div>
                      <div className="flight-times">
                        <div>
                          <strong>{localTime(flight.departure_at)}</strong>
                          <span>SFO · Nov 5</span>
                        </div>
                        <div className="flight-path">
                          <small>{flight.duration}</small>
                          <span />
                          <small>Nonstop</small>
                        </div>
                        <div>
                          <strong>{localTime(flight.arrival_at)}</strong>
                          <span>{flight.arrival_airport} · Nov 6</span>
                        </div>
                      </div>
                      <div className="flight-price">
                        <strong>{money(flight.price_cents)}</strong>
                        <span>per traveler</span>
                      </div>
                      <ChevronRight className="flight-chevron" size={19} />
                    </button>
                    <div className="flight-footer">
                      <span className="tag">{flight.tag}</span>
                      <span>{flight.baggage}</span>
                      {trip.flight_id === flight.id && (
                        <span className="saved-label">
                          <Check size={14} /> Saved to trip
                        </span>
                      )}
                    </div>
                    {selected.flights === flight.id && (
                      <div className="selection-detail">
                        <p>{flight.description}</p>
                        <div>
                          <button
                            className="secondary"
                            onClick={() =>
                              send("Would this flight work for my trip?")
                            }
                            disabled={sending}
                          >
                            <MessageCircle size={16} /> Ask OneAgent
                          </button>
                          <button
                            className="primary small"
                            disabled={
                              actionPending || trip.flight_id === flight.id
                            }
                            onClick={() => save("flight", flight.id)}
                          >
                            {trip.flight_id === flight.id
                              ? "Saved"
                              : "Save flight"}
                            <Check size={16} />
                          </button>
                        </div>
                      </div>
                    )}
                  </article>
                ))}
              </div>
              <p className="catalog-note">
                Fictional flights for this demo. One-way fares include mock
                taxes. All times are local.
              </p>
            </>
          )}
          {app === "hotels" && (
            <>
              <div className="app-heading">
                <span className="app-brand stay-brand">
                  <Hotel size={24} /> staywell
                  <span>A PLACE THAT FEELS LIKE YOU.</span>
                </span>
                <span className="connected-badge">
                  <Check size={14} /> Connected to OneAgent
                </span>
              </div>
              <div className="page-heading">
                <span className="eyebrow">MAKE YOURSELF AT HOME</span>
                <h1>Somewhere to slow down.</h1>
                <p>Find your neighborhood, then find your stay.</p>
              </div>
              <div className="search-bar hotel-search">
                <div>
                  <small>DESTINATION</small>
                  <strong>Tokyo, Japan</strong>
                </div>
                <div>
                  <small>CHECK-IN</small>
                  <strong>Nov 6, 2026</strong>
                </div>
                <ArrowRight size={18} />
                <div>
                  <small>CHECK-OUT</small>
                  <strong>Nov 9, 2026</strong>
                </div>
                <span className="one-way">3 nights · 1 guest</span>
              </div>
              <div className="results-heading">
                <label className="quiet-filter">
                  <input
                    type="checkbox"
                    checked={quietOnly}
                    onChange={(e) => setQuietOnly(e.target.checked)}
                  />{" "}
                  Quiet neighborhoods
                </label>
                <label>
                  Sort by{" "}
                  <select
                    value={sort}
                    onChange={(e) => setSort(e.target.value)}
                    aria-label="Sort hotels"
                  >
                    <option value="recommended">Recommended</option>
                    <option value="price">Lowest price</option>
                  </select>
                </label>
              </div>
              <div className="hotel-grid">
                {hotels.map((hotel) => (
                  <article
                    className={`hotel-card ${selected.hotels === hotel.id ? "selected" : ""}`}
                    key={hotel.id}
                  >
                    <button
                      className="hotel-select"
                      onClick={() =>
                        setSelected((p) => ({ ...p, hotels: hotel.id }))
                      }
                      aria-pressed={selected.hotels === hotel.id}
                      aria-label={`View ${hotel.name}`}
                    >
                      <div className="hotel-image">
                        <img
                          src={hotel.image}
                          alt="Illustrative hotel bedroom; demo properties are fictional"
                        />
                        <span className="neighborhood">
                          <MapPin size={13} />
                          {hotel.neighborhood}
                        </span>
                        {trip.hotel_id === hotel.id && (
                          <span className="image-saved">
                            <Check size={15} /> Saved
                          </span>
                        )}
                      </div>
                      <div className="hotel-card-body">
                        <div className="hotel-title">
                          <h3>{hotel.name}</h3>
                          <span className="rating">
                            <Star size={13} />
                            {hotel.rating}
                          </span>
                        </div>
                        <p>{hotel.style}</p>
                        <div className="hotel-amenity">
                          <Clock3 size={14} />
                          {hotel.late_check_in
                            ? "24-hour reception"
                            : `Reception until ${hotel.check_in_until}`}
                        </div>
                        <div className="hotel-pricing">
                          <span>
                            <strong>{money(hotel.nightly_cents)}</strong> /
                            night
                          </span>
                          <span>{money(hotel.nightly_cents * 3)} total</span>
                        </div>
                      </div>
                    </button>
                    {selected.hotels === hotel.id && (
                      <div className="hotel-detail">
                        <p>{hotel.description}</p>
                        <div className="amenities">
                          {hotel.amenities.map((a) => (
                            <span key={a}>
                              <Check size={12} />
                              {a}
                            </span>
                          ))}
                        </div>
                        <div className="hotel-actions">
                          <button
                            className="secondary"
                            onClick={() =>
                              send("Does this hotel work with my saved flight?")
                            }
                            disabled={sending}
                          >
                            <MessageCircle size={15} /> Ask agent
                          </button>
                          <button
                            className="primary small"
                            disabled={
                              actionPending || trip.hotel_id === hotel.id
                            }
                            onClick={() => save("hotel", hotel.id)}
                          >
                            {trip.hotel_id === hotel.id ? "Saved" : "Save stay"}
                            <Check size={15} />
                          </button>
                        </div>
                      </div>
                    )}
                  </article>
                ))}
              </div>
              <p className="catalog-note">
                Fictional properties and ratings. Three-night totals include
                mock taxes. Room photo is illustrative.
              </p>
            </>
          )}
          <section className="budget-strip">
            <div>
              <Wallet size={19} />
              <span>Saved trip total</span>
              <strong>{money(trip.total_cents)}</strong>
            </div>
            <span className={trip.remaining_cents < 0 ? "over-budget" : ""}>
              {money(Math.abs(trip.remaining_cents))}{" "}
              {trip.remaining_cents < 0 ? "over budget" : "remaining"}{" "}
              <small>of {money(trip.budget_cents)}</small>
            </span>
          </section>
          {trip.warnings.map((warning) => (
            <div className="trip-warning" key={warning}>
              <Clock3 size={17} />
              <span>{warning}</span>
            </div>
          ))}
          <footer className="footer">
            <span>OneAgent Travel · A working prototype</span>
            <span>Demo data. Saved selections are not bookings.</span>
          </footer>
        </main>
        <aside
          className={`agent-panel ${mobileChat ? "mobile-open" : ""}`}
          aria-label="OneAgent conversation"
        >
          <div className="agent-header">
            <div className="agent-avatar">
              <Orbit size={25} />
            </div>
            <div>
              <strong>OneAgent</strong>
              <span>Your personal travel companion</span>
            </div>
            <button
              className="close-chat icon-button"
              aria-label="Close chat"
              onClick={() => setMobileChat(false)}
            >
              <X size={21} />
            </button>
          </div>
          <div className="agent-context">
            <span className="context-dot" />
            <span>
              With you in <strong>{titles[app]}</strong>
            </span>
          </div>
          {current && (
            <div className="viewing">
              <small>LOOKING AT</small>
              <span>
                {app === "flights" ? <Plane size={15} /> : <Hotel size={15} />}{" "}
                {current.name}
              </span>
            </div>
          )}
          <div
            className="chat-log"
            role="log"
            aria-label="Conversation messages"
          >
            <div className="agent-welcome">
              <span className="mini-agent">
                <Orbit size={18} />
              </span>
              <p>
                {app === "home"
                  ? "A good trip starts with what matters to you. Set your budget and preferences, then explore flights and stays. I’ll be with you in each app."
                  : `Same agent, new place. I remember our conversation. ${current ? "Ask me about this option or how it compares." : `Select a ${app === "flights" ? "flight" : "hotel"} and ask me anything about it.`}`}
              </p>
            </div>
            {transcript.messages.map((message) => {
              const output = transcript.outputs.find(
                (o) => o.in_reply_to === message.message.id,
              );
              return (
                <React.Fragment key={message.event_id}>
                  <div className="user-message">
                    {message.context.selected_object && (
                      <small>{message.context.selected_object.name}</small>
                    )}
                    <p>{message.message.text}</p>
                  </div>
                  {output && (
                    <div className="agent-message">
                      <span className="mini-agent">
                        <Orbit size={18} />
                      </span>
                      <div>
                        <p>{output.text}</p>
                        {output.proposal && (
                          <button
                            className="proposal"
                            disabled={actionPending}
                            onClick={() => confirmProposal(output.proposal!)}
                          >
                            <Check size={16} />{" "}
                            {output.proposal.name === "trip.update_brief"
                              ? "Confirm trip brief update"
                              : `Confirm ${output.proposal.name.endsWith("flight") ? "flight" : "hotel"} selection`}
                          </button>
                        )}
                        {Object.keys(output.shared_context).length > 0 && (
                          <span className="shared-label">
                            <ShieldCheck size={13} /> Authorized preferences
                            shared
                          </span>
                        )}
                      </div>
                    </div>
                  )}
                </React.Fragment>
              );
            })}
            {(pending || sending) && !transcript.error && (
              <div className="thinking">
                <Orbit size={17} className="spin" /> Thinking with your trip in
                mind…
              </div>
            )}
            {transcript.error && (
              <div className="chat-error">
                <p>{transcript.error}</p>
                <button
                  onClick={() =>
                    api("retry", {})
                      .then(() =>
                        setTranscript((t) => ({
                          ...t,
                          error: null,
                          running: true,
                        })),
                      )
                      .catch((e) => setError(e.message))
                  }
                >
                  <RotateCcw size={14} /> Retry reply
                </button>
              </div>
            )}
            <div ref={logEnd} />
          </div>
          <div className="chat-bottom">
            {transcript.messages.length === 0 && (
              <div className="suggestions">
                {prompts.map((prompt) => (
                  <button
                    key={prompt}
                    onClick={() => send(prompt)}
                    disabled={sending || (app !== "home" && !current)}
                  >
                    {prompt}
                    <ArrowUp size={14} />
                  </button>
                ))}
              </div>
            )}
            <form
              className="composer"
              onSubmit={(e) => {
                e.preventDefault();
                send();
              }}
            >
              <textarea
                aria-label="Message OneAgent"
                placeholder={
                  current ? "Ask about this option…" : "Ask your agent…"
                }
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                rows={2}
                maxLength={16000}
                onKeyDown={(e) => {
                  if (
                    e.key === "Enter" &&
                    !e.shiftKey &&
                    !e.nativeEvent.isComposing
                  ) {
                    e.preventDefault();
                    send();
                  }
                }}
              />
              <div className="composer-bottom">
                <span>
                  <Sparkles size={13} /> Context comes with you
                </span>
                <button
                  type="submit"
                  aria-label="Send message"
                  disabled={sending || !draft.trim()}
                >
                  <ArrowUp size={18} />
                </button>
              </div>
            </form>
            {app !== "home" && (
              <label className="share-toggle">
                <input
                  type="checkbox"
                  checked={sharing}
                  onChange={(e) => setSharing(e.target.checked)}
                />{" "}
                Share budget & preferences with this app
              </label>
            )}
            <div className="agent-footnote">
              <ShieldCheck size={12} /> Your conversation stays with your agent
            </div>
            {boot.mode !== "live" && (
              <div className="fixture-banner">
                Test fixture mode · Responses are not live
              </div>
            )}
          </div>
        </aside>
      </div>
      <button
        className="mobile-chat-toggle"
        onClick={() => setMobileChat(true)}
      >
        <Orbit size={20} /> Ask OneAgent
        {pending && <span className="pending-dot" />}
      </button>
      {toast && (
        <div role="status" className="toast">
          <Check size={18} />
          {toast}
        </div>
      )}
      {error && (
        <div role="alert" className="error-toast">
          <span>{error}</span>
          <button aria-label="Dismiss error" onClick={() => setError("")}>
            <X size={18} />
          </button>
        </div>
      )}
    </div>
  );
}

createRoot(document.getElementById("root")!).render(<App />);
