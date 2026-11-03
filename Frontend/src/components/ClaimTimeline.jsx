export default function ClaimTimeline({ status }) {
  const steps = [
    { label: "Submitted", index: 0 },
    { label: "Intake", index: 1 },
    { label: "Assessment", index: 2 },
    { label: "Review", index: 3 },
    { label: "Decision", index: 4 },
    { label: "Settled", index: 5 },
  ];
  
  const statusMap = {
    submitted: 0,
    intake: 1,
    needs_documents: 1,
    assessing: 2,
    pending_review: 3,
    approved: 4,
    rejected: 4,
    settled: 5,
  };
  
  const currentStepIndex = statusMap[status] ?? 0;
  
  return (
    <div className="space-y-4">
      {steps.map((step) => {
        const isDone = step.index < currentStepIndex;
        const isCurrent = step.index === currentStepIndex;
        const isUpcoming = step.index > currentStepIndex;
        
        let markerClass = "bg-white text-black";
        let labelClass = "font-body text-sm";
        
        if (isDone) {
          markerClass = "bg-secondary text-white";
        } else if (isCurrent) {
          markerClass = "bg-accent text-black";
          labelClass = "font-body text-sm font-bold";
        }
        
        let displayLabel = step.label;
        if (step.label === "Decision" && status === "approved") {
          displayLabel = "Approved";
        } else if (step.label === "Decision" && status === "rejected") {
          displayLabel = "Rejected";
        }
        
        return (
          <div key={step.index} className="flex items-start gap-3">
            <div className={`w-8 h-8 border-2 border-secondary rounded-none flex items-center justify-center ${markerClass}`}>
              <span className="font-mono text-xs">{step.index + 1}</span>
            </div>
            <div>
              <div className={labelClass}>{displayLabel}</div>
              {step.label === "Intake" && status === "needs_documents" && (
                <div className="font-mono text-xs text-black">Documents needed</div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
