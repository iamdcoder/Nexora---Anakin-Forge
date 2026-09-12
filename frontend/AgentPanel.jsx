function AgentPanel({
  name,
  role,
  targetPrice,
  latestProposal,
}) {
  return (
    <div className="rounded-xl border border-zinc-700 bg-zinc-950 p-6">

      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-zinc-800">
          🤖
        </div>

        <div>
          <h2 className="font-semibold">{name}</h2>
          <p className="text-sm text-zinc-400">{role}</p>
        </div>
      </div>

      <div className="mt-5">
        <p className="text-sm text-zinc-400">
          Current target
        </p>

        <p className="text-2xl font-bold">
          ₹{targetPrice.toLocaleString()}
        </p>
      </div>

      {latestProposal && (
        <div className="mt-5 border-t border-zinc-800 pt-5">
          <p className="text-sm text-zinc-400">
            Latest proposal
          </p>

          <p className="mt-1 font-medium">
            ₹{latestProposal.price.toLocaleString()}
          </p>
        </div>
      )}

    </div>
  );
}

export default AgentPanel;