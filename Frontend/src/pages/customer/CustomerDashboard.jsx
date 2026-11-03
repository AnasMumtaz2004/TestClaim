import { useState, useEffect } from "react";
import Navbar from "../../components/Navbar";
import DataTable from "../../components/DataTable";
import StatusBadge from "../../components/StatusBadge";
import Modal from "../../components/Modal";
import ClaimTimeline from "../../components/ClaimTimeline";
import FileUpload from "../../components/FileUpload";
import { apiRequest } from "../../api";

export default function CustomerDashboard() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [claims, setClaims] = useState([]);
  const [policies, setPolicies] = useState([]);
  const [selectedClaim, setSelectedClaim] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [messages, setMessages] = useState([]);
  const [showFileModal, setShowFileModal] = useState(false);
  const [newMessage, setNewMessage] = useState("");
  const [sendingMessage, setSendingMessage] = useState(false);
  
  const [selectedPolicy, setSelectedPolicy] = useState("");
  const [lossDate, setLossDate] = useState("");
  const [claimedAmount, setClaimedAmount] = useState("");
  const [description, setDescription] = useState("");
  const [submittingClaim, setSubmittingClaim] = useState(false);
  const [claimError, setClaimError] = useState("");
  
  useEffect(() => {
    loadData();
  }, []);
  
  useEffect(() => {
    if (selectedClaim) {
      loadClaimDetails(selectedClaim.id);
    }
  }, [selectedClaim]);
  
  async function loadData() {
    setLoading(true);
    setError("");
    
    try {
      const [claimsData, policiesData] = await Promise.all([
        apiRequest("/customer/claims"),
        apiRequest("/customer/policies"),
      ]);
      
      setClaims(claimsData);
      setPolicies(policiesData);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }
  
  async function loadClaimDetails(claimId) {
    try {
      const [docsData, messagesData] = await Promise.all([
        apiRequest(`/customer/claims/${claimId}/documents`),
        apiRequest(`/customer/claims/${claimId}/messages`),
      ]);
      
      setDocuments(docsData);
      setMessages(messagesData);
    } catch (err) {
      setError(err.message);
    }
  }
  
  async function handleFileClaim() {
    setClaimError("");
    setSubmittingClaim(true);
    
    try {
      const newClaim = await apiRequest("/customer/claims", {
        method: "POST",
        body: JSON.stringify({
          policy_id: selectedPolicy,
          loss_date: new Date(lossDate).toISOString(),
          claimed_amount: parseFloat(claimedAmount),
          description,
        }),
      });
      
      await loadData();
      setShowFileModal(false);
      setSelectedPolicy("");
      setLossDate("");
      setClaimedAmount("");
      setDescription("");
      
      const fullClaim = claims.find(c => c.id === newClaim.id) || newClaim;
      setSelectedClaim(fullClaim);
    } catch (err) {
      setClaimError(err.message);
    } finally {
      setSubmittingClaim(false);
    }
  }
  
  async function handleSendMessage() {
    if (!newMessage.trim()) {
      return;
    }
    
    setSendingMessage(true);
    
    try {
      await apiRequest(`/customer/claims/${selectedClaim.id}/messages`, {
        method: "POST",
        body: JSON.stringify({ body: newMessage }),
      });
      
      setNewMessage("");
      await loadClaimDetails(selectedClaim.id);
    } catch (err) {
      setError(err.message);
    } finally {
      setSendingMessage(false);
    }
  }
  
  function handleDocumentUploaded() {
    if (selectedClaim) {
      loadClaimDetails(selectedClaim.id);
    }
  }
  
  const inProgressCount = claims.filter(c => 
    ["submitted", "intake", "needs_documents", "assessing", "pending_review"].includes(c.status)
  ).length;
  
  const decidedCount = claims.filter(c => 
    ["approved", "rejected", "settled"].includes(c.status)
  ).length;
  
  const columns = [
    { key: "claim_number", label: "Claim number" },
    { key: "line", label: "Line" },
    {
      key: "claimed_amount",
      label: "Amount",
      render: (val) => `₹${val.toLocaleString("en-IN")}`,
    },
    {
      key: "status",
      label: "Status",
      render: (val) => <StatusBadge status={val} />,
    },
    {
      key: "created_at",
      label: "Filed",
      render: (val) => new Date(val).toLocaleDateString("en-IN"),
    },
  ];
  
  if (loading) {
    return (
      <div className="min-h-screen bg-primary">
        <Navbar />
        <main className="px-6 sm:px-8 py-8">
          <div className="font-body text-black">Loading...</div>
        </main>
      </div>
    );
  }
  
  return (
    <div className="min-h-screen bg-primary">
      <Navbar />
      <main className="px-6 sm:px-8 py-8 space-y-8">
        {error && (
          <div className="bg-accent border-l-2 border-secondary p-3 font-mono text-xs text-black">
            {error}
          </div>
        )}
        
        <div className="flex items-center justify-between">
          <h1 className="font-display text-3xl uppercase tracking-tight text-secondary">
            Your claims
          </h1>
          <button
            onClick={() => setShowFileModal(true)}
            className="bg-secondary text-white hover:bg-black font-body font-semibold text-sm px-4 py-3 rounded-none transition-colors"
          >
            File a claim
          </button>
        </div>
        
        <div className="grid grid-cols-3 gap-4">
          <div className="bg-white border-2 border-secondary p-4">
            <div className="font-mono text-xs uppercase tracking-wider text-black mb-2">
              Total claims
            </div>
            <div className="font-display text-4xl text-secondary">
              {claims.length}
            </div>
          </div>
          
          <div className="bg-white border-2 border-secondary p-4">
            <div className="font-mono text-xs uppercase tracking-wider text-black mb-2">
              In progress
            </div>
            <div className="font-display text-4xl text-secondary">
              {inProgressCount}
            </div>
          </div>
          
          <div className="bg-white border-2 border-secondary p-4">
            <div className="font-mono text-xs uppercase tracking-wider text-black mb-2">
              Decided
            </div>
            <div className="font-display text-4xl text-secondary">
              {decidedCount}
            </div>
          </div>
        </div>
        
        <div className="bg-white border-2 border-secondary p-6">
          <h2 className="font-display text-xl uppercase text-secondary mb-4">
            All claims
          </h2>
          <DataTable
            columns={columns}
            rows={claims}
            onRowClick={(claim) => setSelectedClaim(claim)}
            emptyText="You have not filed any claims yet."
          />
        </div>
        
        {selectedClaim && (
          <div className="bg-white border-2 border-secondary p-6 space-y-6">
            <div className="flex items-center justify-between">
              <h2 className="font-display text-xl uppercase text-secondary">
                {selectedClaim.claim_number}
              </h2>
              <StatusBadge status={selectedClaim.status} />
            </div>
            
            <div className="grid md:grid-cols-2 gap-6">
              <div>
                <ClaimTimeline status={selectedClaim.status} />
              </div>
              
              <div className="space-y-4">
                <div>
                  <div className="font-mono text-xs uppercase tracking-wider text-black mb-1">
                    Loss date
                  </div>
                  <div className="font-body text-sm text-black">
                    {new Date(selectedClaim.loss_date).toLocaleDateString("en-IN")}
                  </div>
                </div>
                
                <div>
                  <div className="font-mono text-xs uppercase tracking-wider text-black mb-1">
                    Amount claimed
                  </div>
                  <div className="font-body text-sm text-black">
                    ₹{selectedClaim.claimed_amount.toLocaleString("en-IN")}
                  </div>
                </div>
                
                {selectedClaim.description && (
                  <div>
                    <div className="font-mono text-xs uppercase tracking-wider text-black mb-1">
                      Description
                    </div>
                    <div className="font-body text-sm text-black">
                      {selectedClaim.description}
                    </div>
                  </div>
                )}
              </div>
            </div>
            
            <div>
              <h3 className="font-body font-semibold text-lg text-secondary mb-4">
                Documents
              </h3>
              
              {documents.length > 0 && (
                <div className="space-y-2 mb-4">
                  {documents.map(doc => (
                    <div key={doc.id} className="flex items-center justify-between border-2 border-secondary p-3 bg-white">
                      <div className="font-body text-sm text-black">
                        {doc.doc_type.replace(/_/g, " ")}
                      </div>
                      <div className="flex items-center gap-3">
                        <div className="font-mono text-xs text-black">
                          {Math.round(doc.size_bytes / 1024)} KB
                        </div>
                        {doc.retake ? (
                          <div className="font-mono text-xs text-black bg-accent px-2 py-1">
                            Retake needed
                          </div>
                        ) : (
                          <div className="font-mono text-xs text-black">
                            OK
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
              
              <FileUpload
                claimId={selectedClaim.id}
                onUploaded={handleDocumentUploaded}
              />
            </div>
            
            <div>
              <h3 className="font-body font-semibold text-lg text-secondary mb-4">
                Messages
              </h3>
              
              {messages.length > 0 && (
                <div className="space-y-3 mb-4">
                  {messages.map(msg => (
                    <div key={msg.id} className="border-2 border-secondary p-4 bg-white">
                      <div className="font-mono text-xs uppercase tracking-wider text-black mb-2">
                        {msg.sender_role.replace(/_/g, " ")}
                      </div>
                      <div className="font-body text-sm text-black mb-2">
                        {msg.body}
                      </div>
                      <div className="font-mono text-xs text-black">
                        {new Date(msg.created_at).toLocaleString("en-IN")}
                      </div>
                    </div>
                  ))}
                </div>
              )}
              
              {messages.length > 0 && (
                <div className="space-y-3">
                  <textarea
                    value={newMessage}
                    onChange={(e) => setNewMessage(e.target.value)}
                    placeholder="Type your message..."
                    rows={3}
                    className="w-full bg-white text-black font-body text-sm border-2 border-black rounded-none px-3 py-3 placeholder:text-secondary focus:outline-none focus:ring-2 focus:ring-secondary focus:ring-offset-2"
                  />
                  <button
                    onClick={handleSendMessage}
                    disabled={sendingMessage || !newMessage.trim()}
                    className="bg-secondary text-white hover:bg-black font-body font-semibold text-sm px-4 py-3 rounded-none disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {sendingMessage ? "Sending..." : "Send reply"}
                  </button>
                </div>
              )}
            </div>
          </div>
        )}
      </main>
      
      <Modal
        open={showFileModal}
        title="File a claim"
        onClose={() => {
          setShowFileModal(false);
          setClaimError("");
        }}
      >
        <div className="space-y-6">
          {claimError && (
            <div className="bg-accent border-l-2 border-secondary p-3 font-mono text-xs text-black">
              {claimError}
            </div>
          )}
          
          <div>
            <label className="block font-mono text-xs uppercase tracking-wider font-medium text-black mb-2">
              Policy
            </label>
            <select
              value={selectedPolicy}
              onChange={(e) => setSelectedPolicy(e.target.value)}
              disabled={submittingClaim}
              className="w-full bg-white text-black font-body text-sm border-2 border-black rounded-none px-3 py-3 focus:outline-none focus:ring-2 focus:ring-secondary focus:ring-offset-2 disabled:cursor-not-allowed"
            >
              <option value="">Select a policy</option>
              {policies.map(policy => (
                <option key={policy.id} value={policy.id}>
                  {policy.policy_number} - {policy.product}
                </option>
              ))}
            </select>
          </div>
          
          <div>
            <label className="block font-mono text-xs uppercase tracking-wider font-medium text-black mb-2">
              Loss date
            </label>
            <input
              type="date"
              value={lossDate}
              onChange={(e) => setLossDate(e.target.value)}
              disabled={submittingClaim}
              className="w-full bg-white text-black font-body text-sm border-2 border-black rounded-none px-3 py-3 focus:outline-none focus:ring-2 focus:ring-secondary focus:ring-offset-2 disabled:cursor-not-allowed"
            />
          </div>
          
          <div>
            <label className="block font-mono text-xs uppercase tracking-wider font-medium text-black mb-2">
              Amount
            </label>
            <input
              type="number"
              value={claimedAmount}
              onChange={(e) => setClaimedAmount(e.target.value)}
              disabled={submittingClaim}
              placeholder="0"
              className="w-full bg-white text-black font-body text-sm border-2 border-black rounded-none px-3 py-3 placeholder:text-secondary focus:outline-none focus:ring-2 focus:ring-secondary focus:ring-offset-2 disabled:cursor-not-allowed"
            />
          </div>
          
          <div>
            <label className="block font-mono text-xs uppercase tracking-wider font-medium text-black mb-2">
              Description
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              disabled={submittingClaim}
              rows={4}
              className="w-full bg-white text-black font-body text-sm border-2 border-black rounded-none px-3 py-3 placeholder:text-secondary focus:outline-none focus:ring-2 focus:ring-secondary focus:ring-offset-2 disabled:cursor-not-allowed"
            />
          </div>
          
          <button
            onClick={handleFileClaim}
            disabled={submittingClaim || !selectedPolicy || !lossDate || !claimedAmount}
            className="w-full bg-secondary text-white hover:bg-black font-body font-semibold text-sm rounded-none py-3.5 px-4 transition-colors disabled:bg-secondary disabled:cursor-not-allowed disabled:opacity-50"
          >
            {submittingClaim ? "Submitting..." : "Submit claim"}
          </button>
        </div>
      </Modal>
    </div>
  );
}
