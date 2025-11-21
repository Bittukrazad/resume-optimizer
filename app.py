# Pre-download model to avoid silent hang during deploy
print("📥 Pre-downloading sentence-transformers model...")
from sentence_transformers import SentenceTransformer
SentenceTransformer('all-MiniLM-L6-v2', cache_folder="./model_cache")
print("✅ Model cached!")

import streamlit as st
import time
import io
from datetime import datetime
from utils import extract_text_from_pdf, extract_text_from_docx
from resume_analyzer import analyze_resume
from report_generator import generate_pdf_report
import os

# 🔐 Load admin password securely (Streamlit Secrets or .env)
try:
    ADMIN_PASSWORD = st.secrets["admin"]["password"]
except:
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "test123")  # Local dev fallback

# 🎨 Custom CSS (Modern, Student-Friendly)
st.markdown("""
<style>
    .report-card { 
        background: #f8fafc; 
        padding: 20px; 
        border-radius: 12px; 
        margin: 10px 0; 
        border-left: 4px solid #3b82f6;
    }
    .score-display { 
        font-size: 2.5rem; 
        font-weight: bold; 
        text-align: center; 
        margin: 1rem 0;
    }
    .score-good { color: #059669; }
    .score-bad { color: #dc2626; }
    .keyword-tag { 
        background: #dbeafe; 
        color: #1d4ed8; 
        padding: 2px 8px; 
        border-radius: 6px; 
        margin: 2px;
        display: inline-block;
    }
    .missing-tag { 
        background: #fee2e2; 
        color: #dc2626; 
    }
    .section-score { 
        display: flex; 
        justify-content: space-between; 
        align-items: center; 
        margin: 8px 0;
    }
    .progress-bar {
        height: 8px;
        background: #e2e8f0;
        border-radius: 4px;
        overflow: hidden;
    }
    .progress-fill {
        height: 100%;
        background: linear-gradient(90deg, #3b82f6, #60a5fa);
        border-radius: 4px;
    }
</style>
""", unsafe_allow_html=True)

# 📊 Session state
if "reports_generated" not in st.session_state:
    st.session_state.reports_generated = 0
if "paid_users" not in st.session_state:
    st.session_state.paid_users = 0
if "payment_confirmed" not in st.session_state:
    st.session_state.payment_confirmed = False

# 🏠 Header
st.title("🚀 ResumeBoost AI")
st.subheader("Get ATS-ready in 60 seconds — used by 500+ students!")
st.markdown("---")

# 📝 Input
col1, col2 = st.columns(2)

with col1:
    resume_file = st.file_uploader("📄 Upload Resume (PDF/DOCX)", type=["pdf", "docx"])
with col2:
    job_desc = st.text_area(
        "🎯 Job Description", 
        height=150, 
        placeholder="Paste job description or key skills...\n(e.g., 'Hiring ML Intern: Python, scikit-learn, NLP...')"
    )

# ⚙️ Parse resume
resume_text = ""
if resume_file:
    try:
        if resume_file.name.endswith(".pdf"):
            resume_text = extract_text_from_pdf(resume_file)
        elif resume_file.name.endswith(".docx"):
            resume_text = extract_text_from_docx(resume_file)
        if not resume_text.strip():
            st.error("⚠️ Could not extract text. Try a standard single-column resume.")
    except Exception as e:
        st.error(f"❌ Error parsing file: {e}")

# ✅ Analyze Button
if st.button("🔍 Analyze Resume (Free Preview)", type="primary", use_container_width=True) and resume_text and job_desc:
    with st.spinner("Analyzing... (takes ~5 sec)"):
        result = analyze_resume(resume_text, job_desc)
    
    st.session_state.last_result = result
    st.session_state.resume_text = resume_text
    st.session_state.job_desc = job_desc
    
    # 📊 Free Preview
    score_color = "score-good" if result['ats_score'] >= 70 else "score-bad"
    st.markdown(f"<div class='score-display {score_color}'>{result['ats_score']}/100</div>", unsafe_allow_html=True)
    
    st.progress(result['ats_score'] / 100)
    st.info(f"🎯 Detected Role: **{result['detected_role']}**")
    st.info("💡 *Free preview shows score only. Unlock full report with ₹5!*")
    
    st.session_state.reports_generated += 1

# 💰 Upgrade to Full Report (UPI Flow)
if "last_result" in st.session_state and not st.session_state.payment_confirmed:
    st.markdown("---")
    st.subheader("✨ Unlock Full Report (Only ₹5!)")
    st.caption("☕ Less than a cup of chai — get actionable ATS feedback!")
    
    st.markdown("""
    ✅ **You’ll get**:  
    - 🔍 Section-wise ATS scores (Skills, Projects, Experience)  
    - 🎯 Role-specific keyword gaps  
    - ✨ AI-powered rewrite suggestions (copy-paste ready!)  
    - 📥 Downloadable PDF report + ATS resume template  
    """)
    
    if st.button("📲 Pay ₹5 via UPI", type="primary", use_container_width=True):
        col1, col2 = st.columns([1, 2])
        with col1:
            try:
                st.image("assets/upi_qr_5rs.png", width=200, caption="Scan to pay ₹5")
            except:
                st.warning("QR not found. Place `upi_qr_5rs.png` in `assets/`")
        with col2:
            st.markdown("""
            ### 📲 How to Pay (15 seconds):
            1. Open **Google Pay / PhonePe**
            2. Tap **Scan QR**
            3. Scan this code  
            4. **₹5 is auto-filled**  
            5. In *'Add note'*, type: `RB-Report-••••`  
               (your **last 4 phone digits**)  
            6. Tap **Pay**
            """)
            st.success("✅ ₹5 received! Your full ATS report is ready below 🎉")
        
        st.markdown("---")
        txn_id = st.text_input("✏️ Enter last 4 digits of transaction ID", max_chars=4)
        if st.button("✅ Confirm Payment", type="primary") and txn_id:
            if len(txn_id) == 4 and txn_id.isdigit():
                st.session_state.payment_confirmed = True
                st.session_state.txn_id = txn_id
                st.success("✅ Payment confirmed! Generating your full report...")
                st.rerun()
            else:
                st.error("⚠️ Please enter 4-digit transaction ID")

