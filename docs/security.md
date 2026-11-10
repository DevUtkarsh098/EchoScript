# Security model

Production must disable mock authentication and validate Cognito JWT signature, issuer, expiry, `token_use`, and client association against cached JWKS. Browser tokens remain in memory; refresh persistence should use a backend-for-frontend with HttpOnly, Secure, SameSite cookies.

S3 buckets are private, encrypted, versioned, and public access is blocked. IAM policies must name exact bucket/object ARNs. Kubernetes permissions limit ingest-service to creating and inspecting Jobs in the application namespace. Metrics and administrative tools are not exposed through the user ingress.

Use HTTPS before enabling Cognito. CORS is an explicit origin list. Rotate internal service tokens and HeyGen secrets, redact credentials and raw transcript content from logs, and scan dependencies, secrets, Terraform, and images in CI.

## Jenkins security gates

The handover branch runs Trivy filesystem secret scanning before delivery, runtime, and infrastructure pipeline work. It explicitly disables Trivy's default Markdown allow rule so documentation examples are included, and disables ignore-file loading. Scanner stdout/stderr is suppressed to keep matched source content out of Jenkins logs; the wrapper preserves the scanner exit status and reports failure generically. Findings are not archived, so investigate them in a controlled environment. A missing Trivy executable also fails the stage. Image vulnerability scans block both HIGH and CRITICAL findings and disable ignore-file loading. Keep these gates enabled and do not add broad ignore rules; investigate any finding and document narrowly scoped exceptions only through review.

