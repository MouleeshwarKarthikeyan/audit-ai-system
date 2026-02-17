import pandas as pd
import numpy as np
import io
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import xlsxwriter

# ============================================================
# ISO 9001:2015 CLAUSE MASTER (EXACT COPY FROM USER)
# ============================================================
ISO_CLAUSES = {
    "INTERNAL AUDIT": "9.2 Internal Audit",
    "MANAGEMENT REVIEW": "9.3 Management Review",
    "TRAINING MANAGEMENT": "7.2 Competence",
    "SKILL/COMPETENCY MATRIX": "7.2 Competence",
    "DOCUMENT CONTROL": "7.5 Documented Information",
    "DEVIATION MANAGEMENT": "8.7 Control of Nonconforming Outputs",
    "PROCESS CONFIRMATION": "8.5 Production & Service Provision",
    "PRODUCT AUDIT (COPA,PEP, SALAPA)": "8.6 Release of Products & Services",
    "TEST EQUIPMENT MANAGEMENT": "7.1.5 Monitoring & Measuring Resources",
    "EV PARTS MANAGEMENT": "8.4 Control of Externally Provided Processes",
    "PAINT INSPECTION": "8.6 Release of Products & Services",
    "Q CHECK PROCESS": "8.6 Release of Products & Services",
    "Q GATES": "8.6 Release of Products & Services",
    "MAINTENANCE MANAGEMENT (PREVENTIVE)": "7.1.3 Infrastructure",
    "BLOCKING PROCESS": "8.7 Control of Nonconforming Outputs",
    "CONSUMABLE MANAGEMENT": "8.5 Production & Service Provision",
    "HR PROCESS": "7.1.2 People",
    "TOOLING (PFU)": "7.1.3 Infrastructure",
    "ESD COMPLIANCE": "7.1.5 Monitoring & Measuring Resources",
    "LAUNCH MANAGEMENT": "6.3 Planning of Changes"
}

HIDDEN = [
    "governance oversight failure",
    "accountability gap",
    "policy enforcement weakness",
    "segregation of duties violation",
    "systemic compliance weakness"
]

LEAKAGE = [
    "control override",
    "manual dependency",
    "approval bypass",
    "data integrity failure",
    "documentation weakness"
]

def map_iso(process_name):
    for key in ISO_CLAUSES:
        if key.lower() in str(process_name).lower():
            return ISO_CLAUSES[key]
    return "ISO 9001:2015 – General Process Control"

