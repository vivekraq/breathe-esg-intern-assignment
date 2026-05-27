# Tradeoffs

1. I did not build live SAP, utility, or Concur connectors. CSV upload is less impressive but lets the prototype focus on realistic row shapes, normalization, review, and auditability. A live connector would require credentials and more time spent on OAuth and network edge cases.

2. I did not build a complete emission factor service. The prototype uses small hard-coded factors to prove the flow. In production, factors need versioning, geography, effective dates, uncertainty, source documents, and approval controls.

3. I did not build full analyst editing and comment threads. The backend supports an `edit` review action and audit events, but the UI keeps actions to approve/reject/lock. A richer editing UI would be useful, but the assignment weight favors data model and ingestion judgment over a full back-office product.
