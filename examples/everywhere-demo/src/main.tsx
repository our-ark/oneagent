import React, { useState, useEffect, useRef, useMemo } from "react";
import { createRoot } from "react-dom/client";
import { CopilotKit, useAgent, useCopilotKit } from "@copilotkit/react-core/v2";
import { HttpAgent } from "@ag-ui/client";
import {
  ArrowUp,
  ArrowUpRight,
  ArrowRight,
  ArrowLeft,
  Check,
  ChevronDown,
  ChevronRight,
  CircleCheck,
  Copy,
  Download,
  ExternalLink,
  Globe,
  Heart,
  Link2,
  LockKeyhole,
  Menu,
  MessageCircle,
  Monitor,
  MoreHorizontal,
  Plus,
  Radio,
  RotateCcw,
  Send,
  ShieldCheck,
  ShoppingBag,
  Smartphone,
  Sparkles,
  Unplug,
  X,
  Zap,
  Activity,
  Wallet,
  Footprints,
  Layers,
  Wifi,
  Battery,
  Signal,
} from "lucide-react";
import QRCode from "qrcode";
import { api, uuid, names } from "./api";
import type { Surface, Snapshot, Product, Message, Quote } from "./types";
import "./styles.css";

const surfaces: Surface[] = ["phone", "dayform", "stride", "desktop"];
const icons = {
  phone: Smartphone,
  dayform: Globe,
  stride: Globe,
  desktop: Monitor,
};
const money = (n: number) => `$${n.toFixed(2)}`;
function Mark({ small = false }: { small?: boolean }) {
  return (
    <span className={`agent-mark ${small ? "small" : ""}`}>
      <span>b</span>
      <i />
    </span>
  );
}
function Brand() {
  return (
    <div className="brand">
      <img src="/icon.svg" alt="" />
      <span>
        oneagent<span className="brand-dot">.</span>
      </span>
    </div>
  );
}

