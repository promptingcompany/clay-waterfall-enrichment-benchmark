"""Clay through the Public API (https://api.clay.com/public/v0, header clay-api-key). Each contact
runs four routines in sequence, all with exact inputs (no automatic or AI input mapping):
1. CLAY_ROUTINE_ID_COMPANY: Clay's managed "Enrich Company" function, from the company domain. It
   supplies the company name later steps need, plus the firmographics.
2. The arm's email routine:
   - CLAY_ROUTINE_ID_WATERFALL: Clay's managed "Work Email" function, its default email waterfall
   - CLAY_ROUTINE_ID_SINGLE: that waterfall cut to its first provider, Findymail (find + its validation)
3. CLAY_ROUTINE_ID_LINKEDIN: Clay's managed "Person LinkedIn URL" function (its own default waterfall),
   from name, company name and domain. Clay's phone waterfall needs a LinkedIn URL; same step in both arms.
4. The arm's phone routine, for contacts with a LinkedIn URL:
   - CLAY_ROUTINE_ID_PHONE_WATERFALL: Clay's managed "Mobile Phone Number" function (default phone waterfall)
   - CLAY_ROUTINE_ID_PHONE_SINGLE: Forager alone, the default waterfall's first provider

Request shapes are from the Clay CLI's documented API (`clay routines runs start/get --help`):
POST /routines/{id}/run with {"items": [{"id", "inputs"}]} returns {"routine_run_id"} (the CLI shows it as
routineRunId); GET /routines/run/{runId}/results returns {"status", "data": [{"id", "status", "result": {...}}]}.
One item per run, so latency is per contact. Every started run ID goes in the journal before
anything else, so a resumed run polls it instead of paying to start it again.
Usage is read per table in Clay (bench usage --units), so balance() stays None.
"""
import time

from benchkit.adapters import Adapter, http_json, require_env, result

from .common import fields, find

BASE = "https://api.clay.com/public/v0"
POLL_S, MAX_WAIT_S, POST_PAUSE_S = 30, 3 * 3600, 0.2
DONE, FAILED = {"complete", "completed"}, {"validation_failed", "processing_failed", "failed", "error", "cancelled"}


