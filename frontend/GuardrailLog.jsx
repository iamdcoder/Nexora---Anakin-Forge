import { useEffect, useRef } from "react";

const TYPE_META = {
  proposal_blocked: { icon: "🚫", cls: "border-red-900/40 bg-red-950/20 text-red-300" },
  agreement_reached: { icon: "✅", cls: "border-emerald-900/40 bg-emerald-950/20 text-emerald-300" },
  deadlock: { icon: "🔴", cls: "border-orange-900/40 bg-orange-950/20 text-orange-300" },
  contract_generated: { icon: "📄", cls: "border-indigo-900/40 bg-indigo-950/20 text-indigo-300" },
  default: { icon: "📋", cls: "border-white/10 bg-white/5 text-gray-300" },
};

function GuardrailLog({ events = [] }) {
  const ref = useRef(null);

  useEffect(() => {
    if (ref.current) ref.current.scrollTop = ref.current.scrollHeight;
  }, [events]);

  if (!events.length) {
    return null;
  }

  return (
    <div ref={ref} className="overflow-auto max-h-72 space-y-1.5 pr-1">
      {events.map((e, i) => {
        const meta = TYPE_META[e.event_type] ?? TYPE_META.default;
        return (
          <div
            key={i}
            className={`flex items-start gap-2 rounded-lg border p-2.5 text-xs ${meta.cls}`}
          >
            <span className="shrink-0 mt-px">{meta.icon}</span>
            <div className="flex-1 min-w-0">
              <div className="flex flex-wrap items-center gap-1.5 font-medium">
                <span className="capitalize">
                  {e.event_type.replace(/_/g, " ")}
                </span>
                <span className="text-zinc-500">·</span>
                <span className="text-zinc-400">{e.actor}</span>
                {e.round_number != null && (
                  <span className="text-zinc-500">R{e.round_number}</span>
                )}
              </div>
              {e.event_type === "proposal_blocked" &&
                e.details?.violations?.length > 0 && (
                  <p className="mt-0.5 truncate text-red-400">
                    {e.details.violations[0]}
                  </p>
                )}
              {e.event_type === "agreement_reached" &&
                e.details?.final_proposal?.price != null && (
                  <p className="mt-0.5 text-emerald-400">
                    ₹{e.details.final_proposal.price.toFixed(2)}
                  </p>
                )}
            </div>
            <span className="shrink-0 text-zinc-600">
              {new Date(e.timestamp).toLocaleTimeString()}
            </span>
          </div>
        );
      })}
    </div>
  );
}

export default GuardrailLog;