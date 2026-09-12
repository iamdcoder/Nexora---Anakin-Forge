import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
} from "recharts";


function ConcessionChart({ rounds }) {

  const data = rounds.map((round) => ({
    round: round.round,
    Buyer: round.buyer.price,
    Supplier: round.supplier.price,
  }));

  return (
    <div className="h-80 w-full">

      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data}>

          <CartesianGrid strokeDasharray="3 3" />

          <XAxis
            dataKey="round"
            label={{
              value: "Round",
              position: "insideBottom",
              offset: -5,
            }}
          />

          <YAxis />

          <Tooltip />

          <Legend />

          <Line
            type="monotone"
            dataKey="Buyer"
            strokeWidth={2}
          />

          <Line
            type="monotone"
            dataKey="Supplier"
            strokeWidth={2}
          />

        </LineChart>
      </ResponsiveContainer>

    </div>
  );
}

export default ConcessionChart;