class AuditEngine:
    def __init__(self):
        print("🔄 Initializing Enterprise Audit Engine (User Original Logic)...")
        # MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
        self.model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2", device="cpu")
        self.hidden_emb = self.model.encode(HIDDEN, normalize_embeddings=True)
        self.leak_emb = self.model.encode(LEAKAGE, normalize_embeddings=True)
        
        self.df_plan = pd.DataFrame({"Process": ["General Process", "Management", "Operations", "Support", "Quality"]})
        self.plan_embeddings = self.model.encode(
            self.df_plan["Process"].astype(str).tolist(),
            normalize_embeddings=True
        )
        self.df_findings = None
        self.finding_embeddings = None
        self.df_results = None

    def process_audit_plan(self, file_content):
        # EXACT LOGIC: col_plan = df_plan_raw.astype(str).stack().str.len().groupby(level=1).mean().idxmax()
        df_plan_raw = pd.read_excel(io.BytesIO(file_content))
        col_plan = df_plan_raw.astype(str).stack().str.len().groupby(level=1).mean().idxmax()
        self.df_plan = df_plan_raw[[col_plan]].copy()
        self.df_plan.columns = ["Process"]
        self.df_plan.dropna(inplace=True)
        
        self.plan_embeddings = self.model.encode(
            self.df_plan["Process"].astype(str).tolist(),
            normalize_embeddings=True
        )
        return len(self.df_plan)

    def process_findings(self, files_data, append=False):
        all_findings = []
        for filename, content in files_data:
            df_raw = pd.read_excel(io.BytesIO(content))
            col_find = df_raw.astype(str).stack().str.len().groupby(level=1).mean().idxmax()
            df = df_raw[[col_find]].copy()
            df.columns = ["Finding"]
            
            # Country handling
            country_col = None
            for c in df_raw.columns:
                if "country" in c.lower():
                    country_col = c
                    break
            if country_col:
                df["Country"] = df_raw[country_col]
            else:
                df["Country"] = filename
            all_findings.append(df)
            
        if not all_findings: return 0
        
        new_findings = pd.concat(all_findings, ignore_index=True)
        new_findings.dropna(inplace=True)

        if append and self.df_findings is not None:
             self.df_findings = pd.concat([self.df_findings, new_findings], ignore_index=True)
        # Avoid duplicating if append is False (default behavior is overwrite)
        else:
             self.df_findings = new_findings
             
        return len(self.df_findings)

    def calculate_scores(self):
        # EXACT LOGIC FROM USER SCRIPT
        # EXACT LOGIC FROM USER SCRIPT
        print("DEBUG: Calculating scores. df_findings:", len(self.df_findings) if self.df_findings is not None else 0)
        if self.df_findings is None: return
        # df_plan is now guaranteed to exist

        self.finding_embeddings = self.model.encode(
            self.df_findings["Finding"].astype(str).tolist(),
            normalize_embeddings=True
        )

        results = []
        for i, emb in enumerate(self.finding_embeddings):
            emb = emb.reshape(1, -1)

            # SCORING
            sim_p = cosine_similarity(emb, self.plan_embeddings)
            idx_p = sim_p.argmax()
            process = self.df_plan.iloc[idx_p]["Process"]
            score_p = sim_p.max()

            sim_h = cosine_similarity(emb, self.hidden_emb)
            idx_h = sim_h.argmax()
            hidden = HIDDEN[idx_h]
            score_h = sim_h.max()

            sim_l = cosine_similarity(emb, self.leak_emb)
            idx_l = sim_l.argmax()
            leakage = LEAKAGE[idx_l]
            score_l = sim_l.max()

            # FORMULA
            escalation = (score_p*0.5 + score_h*0.3 + score_l*0.2)
            escalation = (escalation**0.5) * 100
            escalation = round(float(escalation),2)

            # CATEGORIES
            if escalation >= 90: category = "Top Critical"
            elif escalation >= 70: category = "High"
            elif escalation >= 40: category = "Moderate"
            elif escalation >= 10: category = "Low"
            else: category = "Clear"

            hidden_flag = "Yes" if score_h > 0.35 else "No"
            leak_flag = "Yes" if score_l > 0.35 else "No"
            
            audit_status = "Audited" if escalation >= 40 else "Not Audited"
            checklist_status = "Action Required" if escalation >= 40 else "Monitor"
            
            business_reason = (
                f"Finding mapped to '{process}' with significant control similarity. "
                f"Indicates {hidden}. Potential risk exposure via {leakage}."
            )
            
            # ISO MAPPING
            iso_clause = map_iso(process)

            # --- ENHANCEMENTS (Requested: Remediation/Schedule) ---
            remediation = f"Review protocol for {process}."
            if "competence" in iso_clause.lower() or "training" in self.df_findings.iloc[i]['Finding'].lower():
                remediation = "Conduct Skill Gap Analysis (ILUO Matrix)."
            elif "documents" in iso_clause.lower():
                remediation = "Update Control Plan in DMS."
            
            schedule = "Annual"
            if escalation >= 90: schedule = "IMMEDIATE (24hrs)"
            elif escalation >= 70: schedule = "Urgent (7 days)"

            results.append({
                "Country": self.df_findings.iloc[i]["Country"],
                "Process": process,
                "ISO 9001:2015 Clause": iso_clause,
                "Finding": self.df_findings.iloc[i]["Finding"],
                "Critical Score": escalation,
                "Category": category,
                "Hidden Meaning": hidden_flag,
                "Hidden Reason": hidden,
                "Leakage Area": leak_flag,
                "Leakage Reason": leakage,
                "Audit Status": audit_status,
                "Checklist Status": checklist_status,
                "Business Reason": business_reason,
                "Remediation": remediation,
                "Audit Schedule": schedule
            })
            
        self.df_results = pd.DataFrame(results)

    def perform_deep_analysis(self):
        # Optional: Clustering for "Leakage Area detection"
        try:
            from analysis import DeepAnalyzer
            analyzer = DeepAnalyzer(self.model)
            self.df_findings, self.clusters = analyzer.analyze_clusters(self.finding_embeddings, self.df_findings)
            return self.clusters
        except:
            return []

    def get_stats(self):
        if self.df_results is None: return {}
        
        process_summary = (
            self.df_results.groupby("Process")
            .agg(Total_Findings=("Process","count"), Avg_Risk=("Critical Score","mean"))
            .sort_values("Avg_Risk", ascending=False).head(10).reset_index().to_dict(orient="records")
        )
        risk_counts = self.df_results["Category"].value_counts().to_dict()
        deep = getattr(self, 'clusters', [])
        
        return {
            "total_findings": len(self.df_results),
            "risk_counts": risk_counts,
            "top_processes": process_summary,
            "recent_findings": self.df_results.head(50).to_dict(orient="records"),
            "deep_analysis": deep
        }

    def export_excel(self):
        if self.df_results is None: return None
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            self.df_results.to_excel(writer, sheet_name="Full_Data", index=False)
        output.seek(0)
        return output

    def chat_query(self, query):
        if self.df_results is None: return "Please upload data first."
        query_emb = self.model.encode([query], normalize_embeddings=True)
        sim = cosine_similarity(query_emb, self.finding_embeddings)[0]
        top_idx = sim.argsort()[-5:][::-1]
        
        response = f"**Consultative Advice for:** '{query}'\n\n"
        for idx in top_idx:
            if sim[idx] < 0.25: continue
            row = self.df_results.iloc[idx]
            response += f"> **{row['Category']} Risk**: {row['Finding']}\n"
            response += f"  *Remediation*: {row['Remediation']}\n"
            response += f"  *Schedule*: {row['Audit Schedule']}\n\n"
        return response