function App() {
  const route = location.pathname.split("/")[1];
  const standalone = surfaces.includes(route as Surface);
  const [surface, setSurface] = useState<Surface>(
    standalone ? (route as Surface) : "dayform",
  );
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [connection, setConnection] = useState(false);
  const [error, setError] = useState("");
  const [modal, setModal] = useState<
    "pair" | "connections" | "memory" | "events" | "guide" | null
  >(null);
  const [toast, setToast] = useState("");
  const [size, setSize] = useState(9);
  const [contextRevision, setContextRevision] = useState(1);
  const [tour, setTour] = useState(false);
  const [step, setStep] = useState(0);
  const sourceSession = useRef(uuid());
  const flash = (message: string) => {
    setToast(message);
    window.setTimeout(() => setToast(""), 3500);
  };
  const init = async (fresh = false) => {
    try {
      const shared = new URLSearchParams(location.hash.slice(1)).get("session");
      const saved = fresh
        ? null
        : shared || localStorage.getItem("oneagent-session");
      let s: Snapshot;
      if (saved) {
        try {
          s = await api<Snapshot>(`/api/sessions/${encodeURIComponent(saved)}`);
        } catch (e) {
          if (shared) throw e;
          s = await api<Snapshot>("/api/sessions", { method: "POST" });
        }
      } else s = await api<Snapshot>("/api/sessions", { method: "POST" });
      localStorage.setItem("oneagent-session", s.id);
      history.replaceState(null, "", `${location.pathname}#session=${s.id}`);
      setSnapshot(s);
      setSize(s.preferences.size);
      setError("");
    } catch (e) {
      setError((e as Error).message);
    }
  };
  useEffect(() => {
    void init();
  }, []);
  useEffect(() => {
    if (!snapshot?.id) return;
    const events = new EventSource(`/api/sessions/${snapshot.id}/events`);
    events.onopen = () => setConnection(true);
    events.onmessage = (e) => {
      setSnapshot(JSON.parse(e.data));
      setConnection(true);
    };
    events.onerror = () => setConnection(false);
    return () => events.close();
  }, [snapshot?.id]);
  const changeSurface = (next: Surface) => {
    setSurface(next);
    setContextRevision((r) => r + 1);
    if (standalone)
      history.replaceState(null, "", `/${next}#session=${snapshot?.id}`);
  };
  const product = snapshot?.products.find((p) => p.app === surface);
  const agent = useMemo(
    () => new HttpAgent({ url: "/api/agent", agentId: "bob" }),
    [snapshot?.id, surface],
  );
  if (!snapshot)
    return (
      <div className="loading">
        <Brand />
        <p>{error || "Getting Bob ready…"}</p>
        {error && <button onClick={() => void init()}>Try again</button>}
      </div>
    );
  const visit = (p: Product) => changeSurface(p.app);
  const newDemo = () => {
    void init(true);
    setStep(0);
    setTour(false);
    changeSurface("phone");
    setModal(null);
  };

  return (
    <CopilotKit
      agents__unsafe_dev_only={{ bob: agent }}
      showDevConsole={false}
      enableInspector={false}
    >
      <div className={`app ${standalone ? "standalone" : ""}`}>
        {!standalone && (
          <>
            <header className="topbar">
              <Brand />
              <div className="topnav">
                <span className="nav-active">The experience</span>
                <button onClick={() => setModal("guide")}>
                  How it works <ArrowUpRight size={13} />
                </button>
              </div>
              <div className="top-right">
                <span className={`sync-pill ${connection ? "" : "offline"}`}>
                  <i />
                  {connection ? "Session connected" : "Reconnecting…"}
                </span>
                <button
                  className="icon-button"
                  aria-label="Open connections"
                  onClick={() => setModal("connections")}
                >
                  <Menu size={19} />
                </button>
              </div>
            </header>
            <section className="intro">
              <div>
                <div className="eyebrow">
                  <span /> ONE AGENT. EVERYWHERE.
                </div>
                <h1>
                  Different apps.
                  <br />
                  <span>The same Bob.</span>
                </h1>
                <p>
                  Your context comes with you. Your conversation keeps going.
                  <br className="desktop-break" /> Meet the personal agent
                  that’s always on your side.
                </p>
              </div>
              <div className="intro-aside">
                <div className="avatar-stack">
                  <div>
                    <Smartphone size={20} />
                  </div>
                  <div>
                    <Globe size={20} />
                  </div>
                  <div>
                    <Monitor size={20} />
                  </div>
                  <Mark />
                </div>
                <p>
                  One relationship.
                  <br />
                  <strong>Every place you work and live.</strong>
                </p>
                <button
                  className="text-button"
                  onClick={() => {
                    setTour(true);
                    setStep(0);
                    changeSurface("phone");
                  }}
                >
                  Try the 2-minute story <ArrowRight size={15} />
                </button>
              </div>
            </section>
            <div className="workspace-toolbar">
              <div className="surface-tabs">
                {surfaces.map((s) => {
                  const Icon = icons[s];
                  return (
                    <button
                      key={s}
                      onClick={() => changeSurface(s)}
                      className={surface === s ? "active" : ""}
                    >
                      <Icon size={15} />
                      <span>
                        {s === "phone"
                          ? "Phone"
                          : s === "dayform"
                            ? "DAYFORM"
                            : s === "stride"
                              ? "STRIDE"
                              : "Desktop"}
                      </span>
                      {s === "dayform" || s === "stride" ? (
                        <span
                          className={`tiny-dot ${snapshot.grants[s].connected ? "" : "muted"}`}
                        />
                      ) : null}
                    </button>
                  );
                })}
              </div>
              <button className="pair-button" onClick={() => setModal("pair")}>
                <Smartphone size={15} />
                <span>Try on your device</span>
                <ArrowUpRight size={14} />
              </button>
            </div>
            {tour && (
              <div className="tour-bar">
                <span className="step-number">0{step + 1}</span>
                <div>
                  <strong>
                    {
                      [
                        "Start with what matters to you",
                        "Open DAYFORM. Bob comes with you.",
                        "A different store. The same conversation.",
                        "Your decision, your approval.",
                        "Your receipt follows you home.",
                      ][step]
                    }
                  </strong>
                  <span>
                    {
                      [
                        "Send the suggested brief on the phone.",
                        "Ask “Will these be comfortable on my walk to work?”",
                        "Ask “How does this compare with the first pair?”",
                        "Ask Bob to order Day One, then review and approve.",
                        "Open the phone or desktop to see the same receipt.",
                      ][step]
                    }
                  </span>
                </div>
                <button
                  onClick={() => {
                    if (step === 4) {
                      setTour(false);
                      return;
                    }
                    setStep(step + 1);
                    changeSurface(
                      (["dayform", "stride", "dayform", "phone"] as Surface[])[
                        step
                      ],
                    );
                  }}
                >
                  {step === 4 ? "Finish story" : "Next step"}
                  <ArrowRight size={14} />
                </button>
                <button
                  className="icon-button"
                  onClick={() => setTour(false)}
                  aria-label="Close guided story"
                >
                  <X size={15} />
                </button>
              </div>
            )}
          </>
        )}

        <div className="experience-layout">
          <main className={`surface-frame ${surface}`}>
            {standalone && (
              <div className="standalone-switch">
                <Brand />
                <button
                  onClick={() => setModal("pair")}
                  aria-label="Connect a device"
                >
                  <Link2 size={17} />
                </button>
                <select
                  aria-label="Switch application"
                  value={surface}
                  onChange={(e) => changeSurface(e.target.value as Surface)}
                >
                  {surfaces.map((s) => (
                    <option key={s} value={s}>
                      {names[s]}
                    </option>
                  ))}
                </select>
                <button
                  onClick={() => setModal("connections")}
                  aria-label="Connections"
                >
                  <ShieldCheck size={18} />
                </button>
              </div>
            )}
            {(surface === "dayform" || surface === "stride") && product ? (
              <>
                {!standalone && (
                  <div className="browser-chrome">
                    <div className="traffic-lights">
                      <i />
                      <i />
                      <i />
                    </div>
                    <div className="address-bar">
                      <LockKeyhole size={10} />
                      {surface}.example / products / {product.id}
                    </div>
                    <button
                      className="icon-button"
                      title="Open this store in another window"
                      onClick={() =>
                        window.open(
                          `/${surface}#session=${snapshot.id}`,
                          "_blank",
                          "noopener",
                        )
                      }
                    >
                      <ExternalLink size={12} />
                    </button>
                  </div>
                )}
                <div className="store-and-chat">
                  <Storefront
                    key={product.app}
                    product={product}
                    snapshot={snapshot}
                    size={size}
                    setSize={(s) => {
                      setSize(s);
                      setContextRevision((r) => r + 1);
                    }}
                    flash={flash}
                  />
                  <Chat
                    key={`${snapshot.id}-${surface}`}
                    snapshot={snapshot}
                    surface={surface}
                    sourceSession={sourceSession.current}
                    product={product}
                    size={size}
                    contextRevision={contextRevision}
                    onVisit={visit}
                    onConnections={() => setModal("connections")}
                  />
                </div>
              </>
            ) : surface === "phone" ? (
              <div className="phone-stage">
                <div className="phone-story">
                  <div className="eyebrow">YOUR PERSONAL COMPANION</div>
                  <h2>
                    A small request.
                    <br />
                    <span>Before a busy day.</span>
                  </h2>
                  <p>
                    Tell Bob what you need.
                    <br />
                    Then pick up anywhere.
                  </p>
                  <div className="phone-story-note">
                    <Link2 size={17} />
                    <span>
                      This phone shares a real session with
                      <br />
                      both stores and your desktop.
                    </span>
                  </div>
                  <button
                    className="outline-button"
                    onClick={() => setModal("pair")}
                  >
                    Open on my phone <ArrowUpRight size={14} />
                  </button>
                </div>
                <div className="phone-device">
                  <div className="phone-status">
                    <strong>9:41</strong>
                    <span className="dynamic-island" />
                    <div>
                      <Signal size={13} />
                      <Wifi size={13} />
                      <Battery size={16} />
                    </div>
                  </div>
                  <Chat
                    key={`${snapshot.id}-${surface}`}
                    snapshot={snapshot}
                    surface={surface}
                    sourceSession={sourceSession.current}
                    size={size}
                    contextRevision={contextRevision}
                    onVisit={visit}
                    onConnections={() => setModal("connections")}
                  />
                  <div className="home-indicator" />
                </div>
              </div>
            ) : (
              <div className="desktop-shell">
                <div className="desktop-titlebar">
                  <div className="traffic-lights">
                    <i />
                    <i />
                    <i />
                  </div>
                  <span>Bob — Personal workspace</span>
                  <span>⌘ K</span>
                </div>
                <div className="desktop-content">
                  <aside className="desktop-sidebar">
                    <Mark />
                    <h3>Your space.</h3>
                    <p>Everything, together.</p>
                    <div className="desktop-nav">
                      <span>
                        <MessageCircle size={15} />
                        Conversation
                      </span>
                      <button onClick={() => setModal("memory")}>
                        <Layers size={15} />
                        Personal memory
                      </button>
                      <button onClick={() => setModal("connections")}>
                        <Link2 size={15} />
                        Connections
                      </button>
                    </div>
                    <div className="desktop-receipt">
                      <ShoppingBag size={19} />
                      <strong>
                        {snapshot.orders.length
                          ? "Your order is ready"
                          : "A task in motion"}
                      </strong>
                      <p>
                        {snapshot.orders.length
                          ? `${snapshot.orders.at(-1)?.product.name} · ${money(snapshot.orders.at(-1)!.total)}`
                          : "Start on your phone. Continue here."}
                      </p>
                    </div>
                  </aside>
                  <Chat
                    key={`${snapshot.id}-${surface}`}
                    snapshot={snapshot}
                    surface={surface}
                    sourceSession={sourceSession.current}
                    size={size}
                    contextRevision={contextRevision}
                    onVisit={visit}
                    onConnections={() => setModal("connections")}
                  />
                </div>
              </div>
            )}
          </main>

          {!standalone && (
            <aside className="continuity-panel">
              <div className="continuity-heading">
                <span className="eyebrow">THE THREAD THAT CONNECTS</span>
                <Radio size={16} />
              </div>
              <div className="bob-card">
                <Mark />
                <div>
                  <h3>Bob</h3>
                  <span>Your personal agent</span>
                </div>
                <span className="status-tag">With you</span>
              </div>
              <div className="continuity-rail">
                <span className="rail-line" />
                {surfaces.map((s) => {
                  const Icon = icons[s];
                  const active = s === surface;
                  return (
                    <button
                      key={s}
                      className={active ? "here" : ""}
                      onClick={() => changeSurface(s)}
                    >
                      <span className="rail-icon">
                        <Icon size={15} />
                      </span>
                      <span>{names[s]}</span>
                      {active ? (
                        <span className="here-label">You’re here</span>
                      ) : (
                        <Check size={12} />
                      )}
                    </button>
                  );
                })}
              </div>
              <div className="memory-card">
                <div>
                  <span className="eyebrow">BOB REMEMBERS</span>
                  <LockKeyhole size={12} />
                </div>
                <h4>Your workday, your way.</h4>
                <span>
                  <Wallet size={14} />
                  Under ${snapshot.preferences.budget}
                </span>
                <span>
                  <Footprints size={14} />
                  US {snapshot.preferences.size} ·{" "}
                  {snapshot.preferences.priority.includes("Style")
                    ? "Style first"
                    : "Comfort first"}
                </span>
                <span>
                  <Heart size={14} />
                  For the everyday commute
                </span>
                <button onClick={() => setModal("memory")}>
                  Your memory, your control <ArrowUpRight size={12} />
                </button>
              </div>
              <div className="context-card">
                <div className="context-label">
                  <span className="live-dot" /> LIVE APP CONTEXT
                </div>
                <strong>
                  {product
                    ? `${product.name} / ${product.color}`
                    : surface === "phone"
                      ? "Personal conversation"
                      : "Your entire shopping journey"}
                </strong>
                <p>
                  {product
                    ? `${names[product.app]} · US ${size} selected`
                    : `${snapshot.messages.length} messages · ${snapshot.orders.length} orders`}
                </p>
                <div className="context-footer">
                  <ShieldCheck size={13} />
                  {product ? "Shared by this store" : "Owned by you"}
                </div>
              </div>
              <button
                className="event-button"
                onClick={() => setModal("events")}
              >
                <Activity size={14} />
                <span>See the live event trail</span>
                <ChevronRight size={14} />
              </button>
            </aside>
          )}
        </div>

        {!standalone && (
          <>
            <div className="under-workspace">
              <span>
                <span className="live-dot" />
                {snapshot.mode === "live" ? "Live model" : "Interactive demo"}
                <span className="divider-dot">·</span>Fictional stores.
                Simulated orders.
              </span>
              <button onClick={newDemo}>
                <RotateCcw size={12} />
                New session
              </button>
            </div>
            <section className="principles">
              <div>
                <span className="principle-icon">
                  <MessageCircle size={20} />
                </span>
                <div>
                  <h3>One continuing conversation</h3>
                  <p>No reintroductions. No starting over.</p>
                </div>
              </div>
              <div>
                <span className="principle-icon">
                  <Layers size={20} />
                </span>
                <div>
                  <h3>Context, right where you are</h3>
                  <p>Each app brings what only it knows.</p>
                </div>
              </div>
              <div>
                <span className="principle-icon">
                  <ShieldCheck size={20} />
                </span>
                <div>
                  <h3>Always on your terms</h3>
                  <p>You choose what’s shared and approved.</p>
                </div>
              </div>
            </section>
            <footer>
              <span>
                Inspired by <em>One Agent, Anywhere</em> & the Bob concept film.
              </span>
              <span>
                Built with{" "}
                <a
                  href="https://docs.copilotkit.ai/"
                  target="_blank"
                  rel="noreferrer"
                >
                  CopilotKit
                </a>
                <span className="divider-dot">/</span>AG-UI
              </span>
            </footer>
          </>
        )}
        {toast && (
          <div className="toast" role="status">
            <CircleCheck size={16} />
            {toast}
          </div>
        )}
        {modal && (
          <Modal
            title={
              {
                pair: "Your agent. On your device.",
                connections: "You control the connections.",
                memory: "Your memory belongs to you.",
                events: "A real conversation, under the hood.",
                guide: "Follow Bob across your day.",
              }[modal]
            }
            onClose={() => setModal(null)}
          >
            {modal === "pair" && <Pairing id={snapshot.id} flash={flash} />}
            {modal === "connections" && (
              <Connections snapshot={snapshot} flash={flash} />
            )}
            {modal === "memory" && (
              <>
                <p className="modal-lead">
                  Bob carries this shopping brief between apps. Stores receive
                  only the context you authorize and the replies you ask for in
                  their interface.
                </p>
                <div className="memory-details">
                  <div>
                    <span>Budget</span>
                    <strong>${snapshot.preferences.budget}</strong>
                  </div>
                  <div>
                    <span>Size</span>
                    <strong>US {snapshot.preferences.size}</strong>
                  </div>
                  <div>
                    <span>Priority</span>
                    <strong>{snapshot.preferences.priority}</strong>
                  </div>
                  <div>
                    <span>Saved candidates</span>
                    <strong>
                      {snapshot.candidates.length
                        ? snapshot.products
                            .filter((p) => snapshot.candidates.includes(p.id))
                            .map((p) => p.name)
                            .join(", ")
                        : "No shortlist yet"}
                    </strong>
                  </div>
                </div>
                <p className="small-note">
                  Change your brief by telling Bob “Set my budget to $150” or
                  “My size is US 10.”
                </p>
                <a
                  className="primary-button download-link"
                  href={`/api/sessions/${snapshot.id}/export`}
                  download
                >
                  <Download size={16} />
                  Export my conversation & memory
                </a>
                <button className="outline-button full" onClick={newDemo}>
                  <Plus size={15} />
                  Start a separate session
                </button>
              </>
            )}
            {modal === "events" && (
              <>
                <p className="modal-lead">
                  Actual server events for this session. Message context stays
                  attached to its source, even when you switch apps.
                </p>
                <div className="event-list">
                  {snapshot.events.length ? (
                    snapshot.events.map((e) => (
                      <div key={e.id}>
                        <div>
                          <span className="event-type">{e.type}</span>
                          <time>{new Date(e.at).toLocaleTimeString()}</time>
                        </div>
                        <strong>{e.description}</strong>
                        <span>{e.source}</span>
                        <details>
                          <summary>Event details</summary>
                          <pre>{JSON.stringify(e.details, null, 2)}</pre>
                        </details>
                      </div>
                    ))
                  ) : (
                    <p>Send Bob a message to see the first events.</p>
                  )}
                </div>
              </>
            )}
            {modal === "guide" && (
              <>
                <p className="modal-lead">
                  A working version of the film’s story. Every surface reads
                  from the same durable personal session.
                </p>
                <ol className="guide-list">
                  <li>
                    <strong>Brief Bob on your phone.</strong>
                    <span>
                      Find comfortable work sneakers under $120, US 9.
                    </span>
                  </li>
                  <li>
                    <strong>Browse DAYFORM.</strong>
                    <span>
                      Ask if Day One will be comfortable for your commute.
                    </span>
                  </li>
                  <li>
                    <strong>Compare in STRIDE.</strong>
                    <span>
                      Ask “How does this compare with the first pair?”
                    </span>
                  </li>
                  <li>
                    <strong>Approve a precise checkout.</strong>
                    <span>
                      Return to DAYFORM, ask to order, and review the total.
                    </span>
                  </li>
                  <li>
                    <strong>Pick up anywhere.</strong>
                    <span>The phone and desktop receive the same receipt.</span>
                  </li>
                </ol>
                <div className="technical-note">
                  <strong>What’s live?</strong>
                  <p>
                    CopilotKit / AG-UI message transport, server persistence,
                    cross-device event streaming, store APIs, permissions, and
                    checkout validation.{" "}
                    {snapshot.mode === "demo"
                      ? "Bob uses a deterministic shopping workflow; an optional Claude model can generate conversational replies."
                      : "Claude generates conversational replies."}{" "}
                    Messaging is our companion UI, not a connected Telegram
                    account. This is a single-server demo of the paper’s
                    collaboration semantics.
                  </p>
                </div>
                <button
                  className="primary-button full"
                  onClick={() => {
                    setModal(null);
                    setTour(true);
                    setStep(0);
                    changeSurface("phone");
                  }}
                >
                  Start the story
                  <ArrowRight size={15} />
                </button>
              </>
            )}
          </Modal>
        )}
      </div>
    </CopilotKit>
  );
}

