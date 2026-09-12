import React, { useEffect, useRef } from "react";
import {
  ArrowUp,
  Check,
  Orbit,
  RotateCcw,
  ShieldCheck,
  Sparkles,
  X,
} from "lucide-react";

export type AgentOutput = {
  id: string;
  source_app: string;
  in_reply_to: string;
  text: string;
  shared_context: Record<string, unknown>;
  confirmed?: boolean;
  proposal?: { name: string; arguments: Record<string, unknown> };
};
export type Conversation = {
  messages: {
    event_id: string;
    source_app: string;
    origin?: string;
    message: { id: string; text: string };
    context: { selected_object?: { name: string } };
  }[];
  outputs: AgentOutput[];
  running: boolean;
  error: string | null;
};
type Props = {
  appName: string;
  sources: Record<string, string>;
  linked: boolean;
  selected?: { name: string };
  conversation: Conversation;
  pending: boolean;
  sending: boolean;
  actionPending: boolean;
  draft: string;
  onDraft: (value: string) => void;
  onSend: (text?: string) => void;
  onConfirm: (output: AgentOutput) => void;
  onRetry: () => void;
  suggestions: string[];
  mobileOpen: boolean;
  onMobileOpen: (value: boolean) => void;
  testMode: boolean;
  children?: React.ReactNode;
};

/** An app-neutral companion panel. Hosts supply context, messages, and actions. */
export function CompanionPanel(props: Props) {
  const { conversation, selected, pending, sending, actionPending } = props;
  const logEnd = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const log = logEnd.current?.parentElement;
    log?.scrollTo({ top: log.scrollHeight, behavior: "smooth" });
  }, [conversation.messages.length, conversation.outputs.length, sending]);
  return (
    <>
      <aside
        className={`agent-panel ${props.mobileOpen ? "mobile-open" : ""}`}
        aria-label="OneAgent conversation"
      >
        <div className="agent-header">
          <div className="agent-avatar">
            <Orbit size={25} />
          </div>
          <div>
            <strong>OneAgent</strong>
            <span>
              {props.linked
                ? "Your agent · synced to Telegram"
                : "Your personal companion"}
            </span>
          </div>
          <button
            className="close-chat icon-button"
            aria-label="Close chat"
            onClick={() => props.onMobileOpen(false)}
          >
            <X size={21} />
          </button>
        </div>
        <div className="agent-context">
          <span className="context-dot" />
          <span>
            With you in <strong>{props.appName}</strong>
          </span>
        </div>
        {selected && (
          <div className="viewing">
            <small>LOOKING AT</small>
            <span>{selected.name}</span>
          </div>
        )}
        <div className="chat-log" role="log" aria-label="Conversation messages">
          <div className="agent-welcome">
            <span className="mini-agent">
              <Orbit size={18} />
            </span>
            <p>
              This chat belongs to {props.appName}.{" "}
              {props.linked
                ? "Our exchanges sync to your private Telegram chat, never to other websites. "
                : "Your messages stay in this website's chat. "}
              {selected
                ? "Ask me about this option or how it compares."
                : "Select an option and ask me anything about it."}
            </p>
          </div>
          {conversation.messages.map((message) => {
            const output = conversation.outputs.find(
              (o) =>
                o.in_reply_to === message.message.id &&
                o.source_app === message.source_app,
            );
            return (
              <React.Fragment key={`${message.source_app}:${message.event_id}`}>
                <div className="conversation-source">
                  {message.origin === "telegram" && "From Telegram → "}
                  {props.sources[message.source_app] || message.source_app}
                </div>
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
                          disabled={actionPending || output.confirmed}
                          onClick={() => props.onConfirm(output)}
                        >
                          <Check size={16} />
                          {output.confirmed
                            ? "Confirmed"
                            : output.proposal.name === "trip.update_brief"
                              ? "Confirm trip brief update"
                              : `Confirm ${output.proposal.name.replace("trip.save_", "")} selection`}
                        </button>
                      )}
                    </div>
                  </div>
                )}
              </React.Fragment>
            );
          })}
          {(pending || sending) && !conversation.error && (
            <div className="thinking">
              <Orbit size={17} className="spin" /> Thinking with your trip in
              mind…
            </div>
          )}
          {conversation.error && (
            <div className="chat-error">
              <p>{conversation.error}</p>
              <button onClick={props.onRetry}>
                <RotateCcw size={14} /> Retry reply
              </button>
            </div>
          )}
          <div ref={logEnd} />
        </div>
        <div className="chat-bottom">
          {conversation.messages.length === 0 && (
            <div className="suggestions">
              {props.suggestions.map((prompt) => (
                <button
                  key={prompt}
                  onClick={() => props.onSend(prompt)}
                  disabled={sending || !selected}
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
              props.onSend();
            }}
          >
            <textarea
              aria-label="Message OneAgent"
              placeholder={
                selected ? "Ask about this option…" : "Ask your agent…"
              }
              value={props.draft}
              onChange={(e) => props.onDraft(e.target.value)}
              rows={2}
              maxLength={16000}
              onKeyDown={(e) => {
                if (
                  e.key === "Enter" &&
                  !e.shiftKey &&
                  !e.nativeEvent.isComposing
                ) {
                  e.preventDefault();
                  props.onSend();
                }
              }}
            />
            <div className="composer-bottom">
              <span>
                <Sparkles size={13} /> Same agent, separate chats
              </span>
              <button
                type="submit"
                aria-label="Send message"
                disabled={sending || !props.draft.trim()}
              >
                <ArrowUp size={18} />
              </button>
            </div>
          </form>
          {props.children}
          <div className="agent-footnote">
            <ShieldCheck size={12} /> Fresh website chat after each restart
          </div>
          {props.testMode && (
            <div className="fixture-banner">
              Test fixture mode · Responses are not live
            </div>
          )}
        </div>
      </aside>
      <button
        className="mobile-chat-toggle"
        onClick={() => props.onMobileOpen(true)}
      >
        <Orbit size={20} /> Ask OneAgent
        {pending && <span className="pending-dot" />}
      </button>
    </>
  );
}
