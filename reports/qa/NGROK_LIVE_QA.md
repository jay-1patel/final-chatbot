# Ngrok-only live QA (target)

**Base:** `https://prominent-faster-dropper.ngrok-free.dev/`  
**Auth:** superadmin login OK (`role=super_admin`)  
**Tenants seen:** `leewaytest`, `makemytrip` (Active Test Bot), `p` (Prestigue), `s` (sbi), `troogood`  
**Scope:** live API + console only (no local `:9000` / `:5173`)  
**Writes:** none this pass (upload/mutation probes not run without explicit approval)

## Confirmed live bugs

| ID | Sev | Finding | Evidence |
|---|---|---|---|
| NGROK-01 | **Blocker** | `POST /api/test-simulator` with `tenant_id` ∈ {`p`,`makemytrip`,`troogood`,`s`} all return MakeMyTrip welcome + corrupted checklist header | API responses: header starts `Booking Checklist…`, body `Welcome to MakeMyTrip!` for every tid |
| NGROK-02 | **Major** | MakeMyTrip Profile Display/Company name = truncated checklist text | Browser `#/tenants/makemytrip/profile` |
| NGROK-03 | **Major** | Prestigue Intents contain foreign kit content (Skyline Realty, SG Highway, Ahmedabad RERA) mixed with Prestige Bangalore offerings | Browser `#/tenants/p/intents` |
| NGROK-04 | **Major** | Live offering copy still has `[Confirm: …]` / `[Confirm inventory]` placeholders | Browser `#/tenants/p/offerings` |
| NGROK-05 | **Minor** | Callbacks nav badge shows **5** but filter **all** lists **0** (“No callbacks”) | Browser `#/tenants/p/callbacks` |
| NGROK-06 | **Minor** | Deep link `#/tenants/p/integrations` → **Unknown view** | Browser |
| NGROK-07 | **Minor** | After opening MakeMyTrip profile URL, sidebar still labeled Prestigue | Browser shell while URL=`…/makemytrip/profile` |

## Panels that loaded OK (Prestigue / shared)

Overview, Uploads, Profile (Prestigue brand OK), Menu (preview header Prestige Group OK — unlike simulator), Properties (5), Customers (empty), Callbacks UI, Intents Editor, Team, Login.

## Contrast

Console **menu preview** for Prestigue is correct (`Prestige Group`), but **simulator/WhatsApp path** ignores tenant and serves Active Test Bot (MakeMyTrip). So the bug is routing/override, not the Prestigue published profile itself.

## Still needed (needs your OK)

- Upload matrix / bifurcation write tests (prefer a new throwaway tenant, not `p`/`makemytrip`)
- Clear or change Active Test Bot and re-run simulator matrix
- Live WhatsApp send to designated test number (capture-only vs live)