function Storefront({
  product: p,
  snapshot,
  size,
  setSize,
  flash,
}: {
  product: Product;
  snapshot: Snapshot;
  size: number;
  setSize: (s: number) => void;
  flash: (s: string) => void;
}) {
  const favoriteKey = `oneagent-favorite-${snapshot.id}-${p.id}`;
  const [saved, setSaved] = useState(
    () => localStorage.getItem(favoriteKey) === "true",
  );
  const [details, setDetails] = useState(false);
  const [bag, setBag] = useState(false);
  const [sharedCatalog, setSharedCatalog] = useState<{
    products: Product[];
    authorizedContext: { budget?: number };
  } | null>(null);
  const grant = snapshot.grants[p.app];
  useEffect(() => {
    if (grant.connected)
      void api<{ products: Product[]; authorizedContext: { budget?: number } }>(
        `/api/sessions/${snapshot.id}/catalog/${p.app}`,
      )
        .then(setSharedCatalog)
        .catch(() => setSharedCatalog(null));
    else setSharedCatalog(null);
  }, [grant.connected, grant.shareBudget, snapshot.preferences.budget, p.app]);
  return (
    <section className={`storefront ${p.app}`}>
      <nav className="store-nav">
        <span className="store-logo">
          {p.app === "dayform" ? "DAYFORM" : "STRIDE / STUDIO"}
        </span>
        <button className="store-edit" onClick={() => setDetails(!details)}>
          {p.app === "dayform" ? "The everyday edit" : "The collection"}
        </button>
        <button aria-label="View store bag" onClick={() => setBag(!bag)}>
          <ShoppingBag size={16} />
          <span>
            {snapshot.orders
              .filter((o) => o.product.app === p.app)
              .length.toString()
              .padStart(2, "0")}
          </span>
        </button>
      </nav>
      {bag && (
        <div className="store-inline-note">
          <strong>Your bag</strong>
          <p>
            {snapshot.orders.some((o) => o.product.app === p.app)
              ? "Your approved order is complete. Find the receipt with Bob."
              : "Your bag is empty. Ask Bob to prepare a checkout for this pair."}
          </p>
        </div>
      )}
      <div className="product-content">
        <div className="collection-label">
          {p.app === "dayform"
            ? "MADE FOR THE EVERYDAY"
            : "ENGINEERED FOR THE CITY"}
        </div>
        <h2>
          {p.app === "dayform" ? (
            <>
              A good day
              <br />
              starts here.
            </>
          ) : (
            <>
              MOVE
              <br />
              <span>DIFFERENT.</span>
            </>
          )}
        </h2>
        <div className="product-photo">
          <img
            src={p.image}
            alt={`${p.name} ${p.color} sneaker, side profile`}
          />
          <button
            className={`favorite ${saved ? "saved" : ""}`}
            aria-label={saved ? "Remove from favorites" : "Save to favorites"}
            onClick={() => {
              setSaved(!saved);
              localStorage.setItem(favoriteKey, String(!saved));
              flash(
                saved
                  ? "Removed from store favorites"
                  : "Saved to this store’s favorites",
              );
            }}
          >
            <Heart size={18} fill={saved ? "currentColor" : "none"} />
          </button>
          <span className="photo-caption">
            {p.app === "dayform"
              ? "LESS EFFORT. MORE EVERYDAY."
              : "FORM MEETS FORWARD."}
          </span>
        </div>
        <div className="product-meta">
          <div>
            <h3>
              {p.name}
              <span> / {p.color}</span>
            </h3>
            <p>
              {p.app === "dayform"
                ? "Your new everyday essential."
                : "A sharper silhouette. A new perspective."}
            </p>
          </div>
          <span className="product-price">${p.price}</span>
        </div>
        <div className="color-row">
          <span className="color-swatch" /> {p.color}
          <span className="fit-label">
            {p.app === "dayform"
              ? "Comfort, considered."
              : "Precision, in every step."}
          </span>
        </div>
        <div className="size-label">
          <span>
            SELECT SIZE <span>US</span>
          </span>
          <button onClick={() => setDetails(!details)}>
            Size & fit <ArrowUpRight size={11} />
          </button>
        </div>
        <div className="size-options">
          {p.sizes.map((s) => (
            <button
              key={s}
              aria-label={`Select US ${s}`}
              aria-pressed={s === size}
              className={s === size ? "selected" : ""}
              onClick={() => setSize(s)}
            >
              {s}
            </button>
          ))}
        </div>
        <div className="shipping-line">
          <Check size={14} />
          Free shipping <span>·</span> Arrives {p.arrival}
          <span className="in-stock">In stock</span>
        </div>
        {grant.shareBudget && sharedCatalog && (
          <div className="budget-disclosure">
            <ShieldCheck size={12} />
            {sharedCatalog.products.length
              ? `Store filter: under $${sharedCatalog.authorizedContext.budget}`
              : `Store filter: this pair exceeds your $${sharedCatalog.authorizedContext.budget} budget`}
          </div>
        )}
        <button className="details-toggle" onClick={() => setDetails(!details)}>
          Thoughtfully made. Every detail.
          <ChevronDown size={14} />
        </button>
        {details && (
          <div className="product-details">
            <p>{p.description}</p>
            <p>
              {p.fit}. {p.cushioning}. 30-day demo returns. Prices exclude 10%
              demo tax.
            </p>
          </div>
        )}
      </div>
    </section>
  );
}

