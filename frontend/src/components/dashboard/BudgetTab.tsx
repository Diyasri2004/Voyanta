"use client";

import { useState } from "react";
import { Doughnut } from "react-chartjs-2";
import { Chart as ChartJS, ArcElement, Tooltip, Legend } from "chart.js";

ChartJS.register(ArcElement, Tooltip, Legend);

export default function BudgetTab({ trip }: { trip: any }) {
  const [budgetLimit, setBudgetLimit] = useState(2000);
  const [expenses, setExpenses] = useState([
    { category: "Dining", amount: 450, color: "#ff007f" },
    { category: "Transit", amount: 200, color: "#00f0ff" },
    { category: "Tickets", amount: 350, color: "#39ff14" },
    { category: "Shopping", amount: 150, color: "#f59e0b" },
  ]);

  const totalSpent = expenses.reduce((acc, curr) => acc + curr.amount, 0);
  const remaining = budgetLimit - totalSpent;

  const data = {
    labels: expenses.map(e => e.category),
    datasets: [
      {
        data: expenses.map(e => e.amount),
        backgroundColor: expenses.map(e => e.color),
        borderWidth: 0,
        hoverOffset: 4,
      },
    ],
  };

  const options = {
    cutout: "75%",
    plugins: {
      legend: { display: false },
    },
  };

  return (
    <div className="flex flex-col gap-6">
      <div className="bg-white/5 border border-white/10 rounded-xl p-5 flex items-center justify-between">
        <div>
          <p className="text-[#94A3B8] text-xs font-bold uppercase tracking-wider">Remaining</p>
          <p className="text-3xl font-syne font-bold text-white mt-1">${remaining}</p>
        </div>
        <div className="h-20 w-20 relative">
          <Doughnut data={data} options={options} />
        </div>
      </div>

      <div className="flex flex-col gap-3">
        <h3 className="font-bold text-sm text-white uppercase tracking-widest border-b border-white/10 pb-2">Expenses</h3>
        {expenses.map(e => (
          <div key={e.category} className="flex items-center justify-between bg-white/5 p-3 rounded-lg border border-white/5">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full shadow-[0_0_8px_currentColor]" style={{ backgroundColor: e.color, color: e.color }} />
              <span className="text-sm font-semibold">{e.category}</span>
            </div>
            <span className="text-sm font-bold">${e.amount}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