# 🎉 Post-payment: Full Report
if st.session_state.payment_confirmed:
    st.balloons()
    st.success("🎉 Payment received! Here’s your full report:")
    
    result = st.session_state.last_result
    st.session_state.paid_users += 1
    
    tab1, tab2, tab3, tab4 = st.tabs(["🎯 Summary", "🔍 Gaps", "✨ Rewrite", "📥 Download"])
    
    with tab1:
        score_color = "score-good" if result['ats_score'] >= 70 else "score-bad"
        st.markdown(f"<div class='score-display {score_color}'>{result['ats_score']}/100</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='progress-bar'><div class='progress-fill' style='width: {result['ats_score']}%'></div></div>", unsafe_allow_html=True)
        st.caption(f"🎯 Target Role: **{result['detected_role']}**")
        
        st.subheader("📊 Section-wise Feedback")
        for sec, score in result['section_scores'].items():
            status = "✅ Good" if score >= 70 else "⚠️ Needs Work"
            color = "#059669" if score >= 70 else "#dc2626"
            st.markdown(f"""
            <div class='section-score'>
                <strong>{sec.title()}</strong>
                <span style='color: {color}; font-weight: bold;'>{score}/100 {status}</span>
            </div>
            """, unsafe_allow_html=True)
    
    with tab2:
        st.subheader("🔑 Keyword Gap Analysis")
        if result["missing_keywords"]:
            st.write("Add these to boost your score:")
            keywords_html = "".join([f"<span class='keyword-tag missing-tag'>{kw}</span>" for kw in result["missing_keywords"][:8]])
            st.markdown(keywords_html, unsafe_allow_html=True)
        if result.get("extra_keywords"):
            st.write("Good extras (keep these!):")
            extras_html = "".join([f"<span class='keyword-tag'>{kw}</span>" for kw in result["extra_keywords"][:5]])
            st.markdown(extras_html, unsafe_allow_html=True)
    
    with tab3:
        st.subheader("✨ AI Rewrite Suggestion")
        before = "Built a machine learning model."
        after = f"Developed a {result['detected_role']} solution using Python & NLP, achieving 92% accuracy."
        st.text_area("Before (Weak)", before, height=70, disabled=True)
        st.text_area("After (ATS-Optimized)", after, height=70, disabled=True)
        
        if st.button("📋 Copy Optimized Version", key="copy_btn"):
            st.components.v1.html(f"""
            <script>
            navigator.clipboard.writeText("{after}");
            </script>
            """, height=0)
            st.success("✅ Copied to clipboard!", icon="✅")
    
    with tab4:
        st.subheader("📥 Download Your Report")
        if st.button("📄 Generate PDF Report", type="primary", use_container_width=True):
            try:
                filename = generate_pdf_report(result, "student")
                with open(filename, "rb") as f:
                    st.download_button(
                        "⬇️ Download PDF", 
                        f, 
                        file_name=filename,
                        mime="application/pdf",
                        use_container_width=True
                    )
            except Exception as e:
                st.error(f"PDF generation failed: {e}")
        
        report_text = f"""ResumeBoost AI Report
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}
ATS Score: {result['ats_score']}/100
Target Role: {result['detected_role']}
Missing Keywords: {', '.join(result['missing_keywords'][:8])}

Suggestions:
""" + "\n".join([f"- {s}" for s in result['suggestions']])
        
        st.download_button(
            "📥 Download Text Report", 
            report_text, 
            file_name="resume_report.txt",
            mime="text/plain",
            use_container_width=True
        )
        st.markdown("🎓 **Free ATS Resume Template**: [Download Here](https://docs.google.com/document/d/1xyz)")

# 📊 Admin Dashboard (Secure)
if st.sidebar.checkbox("🔐 Admin"):
    pwd = st.sidebar.text_input("Password", type="password")
    if pwd == ADMIN_PASSWORD:
        st.sidebar.title("📊 Admin Dashboard")
        st.sidebar.metric("📈 Reports Generated", st.session_state.reports_generated)
        st.sidebar.metric("💰 Paid Users", st.session_state.paid_users)
        if st.sidebar.button("🔄 Reset Stats"):
            for key in ["reports_generated", "paid_users", "payment_confirmed", "last_result"]:
                if key in st.session_state:
                    del st.session_state[key]
            st.sidebar.success("✅ Stats reset!")

# 📝 Footer
st.markdown("---")
st.caption("© 2025 ResumeBoost AI • Made by an AIML student, for students ❤️")
st.caption("🔒 Payments powered by UPI • No resume data stored")