function Chat({
  snapshot: s,
  surface,
  sourceSession,
  product,
  size,
  contextRevision,
  onVisit,
  onConnections,
}: {
  snapshot: Snapshot;
  surface: Surface;
  sourceSession: string;
  product?: Product;
  size: number;
  contextRevision: number;
  onVisit: (p: Product) => void;
  onConnections: () => void;
}) {
  const { agent } = useAgent({ agentId: "bob" });
  const { copilotkit } = useCopilotKit();
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [pending, setPending] = useState<Message | null>(null);
  const bottom = useRef<HTMLDivElement>(null);
  const isStore = surface === "dayform" || surface === "stride";
  const connected = !isStore || s.grants[surface].connected;
  const messages = s.messages.filter((m) => !isStore || m.source === surface);
  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [s.messages.length, busy]);
  const send = async (text: string) => {
    if (!text.trim() || busy || !connected) return;
    setInput("");
    setBusy(true);
    setError("");
    const id = uuid();
    const message = { id, role: "user" as const, content: text.trim() };
    setPending({ ...message, source: surface, at: new Date().toISOString() });
    try {
      agent.setMessages([message]);
      await copilotkit.runAgent({
        agent,
        forwardedProps: {
          ownerSession: s.id,
          surface,
          sessionId: sourceSession,
          productId: product?.id,
          size: product ? size : undefined,
          contextRevision,
        },
      });
    } catch (e) {
      setError(
        (e as Error).message || "Bob couldn’t finish that reply. Try again.",
      );
      setInput(text);
    } finally {
      setBusy(false);
      setPending(null);
    }
  };
  const suggestions =
    surface === "phone" || surface === "desktop"
      ? s.candidates.length
        ? ["What do you remember?", "Set my budget to $150"]
        : ["Find work sneakers under $120, US 9"]
      : surface === "dayform"
        ? ["Will these be comfortable on my walk?", "Order this pair"]
        : [
            "How does this compare with the first pair?",
            "Will these fit my budget?",
          ];
  return (
    <section
      className={`chat-panel ${surface}`}
      aria-label={`Bob conversation in ${names[surface]}`}
    >
      <header className="chat-header">
        {surface === "phone" && (
          <MessageCircle size={19} className="phone-back" />
        )}
        <Mark />
        <div>
          <h3>
            Bob <span className="personal-tag">YOUR AGENT</span>
          </h3>
          <p>{busy ? "Looking into it…" : "Same Bob. Right here with you."}</p>
        </div>
        <button
          className="icon-button"
          aria-label="Manage Bob’s connections"
          onClick={onConnections}
        >
          <MoreHorizontal size={19} />
        </button>
      </header>
      <div className="continuing-strip">
        <Link2 size={12} />
        {isStore
          ? s.candidates.length
            ? "Continuing your shopping conversation"
            : "Your personal agent, inside this store"
          : "One conversation, across all your apps"}
      </div>
      <div className="chat-scroll" aria-live="polite">
        {!connected ? (
          <div className="revoked-note">
            <Unplug size={25} />
            <h3>Connection paused</h3>
            <p>This store can’t send Bob new context or request actions.</p>
            <button className="outline-button" onClick={onConnections}>
              Manage connections
            </button>
          </div>
        ) : (
          <>
            <div className="conversation-date">
              TODAY <span>·</span> YOUR CONTINUING CONVERSATION
            </div>
            {messages.length === 0 && (
              <div className="chat-welcome">
                <div className="mini-agent-label">
                  <Mark small />
                  <span>Bob</span>
                </div>
                <p>
                  {isStore
                    ? s.candidates.length
                      ? `Hey, you made it. We’re looking for work sneakers — US ${s.preferences.size}, under $${s.preferences.budget}. I can see ${product?.name} here. What would you like to know?`
                      : `Hey, I’m Bob. I can see ${product?.name} in this store. Tell me what matters to you, or start a shortlist on your phone and continue here.`
                    : "Hey, I’m Bob. Tell me what you’re looking for. I’ll bring our conversation along wherever you go."}
                </p>
                {isStore && (
                  <div className="brief-chips">
                    <span>US {s.preferences.size}</span>
                    <span>Under ${s.preferences.budget}</span>
                    <span>
                      {s.preferences.priority.includes("Style")
                        ? "Style first"
                        : "Comfort first"}
                    </span>
                  </div>
                )}
              </div>
            )}
            {messages.map((m) => (
              <div key={m.id} className={`chat-message ${m.role}`}>
                <div className="message-meta">
                  {m.role === "assistant" ? (
                    <>
                      <Mark small />
                      Bob
                    </>
                  ) : (
                    <span>You</span>
                  )}
                  {!isStore && (
                    <span className="message-source">{names[m.source]}</span>
                  )}
                </div>
                <div className="message-bubble">{m.content}</div>
                {m.modelFallback && (
                  <span className="small-note">
                    Model unavailable · local workflow reply
                  </span>
                )}
                {m.kind === "shortlist" && (
                  <div className="shortlist">
                    {s.products
                      .filter((p) => s.candidates.includes(p.id))
                      .map((p) => (
                        <button key={p.id} onClick={() => onVisit(p)}>
                          <img src={p.image} alt={`${p.name} sneaker`} />
                          <div>
                            <span>{names[p.app]}</span>
                            <strong>
                              {p.name} / {p.color}
                            </strong>
                            <small>
                              ${p.price} · US {s.preferences.size}
                            </small>
                          </div>
                          <ArrowUpRight size={15} />
                        </button>
                      ))}
                  </div>
                )}
                {m.kind === "comparison" && (
                  <div className="comparison-mini">
                    <div>
                      <span>DAY ONE</span>
                      <strong>$107.80</strong>
                      <small>Roomier · softer</small>
                      <span className="recommended">Comfort pick</span>
                    </div>
                    <div>
                      <span>ARC 02</span>
                      <strong>$123.20</strong>
                      <small>Slimmer · firmer</small>
                      <span>Includes demo tax</span>
                    </div>
                  </div>
                )}
                {m.kind === "receipt" &&
                  s.orders.find((o) => o.id === m.orderId) && (
                    <Receipt
                      order={s.orders.find((o) => o.id === m.orderId)!}
                    />
                  )}
              </div>
            ))}
            {pending && !s.messages.some((m) => m.id === pending.id) && (
              <div className="chat-message user">
                <div className="message-meta">You</div>
                <div className="message-bubble">{pending.content}</div>
              </div>
            )}
            {busy && (
              <div className="thinking">
                <span />
                <span />
                <span />
                <small>Bob is connecting the context</small>
              </div>
            )}
            {s.quote && (!isStore || s.quote.source === surface) && (
              <Checkout key={s.quote.id} quote={s.quote} snapshot={s} />
            )}
          </>
        )}
        <div ref={bottom} />
      </div>
      <div className="chat-bottom">
        {error && (
          <p className="error-text" role="alert">
            {error}
          </p>
        )}
        <div className="suggestions">
          {suggestions.map((text) => (
            <button
              key={text}
              disabled={busy || !connected}
              onClick={() => void send(text)}
            >
              {text}
              <ArrowUpRight size={11} />
            </button>
          ))}
        </div>
        <form
          className="composer"
          onSubmit={(e) => {
            e.preventDefault();
            void send(input);
          }}
        >
          <input
            aria-label="Message Bob"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={isStore ? "Ask Bob about this pair…" : "Message Bob…"}
            disabled={!connected}
          />
          <button
            aria-label="Send message"
            disabled={!input.trim() || busy || !connected}
          >
            <ArrowUp size={18} />
          </button>
        </form>
        <div className="chat-footnote">
          <LockKeyhole size={10} />
          {s.mode === "live"
            ? "Live AI · your shopping context"
            : "Demo mode · no API key needed"}
          <span className="copilot-label">CopilotKit + AG-UI</span>
        </div>
      </div>
    </section>
  );
}

