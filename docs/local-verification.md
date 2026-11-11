# Local branch verification

Date: 2026-11-12. Branch: `giri`, starting commit `0a8449b`. Docker Desktop engine 29.9.2. Application services were built and run locally; no AWS calls, deployment, production state access or Jenkins controller startup occurred during this verification.

## Results

| Check | Result |
| --- | --- |
| Frontend Docker build and TypeScript compilation | Passed |
| Frontend auth tests | 3 passed |
| Frontend lint after fixes | Passed; 2 development fast-refresh warnings in `auth.tsx` |
| API Docker build and tests | Passed; 10 tests, 1 Starlette/httpx deprecation warning |
| Worker Docker build and tests | Passed; 2 tests including actual PyAV WAV decoding and faster-whisper import |
| Optional video-service summarizer unit test | 1 passed; rendering/provider integration not tested |
| CI safety regression tests | 18 passed |
| Trivy source secret scan | Passed; scanner details suppressed; clean exported source plus lint fixes, no local credentials |
| Both Terraform roots: format and backend-free validation | Passed offline using cached locked providers; no plan/apply |
| Ansible lint and both playbook syntax checks | Passed |
| Disposable local Ansible workspace check/apply/repeat apply/repeat check | Passed; repeat apply/check `changed=0 unreachable=0 failed=0` |
| Local frontend HTML, JS/CSS assets and `/dashboard` route | HTTP 200 |
| API `/health` and `/ready` | Passed |
| WAV upload, start, demo processing, TXT/SRT/VTT and original audio download | Passed |
| Wrong upload length and unsupported file type | Rejected with HTTP 400 / 422 |
| Optional local recap video | Failed; API image has no `ffmpeg` executable |

The source's `npm run lint` command originally failed because no ESLint configuration existed. Added a flat configuration using the already installed TypeScript/React plugins and removed four unused imports and one unused map parameter. Application processing and authentication behavior were not changed.

## Running services

- Frontend: <http://localhost:5173>
- API health: <http://localhost:8000/health>
- API docs: <http://localhost:8000/docs>
- Compose project: `echoscript-local-check`.
- Both ports bind to loopback only. Test data is isolated under ignored `.local-run/local-check-data`, preserving existing `data/` and `.env`.
- Built images: `echoscript-api:local-check`, `echoscript-worker:local-check`, `echoscript-worker-tests:local-check`, `echoscript-frontend:local-check`, `echoscript-ansible-test:local-check`.
- Machine-local Compose override, HTTP smoke script and result JSON are retained under ignored `.local-run/compose-check.yml`, `.local-run/local-check-smoke.py` and `.local-run/local-check-results.json`.

To stop only this test stack while retaining test files:

```powershell
docker compose --env-file .env.example -p echoscript-local-check -f docker-compose.yml -f .local-run/compose-check.yml stop
```

## Limits and findings

Compose explicitly enables local mock authentication and processing. Successful demo output does not establish real speech recognition, Cognito login, or an AWS end-to-end release. The worker tests exercise decoding/subtitle behavior without downloading a Whisper model. Real speech inference was not verified in this run.

The optional recap endpoint produced `video_status=FAILED`, consistent with its `ffmpeg` subprocess dependency being absent from the API image. The separate optional video-service container does not supply a binary to the API process. That feature needs a deliberately scoped local runtime/dependency change and a successful rendering check before it can be reported working; the production API image was not expanded during this check.

Frontend installation reported seven moderate dependency advisories. A fresh HIGH/CRITICAL image vulnerability scan was not run as part of this local functional check; previous scans are recorded separately in `ci-verification.md`.

The AWS host playbook was syntax-checked only. Its disposable AWS target checks, real AWS Jenkins pipeline, deployment smoke test, live rollback and backup restore remain pending, separate from these local results. Browser interaction and visual behavior were not verified; HTTP/assets, compilation and automated tests were checked.
