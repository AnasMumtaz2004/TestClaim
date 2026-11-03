export default function StatusBadge({ status }) {
  const labels = {
    submitted: "Submitted",
    intake: "In intake",
    needs_documents: "Documents needed",
    assessing: "Assessing",
    pending_review: "Under review",
    approved: "Approved",
    rejected: "Rejected",
    settled: "Settled",
  };
  
  const label = labels[status] || status;
  
  let colorClass = "bg-white text-black";
  
  if (status === "submitted" || status === "intake" || status === "assessing") {
    colorClass = "bg-white text-black";
  } else if (status === "needs_documents" || status === "pending_review") {
    colorClass = "bg-accent text-black";
  } else if (status === "approved" || status === "settled") {
    colorClass = "bg-secondary text-white";
  } else if (status === "rejected") {
    colorClass = "bg-white text-black border-dashed";
  }
  
  return (
    <span className={`inline-block font-mono text-xs uppercase tracking-wider px-2 py-1 border-2 border-secondary rounded-none ${colorClass}`}>
      {label}
    </span>
  );
}