function Receipt({ order }: { order: Quote }) {
  return (
    <div className="receipt">
      <span className="receipt-heading">
        <CircleCheck size={15} />
        ORDER CONFIRMED
      </span>
      <div className="receipt-product">
        <img src={order.product.image} alt="" />
        <div>
          <strong>
            {order.product.name} / {order.product.color}
          </strong>
          <span>
            US {order.size} · {money(order.total)}
          </span>
        </div>
      </div>
      <div className="receipt-bottom">
        <span>{order.id}</span>
        <span>Simulated order</span>
      </div>
    </div>
  );
}
function Checkout({
  quote: q,
  snapshot: s,
}: {
  quote: Quote;
  snapshot: Snapshot;
}) {
  const [checked, setChecked] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const over = q.total > s.preferences.budget;
  const act = async (approve: boolean) => {
    setBusy(true);
    setError("");
    try {
      await api(
        `/api/sessions/${s.id}/${approve ? "approve" : "cancel-quote"}`,
        {
          method: "POST",
          body: JSON.stringify({ quoteId: q.id, allowOverBudget: checked }),
        },
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="checkout-card">
      <div className="checkout-title">
        <ShieldCheck size={17} />
        <strong>Your call. Always.</strong>
      </div>
      <p>Review {names[q.product.app]}’s checkout</p>
      <div className="checkout-product">
        <img src={q.product.image} alt="" />
        <div>
          <strong>
            {q.product.name} / {q.product.color}
          </strong>
          <span>US {q.size} · Qty 1</span>
        </div>
      </div>
      <dl>
        <div>
          <dt>Subtotal</dt>
          <dd>{money(q.subtotal)}</dd>
        </div>
        <div>
          <dt>Shipping</dt>
          <dd>Free</dd>
        </div>
        <div>
          <dt>Demo tax (10%)</dt>
          <dd>{money(q.tax)}</dd>
        </div>
        <div className="checkout-total">
          <dt>Total</dt>
          <dd>{money(q.total)}</dd>
        </div>
      </dl>
      {over && (
        <label className="over-budget">
          <input
            type="checkbox"
            checked={checked}
            onChange={(e) => setChecked(e.target.checked)}
          />
          I approve {money(q.total - s.preferences.budget)} above my budget.
        </label>
      )}
      {error && <p className="error-text">{error}</p>}
      <button
        className="primary-button full"
        disabled={busy || (over && !checked)}
        onClick={() => void act(true)}
      >
        <Check size={15} />
        {busy ? "Working…" : `Approve demo order · ${money(q.total)}`}
      </button>
      <button
        className="checkout-cancel"
        disabled={busy}
        onClick={() => void act(false)}
      >
        Not yet
      </button>
      <span className="checkout-disclaimer">
        Simulated purchase · no payment is charged
      </span>
    </div>
  );
}

function Modal({
  title,
  children,
  onClose,
}: {
  title: string;
  children: React.ReactNode;
  onClose: () => void;
}) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const before = document.activeElement as HTMLElement;
    ref.current?.focus();
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      if (e.key === "Tab") {
        const nodes = ref.current?.querySelectorAll<HTMLElement>(
          'button, a, input, select, [tabindex="0"]',
        );
        if (!nodes?.length) return;
        const first = nodes[0],
          last = nodes[nodes.length - 1];
        if (
          e.shiftKey &&
          (document.activeElement === first ||
            document.activeElement === ref.current)
        ) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    };
    document.addEventListener("keydown", handler);
    const overflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", handler);
      document.body.style.overflow = overflow;
      before?.focus();
    };
  }, []);
  return (
    <div
      className="modal-backdrop"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        className="modal"
        role="dialog"
        aria-modal="true"
        aria-label={title}
        ref={ref}
        tabIndex={-1}
      >
        <button
          className="modal-close icon-button"
          onClick={onClose}
          aria-label="Close dialog"
        >
          <X size={21} />
        </button>
        <span className="eyebrow">ONEAGENT / YOUR SPACE</span>
        <h2>{title}</h2>
        {children}
      </div>
    </div>
  );
}
function Connections({
  snapshot: s,
  flash,
}: {
  snapshot: Snapshot;
  flash: (s: string) => void;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const update = async (app: string, change: object) => {
    setBusy(true);
    setError("");
    try {
      await api(`/api/sessions/${s.id}/grants/${app}`, {
        method: "PATCH",
        body: JSON.stringify(change),
      });
      flash("Connection preferences saved");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };
  return (
    <>
      <p className="modal-lead">
        Connected stores can share their selected product and answer your
        questions. A connection never authorizes a purchase.
      </p>
      {(["dayform", "stride"] as const).map((app) => (
        <div className="connection-item" key={app}>
          <div>
            <span className={`connection-monogram ${app}`}>
              {app === "dayform" ? "D" : "S"}
            </span>
            <div>
              <strong>{names[app]}</strong>
              <span>
                {s.grants[app].connected
                  ? "Product context & source-session replies"
                  : "Access revoked"}
              </span>
            </div>
            <button
              className={`toggle ${s.grants[app].connected ? "on" : ""}`}
              aria-label={`${s.grants[app].connected ? "Revoke" : "Connect"} ${names[app]}`}
              aria-pressed={s.grants[app].connected}
              disabled={busy}
              onClick={() =>
                void update(app, { connected: !s.grants[app].connected })
              }
            >
              <span />
            </button>
          </div>
          <label>
            <input
              type="checkbox"
              checked={s.grants[app].shareBudget}
              disabled={busy || !s.grants[app].connected}
              onChange={(e) =>
                void update(app, { shareBudget: e.target.checked })
              }
            />
            <span>Share my budget for this store’s own filtering</span>
          </label>
        </div>
      ))}
      {error && <p className="error-text">{error}</p>}
      <div className="technical-note">
        <ShieldCheck size={18} />
        <p>
          Revoking access blocks new messages, product API calls, and checkout.
          It does not erase replies already delivered. This local demo uses one
          trusted backend; independently hosted apps would need separate scoped
          credentials.
        </p>
      </div>
    </>
  );
}
function Pairing({ id, flash }: { id: string; flash: (s: string) => void }) {
  const [base, setBase] = useState(location.origin);
  const [addresses, setAddresses] = useState<string[]>([]);
  const [qr, setQr] = useState("");
  const [target, setTarget] = useState<Surface>("phone");
  const url = `${base}/${target}#session=${id}`;
  useEffect(() => {
    void api<{ addresses: string[] }>("/api/network")
      .then((r) => {
        setAddresses(r.addresses);
        if (r.addresses[0] && /localhost|127.0.0.1/.test(location.hostname))
          setBase(r.addresses[0]);
      })
      .catch(() => {});
  }, []);
  useEffect(() => {
    void QRCode.toDataURL(url, {
      width: 220,
      margin: 1,
      color: { dark: "#163c34", light: "#ffffff" },
    }).then(setQr);
  }, [url]);
  return (
    <>
      <p className="modal-lead">
        Scan to continue this exact conversation on another device. Keep both
        devices on the same Wi-Fi and this server running.
      </p>
      <div className="pair-tabs">
        {(["phone", "desktop"] as const).map((t) => (
          <button
            key={t}
            className={target === t ? "selected" : ""}
            onClick={() => setTarget(t)}
          >
            {t === "phone" ? <Smartphone size={16} /> : <Monitor size={16} />}{" "}
            {names[t]}
          </button>
        ))}
      </div>
      <div className="qr-wrap">
        {qr && <img src={qr} alt="Scan to join this OneAgent session" />}
        <strong>Same Bob. Same memory.</strong>
        <span>Live updates across devices</span>
      </div>
      <label className="pair-host">
        Server address
        <select value={base} onChange={(e) => setBase(e.target.value)}>
          {Array.from(new Set([location.origin, ...addresses])).map((a) => (
            <option key={a} value={a}>
              {a}
            </option>
          ))}
        </select>
      </label>
      <div className="share-url">
        <input aria-label="Device session link" readOnly value={url} />
        <button
          aria-label="Copy device link"
          onClick={() => {
            void navigator.clipboard
              ?.writeText(url)
              .then(() => flash("Device link copied"))
              .catch(() => flash("Select and copy the link above"));
          }}
        >
          <Copy size={16} />
        </button>
      </div>
      <a
        className="primary-button full download-link"
        href={`/${target}#session=${id}`}
        target="_blank"
        rel="noreferrer"
      >
        Open in a new window
        <ExternalLink size={15} />
      </a>
      <p className="small-note">
        The link grants access to this demo session. On a phone, use “Add to
        Home Screen” for an app-like experience. Native desktop launch
        instructions are in README.md.
      </p>
    </>
  );
}

createRoot(document.getElementById("root")!).render(<App />);