class ClayRoutine(Adapter):
    platform = "clay"
    docs_url = "https://api.clay.com/public/v0"
    routine_env = phone_env = ""
    email_inputs = ("Full Name", "Company Domain", "Company Name")   # exactly what each routine declares
    phone_inputs = ("Social Profile URL", "Full Name", "Company Name", "Company Domain")

    def __init__(self):
        self.required_env = ("CLAY_API_KEY", "CLAY_ROUTINE_ID_COMPANY", self.routine_env, "CLAY_ROUTINE_ID_LINKEDIN", self.phone_env)

    def _headers(self):
        return {"clay-api-key": require_env("CLAY_API_KEY")[0]}

    def _stage(self, rows, routine, inputs_of, journal, tag):
        """Run one routine per row (started first, then polled). Returns {input_id: (data, ms, audit)}
        for finished runs and {input_id: (error, status, ms, audit)} for failures."""
        started, done, failed = {}, {}, {}
        for row in rows:
            i, key = row["input_id"], f"{tag}:{row['input_id']}"
            if key in journal:
                started[i] = (journal[key], None, None)   # started in an earlier session: its start time is unknown
                continue
            body = {"items": [{"id": i, "inputs": inputs_of(row)}]}
            t_start = time.monotonic()
            status, data, ms, audit = http_json("POST", f"{BASE}/routines/{routine}/run", headers=self._headers(), body=body)
            run_id = find(data, "routine_run_id", "routineRunId") if status in (200, 201, 202) else None
            if run_id:
                journal[key] = run_id
                started[i] = (run_id, t_start, audit)
            else:
                failed[i] = (str(data)[:300], status, ms, audit)
            time.sleep(POST_PAUSE_S)
        deadline = time.monotonic() + MAX_WAIT_S
        while started and time.monotonic() < deadline:
            for i, (run_id, t_start, audit) in list(started.items()):
                # Latency is wall time from starting the run to seeing it finish (to within one poll interval).
                elapsed = None if t_start is None else round((time.monotonic() - t_start) * 1000, 1)
                status, data, ms2, audit2 = http_json("GET", f"{BASE}/routines/run/{run_id}/results?limit=100", headers=self._headers())
                state = str((data or {}).get("status", "") if isinstance(data, dict) else "").lower()
                both = {"start": audit, "results": audit2}
                items = (data or {}).get("data") or [] if isinstance(data, dict) else []
                if status in (200, 202) and state not in DONE | FAILED:
                    continue   # still running: Clay answers 202 "in_progress" until the run finishes
                if status == 200 and state in DONE and not any(str(it.get("status", "")).lower() in FAILED for it in items):
                    done[i] = (items, elapsed, both)
                    del started[i]
                else:   # the call or the run failed, or the run finished but its item failed
                    failed[i] = (str(data)[:300], status, elapsed, both)
                    del started[i]
                time.sleep(POST_PAUSE_S)
            if started:
                time.sleep(POLL_S)
        for i, (run_id, _, _) in started.items():
            print(f"  {i}: {tag} run {run_id} not finished after {MAX_WAIT_S} s; resume to keep polling")
        return done, failed

    def enrich_batch(self, rows, save, journal):
        company_rt, email_rt, linkedin_rt, phone_rt = require_env(
            "CLAY_ROUTINE_ID_COMPANY", self.routine_env, "CLAY_ROUTINE_ID_LINKEDIN", self.phone_env)
        co, co_failed = self._stage(rows, company_rt, lambda r: {"Company Identifier": r["company_domain"]}, journal, "company")
        # A failed company lookup doesn't stop the contact: later steps fall back to the domain as company name.
        company = {i: (find(d, "Enrich Company") or {}) for i, (d, _, _) in co.items()} | {i: {} for i in co_failed}

        def given(r, extra=None):
            c = company[r["input_id"]]
            return {"Full Name": f"{r['first_name']} {r['last_name']}".strip(), "Company Domain": r["company_domain"],
                    "Company Name": find(c, "name") or r["company_domain"], **(extra or {})}

        todo = [r for r in rows if r["input_id"] in company]
        em, em_failed = self._stage(todo, email_rt, lambda r: {k: given(r)[k] for k in self.email_inputs}, journal, "email")
        li, li_failed = self._stage(todo, linkedin_rt, lambda r: {"Full name": given(r)["Full Name"], "Company name": given(r)["Company Name"],
                                                                  "Company domain": r["company_domain"]}, journal, "linkedin")
        # Clay's LinkedIn step returns "linkedin.com/in/..." but its phone step only accepts a full https URL.
        url = {i: (u if "://" in u else "https://" + u) for i, (d, _, _) in li.items() if (u := find(d, "LinkedIn URL"))}
        with_url = [r for r in todo if url.get(r["input_id"])]
        ph, ph_failed = self._stage(with_url, phone_rt, lambda r: {k: given(r, {"Social Profile URL": url[r["input_id"]]})[k]
                                                                    for k in self.phone_inputs}, journal, "phone")
        for r in todo:
            i, c = r["input_id"], company[r["input_id"]]
            if (i not in em and i not in em_failed) or (i not in li and i not in li_failed) or \
                    (url.get(i) and i not in ph and i not in ph_failed):
                continue   # a step is still running in Clay: --resume polls it from the journal
            steps = {"company": co.get(i) or co_failed.get(i), "email": em.get(i) or em_failed.get(i),
                     "linkedin": li.get(i) or li_failed.get(i), "phone": ph.get(i) or ph_failed.get(i)}
            # Time to email (company + email steps), comparable with the other vendors' synchronous lookups;
            # the LinkedIn and phone steps aren't counted, as other vendors' async phones aren't.
            parts = [steps[k][-2] for k in ("company", "email") if steps[k]]
            ms = None if any(x is None for x in parts) else sum(parts)
            audit = {k: v[-1] for k, v in steps.items() if v}
            firmo = dict(company_name=find(c, "name"), employee_count=find(c, "employee_count"),
                         industry=find(c, "industry"), hq_country=find(c, "country"))
            phone = find(ph[i][0], "Mobile Phone", "mobile_phone") if i in ph else None
            if i in em:
                save(i, result(fields(email=find(em[i][0], "Work Email", "work_email"), phone=phone, **firmo),
                               status=200, latency_ms=ms, audit=audit))
            else:
                err, status = em_failed[i][0], em_failed[i][1]
                save(i, result(fields(phone=phone, **firmo), ok=False, status=status, error=err, latency_ms=ms, audit=audit))


class ClayWaterfall(ClayRoutine):
    name = "clay_waterfall"
    routine_env = "CLAY_ROUTINE_ID_WATERFALL"
    phone_env = "CLAY_ROUTINE_ID_PHONE_WATERFALL"


class ClaySingle(ClayRoutine):
    name = "clay_single"
    platform = "clay_single"
    routine_env = "CLAY_ROUTINE_ID_SINGLE"
    phone_env = "CLAY_ROUTINE_ID_PHONE_SINGLE"
    email_inputs = ("Full Name", "Company Domain")   # Findymail's finder needs no company name
    phone_inputs = ("Social Profile URL",)            # Forager's finder needs only the LinkedIn URL
