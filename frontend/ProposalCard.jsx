function ProposalCard({ proposal, agent }) {
  const isBuyer = agent === "buyer";

  return (
    <div className="rounded-xl border border-zinc-700 bg-zinc-900 p-5">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-lg font-semibold">
          {isBuyer ? "Buyer Agent" : "Supplier Agent"}
        </h3>

        <span className="rounded-full bg-zinc-800 px-3 py-1 text-xs">
          {proposal.action}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-4">

        <div>
          <p className="text-sm text-zinc-400">Price</p>
          <p className="text-xl font-semibold">
            ₹{proposal.price.toLocaleString()}
          </p>
        </div>

        <div>
          <p className="text-sm text-zinc-400">Delivery</p>
          <p className="text-xl font-semibold">
            {proposal.delivery_days} days
          </p>
        </div>

        <div>
          <p className="text-sm text-zinc-400">Payment</p>
          <p className="text-xl font-semibold">
            Net {proposal.payment_days}
          </p>
        </div>

        <div>
          <p className="text-sm text-zinc-400">SLA Penalty</p>
          <p className="text-xl font-semibold">
            {proposal.sla_penalty}%
          </p>
        </div>

      </div>
    </div>
  );
}

export default ProposalCard;