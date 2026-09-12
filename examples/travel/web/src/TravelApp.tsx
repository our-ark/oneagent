import React, { useEffect, useRef, useState } from "react";
import {
  ArrowRight,
  Check,
  ChevronRight,
  Clock3,
  Compass,
  Hotel,
  MapPin,
  MessageCircle,
  Orbit,
  Plane,
  Star,
  X,
} from "lucide-react";
import "./style.css";
import "./site-themes.css";
import {
  CompanionPanel,
  type Conversation as Transcript,
} from "./CompanionPanel";

type AppId = "home" | "flights" | "hotels" | "activities";
export type SiteId = "flights" | "hotels" | "activities";
type Activity = {
  id: string;
  name: string;
  neighborhood: string;
  category: string;
  price_cents: number;
  starts_at: string;
  duration_minutes: number;
  pace: string;
  description: string;
  tag: string;
};
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
  image_alt: string;
};
type Bootstrap = {
  csrf: string;
  catalog: { flights?: Flight[]; hotels?: Stay[]; activities?: Activity[] };
  app_id: SiteId;
  linked: boolean;
  session_id: string;
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
  activities: "Daylight",
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
export function TravelApp({ site }: { site: SiteId }) {
  const [boot, setBoot] = useState<Bootstrap | null>(null);
  const app: AppId = site;
  const appRef = useRef(app);
  const [selected, setSelected] = useState<Record<AppId, string | null>>({
    home: null,
    flights: null,
    hotels: null,
    activities: null,
  });
  const [transcript, setTranscript] = useState<Transcript>(emptyTranscript);
  const [error, setError] = useState("");
  const [connectionError, setConnectionError] = useState("");
  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);
  const [mobileChat, setMobileChat] = useState(false);
  const [sort, setSort] = useState("recommended");
  const [quietOnly, setQuietOnly] = useState(false);

  useEffect(() => {
    const token = new URLSearchParams(location.hash.slice(1)).get("connect");
    if (token) history.replaceState({}, "", location.pathname);
    async function connect() {
      let data = await api<Bootstrap>("session");
      csrfToken = data.csrf;
      if (token) {
        await api("connect", { token });
        data = await api<Bootstrap>("session");
        csrfToken = data.csrf;
      }
      if (data.app_id !== site)
        throw new Error("Open this website using its own Telegram link.");
      setBoot(data);
    }
    connect().catch((e) => setError(e.message));
  }, [site]);
  async function ensureSession(_target: AppId): Promise<string> {
    if (!boot) throw new Error("The agent is still connecting.");
    return boot.session_id;
  }

  useEffect(() => {
    if (!boot) return;
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout>;
    async function refresh() {
      try {
        const messages = await api<Transcript>("conversation");
        if (!cancelled) {
          setTranscript(messages);
          setConnectionError("");
        }
      } catch (e) {
        if (!cancelled) setConnectionError((e as Error).message);
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

  async function navigate(target: AppId) {
    if (target === "home" || target === app) return;
    try {
      const links = await api<Record<string, string>>("links", {});
      location.assign(links[target]);
    } catch (e) {
      setError((e as Error).message);
    }
  }
  const current =
    app === "flights"
      ? boot?.catalog.flights?.find((f) => f.id === selected.flights)
      : app === "hotels"
        ? boot?.catalog.hotels?.find((h) => h.id === selected.hotels)
        : boot?.catalog.activities?.find((a) => a.id === selected.activities);
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
        share: [],
      });
      if (appRef.current === target)
        setTranscript((previous) => ({
          ...previous,
          running: true,
          messages: [
            ...previous.messages,
            {
              event_id: messageId,
              source_app: target,
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
  if (!boot)
    return (
      <main className="loading">
        <Orbit size={38} />
        <h1>Opening {titles[app]}</h1>
        <p>{error || "Connecting your personal agent…"}</p>
        {error && <button onClick={() => location.reload()}>Try again</button>}
      </main>
    );
  const pending = transcript.messages.some(
    (message) =>
      !transcript.outputs.some(
        (output) =>
          output.in_reply_to === message.message.id &&
          output.source_app === message.source_app,
      ),
  );
  const prompts =
    app === "flights"
      ? [
          "Would this flight work for my trip?",
          "How does this compare with the previous flight?",
        ]
      : app === "hotels"
        ? [
            "Does this work with the flight we discussed?",
            "Is this better than the previous hotel?",
          ]
        : [
            "Would this activity fit our trip?",
            "Does this leave enough time after my flight?",
          ];
  const flights = [...(boot.catalog.flights || [])].sort((a, b) =>
    sort === "price"
      ? a.price_cents - b.price_cents
      : sort === "arrival"
        ? a.arrival_at.localeCompare(b.arrival_at)
        : 0,
  );
  const hotels = [...(boot.catalog.hotels || [])]
    .filter((h) => !quietOnly || h.quiet)
    .sort((a, b) => (sort === "price" ? a.nightly_cents - b.nightly_cents : 0));

  return (
    <div className={`shell theme-${app}`}>
      <header className="topbar site-topbar">
        <a className="wordmark" href="/" aria-label={`${titles[app]} home`}>
          {app === "flights" ? (
            <Plane size={29} />
          ) : app === "hotels" ? (
            <Hotel size={29} />
          ) : (
            <Compass size={29} />
          )}
          {titles[app].toLowerCase()}
          <span className="demo-label">DEMO</span>
        </a>
        <div className="site-edition">
          {site === "flights" ? (
            <>
              <span className="edition-label">FLIGHT SEARCH</span>
              <span>USD · One-way fares</span>
            </>
          ) : site === "hotels" ? (
            <>
              <span className="edition-label">
                A considered collection of stays
              </span>
              <span>Tokyo, Japan</span>
            </>
          ) : (
            <>
              <span className="edition-label">GO SOMEWHERE GOOD.</span>
              <span>TOKYO CITY GUIDE / VOL. 01</span>
            </>
          )}
        </div>
      </header>
      <div className="workspace">
        <main className="main-content">
          {app === "flights" && (
            <>
              <div className="page-heading">
                <span className="eyebrow">YOUR NEXT DEPARTURE</span>
                <h1>Tokyo, here you come.</h1>
                <p>
                  Compare nonstop flights from San Francisco. Pick your way
                  there.
                </p>
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
              <section className="stay-editorial">
                <div className="page-heading">
                  <span className="eyebrow">THE TOKYO COLLECTION</span>
                  <h1>
                    Somewhere
                    <br />
                    <em>to slow down.</em>
                  </h1>
                  <p>
                    Good neighborhoods. Thoughtful spaces.
                    <br />A place that feels a little like you.
                  </p>
                </div>
                <div className="stay-hero-photo">
                  <img
                    src={
                      boot.catalog.hotels?.find(
                        (hotel) => hotel.id === "sora-retreat",
                      )?.image
                    }
                    alt="Soft linen and natural materials in an illustrative bedroom"
                  />
                  <span>FOUR STAYS, EACH WITH ITS OWN STORY</span>
                </div>
              </section>
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
                        <img src={hotel.image} alt={hotel.image_alt} />
                        <span className="neighborhood">
                          <MapPin size={13} />
                          {hotel.neighborhood}
                        </span>
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
                              send(
                                "Does this hotel work with the flight we discussed?",
                              )
                            }
                            disabled={sending}
                          >
                            <MessageCircle size={15} /> Ask agent
                          </button>
                        </div>
                      </div>
                    )}
                  </article>
                ))}
              </div>
              <p className="catalog-note">
                Fictional properties and ratings. Three-night totals include
                mock taxes. Photos are illustrative.
              </p>
            </>
          )}
          {app === "activities" && (
            <>
              <section className="activity-hero">
                <img
                  src="/images/tokyo.jpg"
                  alt="Tokyo skyline with Tokyo Tower"
                />
                <div>
                  <span className="eyebrow light">
                    LESS SCROLLING. MORE STORIES.
                  </span>
                  <h1>
                    OUT THERE.
                    <br />
                    <span>IN TOKYO.</span>
                  </h1>
                  <p>Walk it. Taste it. Ride it. Find your next good day.</p>
                  <span className="activity-issue">NOV 6—9, 2026 ↗</span>
                </div>
              </section>
              <div className="results-heading">
                <strong>
                  <span className="section-number">01—04</span> PICK YOUR KIND
                  OF DAY
                </strong>
                <label>
                  Sort by{" "}
                  <select
                    aria-label="Sort activities"
                    value={sort}
                    onChange={(e) => setSort(e.target.value)}
                  >
                    <option value="recommended">Recommended</option>
                    <option value="price">Lowest price</option>
                  </select>
                </label>
              </div>
              <div className="activity-list">
                {[...(boot.catalog.activities || [])]
                  .sort((a, b) =>
                    sort === "price" ? a.price_cents - b.price_cents : 0,
                  )
                  .map((activity) => (
                    <article
                      className={`activity-card ${selected.activities === activity.id ? "selected" : ""}`}
                      key={activity.id}
                    >
                      <button
                        className="activity-select"
                        onClick={() =>
                          setSelected((p) => ({
                            ...p,
                            activities: activity.id,
                          }))
                        }
                        aria-pressed={selected.activities === activity.id}
                        aria-label={`View ${activity.name}`}
                      >
                        <span className="activity-card-top">
                          <span className="tag">{activity.category}</span>
                          <ArrowRight size={24} />
                        </span>
                        <h2>{activity.name}</h2>
                        <p>
                          <MapPin size={15} /> {activity.neighborhood} ·{" "}
                          {activity.pace}
                        </p>
                        <div className="activity-facts">
                          <span>
                            <Clock3 size={15} /> Nov{" "}
                            {Number(activity.starts_at.slice(8, 10))} ·{" "}
                            {localTime(activity.starts_at)} ·{" "}
                            {activity.duration_minutes} min
                          </span>
                          <strong>{money(activity.price_cents)}</strong>
                        </div>
                      </button>
                      {selected.activities === activity.id && (
                        <div className="selection-detail">
                          <p>{activity.description}</p>
                          <div>
                            <button
                              className="secondary"
                              disabled={sending}
                              onClick={() =>
                                send("Would this activity fit our trip?")
                              }
                            >
                              <MessageCircle size={16} /> Ask OneAgent
                            </button>
                          </div>
                        </div>
                      )}
                    </article>
                  ))}
              </div>
              <p className="catalog-note">
                Fictional activities. Prices include mock taxes. Times are local
                to Tokyo.
              </p>
            </>
          )}
          <footer className="footer">
            <span>{titles[app]} · Tokyo demo</span>
            <span>Fictional options for this demo.</span>
          </footer>
        </main>
        <CompanionPanel
          appName={titles[app]}
          sources={{ ...titles, telegram: "Telegram" }}
          linked={boot.linked}
          selected={current}
          conversation={transcript}
          pending={pending}
          sending={sending}
          draft={draft}
          onDraft={setDraft}
          onSend={send}
          onRetry={() =>
            api("retry", {})
              .then(() =>
                setTranscript((t) => ({ ...t, error: null, running: true })),
              )
              .catch((e) => setError(e.message))
          }
          suggestions={prompts}
          mobileOpen={mobileChat}
          onMobileOpen={setMobileChat}
          testMode={boot.mode !== "live"}
        >
          <div
            className="companion-sites"
            aria-label="Continue on another website"
          >
            {(["flights", "hotels", "activities"] as SiteId[])
              .filter((target) => target !== site)
              .map((target) => (
                <button key={target} onClick={() => navigate(target)}>
                  Open {titles[target]} <ArrowRight size={13} />
                </button>
              ))}
          </div>
        </CompanionPanel>
      </div>
      {(error || connectionError) && (
        <div role="alert" className="error-toast">
          <span>{error || connectionError}</span>
          <button
            aria-label="Dismiss error"
            onClick={() => {
              setError("");
              setConnectionError("");
            }}
          >
            <X size={18} />
          </button>
        </div>
      )}
    </div>
  );
}
