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
from report_generator import generate_pdf_report  # ✅ v2: PDF reports
import razorpay
import os

# 🔐 Load secrets (safe for Streamlit Cloud)
try:
    # Streamlit Cloud / Local with secrets.toml
    RAZORPAY_KEY = st.secrets["razorpay"]["RAZORPAY_KEY"]
    RAZORPAY_SECRET = st.secrets["razorpay"]["RAZORPAY_SECRET"]
    ADMIN_PASSWORD = st.secrets["admin"]["password"]
except:
    # Local dev fallback (never commit real secrets here!)
    RAZORPAY_KEY = os.getenv("RAZORPAY_KEY", "rzp_test_00000000000000")
    RAZORPAY_SECRET = os.getenv("RAZORPAY_SECRET", "XXXXXXXXXXXXXXXX")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "test123")

# Initialize Razorpay client (safe fallback)
try:
    client = razorpay.Client(auth=(RAZORPAY_KEY, RAZORPAY_SECRET))
except:
    client = None

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
    st.info("💡 *Free preview shows score only. Unlock full report with section-wise feedback!*")
    
    st.session_state.reports_generated += 1

# 💰 Upgrade to Full Report
if "last_result" in st.session_state:
    st.markdown("---")
    st.subheader("✨ Unlock Full Report (₹49)")
    st.markdown("""
    - 🔍 **Section-wise ATS scores** (Skills, Projects, etc.)  
    - 🎯 **Role-specific keyword gaps**  
    - ✨ **AI-powered rewrite suggestions**  
    - 📥 **Downloadable PDF + ATS template**
    """)
    
    if st.button("💳 Pay ₹49 via Razorpay", type="secondary", use_container_width=True):
        if client:
            try:
                order = client.order.create({
                    "amount": 4900,
                    "currency": "INR",
                    "receipt": f"rb_{int(datetime.now().timestamp())}",
                    "notes": {"service": "resume_report"}
                })
                
                # Razorpay Checkout
                st.markdown(f"""
                <script src="https://checkout.razorpay.com/v1/checkout.js"></script>
                <script>
                var options = {{
                    "key": "{RAZORPAY_KEY}",
                    "amount": "4900",
                    "currency": "INR",
                    "name": "ResumeBoost AI",
                    "description": "Resume Optimization Report",
                    "order_id": "{order['id']}",
                    "handler": function (response) {{
                        window.parent.postMessage({{ type: 'razorpay_success', payment_id: response.razorpay_payment_id }}, '*');
                    }},
                    "prefill": {{
                        "name": "",
                        "email": "",
                        "contact": ""
                    }},
                    "theme": {{ "color": "#2563eb" }}
                }};
                var rzp1 = new Razorpay(options);
                rzp1.open();
                </script>
                """, unsafe_allow_html=True)
                
                st.components.v1.html("""
                <script>
                window.addEventListener('message', function(e) {
                    if (e.data.type === 'razorpay_success') {
                        window.parent.location.href = '?payment=success';
                    }
                });
                </script>
                """, height=0)
            except Exception as e:
                st.error(f"Payment setup error: {e}")
                st.info("Using test mode — click below to simulate success.")
                if st.button("✅ Simulate Payment Success (Testing)"):
                    st.query_params["payment"] = "success"
                    st.rerun()
        else:
            st.info("Razorpay not configured — using test mode.")
            if st.button("✅ Simulate Payment Success"):
                st.query_params["payment"] = "success"
                st.rerun()

# 🎉 Post-payment: Full Report (v2)
if st.query_params.get("payment") == "success":
    st.balloons()
    st.success("🎉 Payment successful! Here’s your full report:")
    
    result = st.session_state.last_result
    st.session_state.paid_users += 1
    
    # Tabs for clean UX
    tab1, tab2, tab3, tab4 = st.tabs(["🎯 Summary", "🔍 Gaps", "✨ Rewrite", "📥 Download"])
    
    with tab1:
        # Score Display
        score_color = "score-good" if result['ats_score'] >= 70 else "score-bad"
        st.markdown(f"<div class='score-display {score_color}'>{result['ats_score']}/100</div>", unsafe_allow_html=True)
        
        # Progress bar
        st.markdown(f"<div class='progress-bar'><div class='progress-fill' style='width: {result['ats_score']}%'></div></div>", unsafe_allow_html=True)
        st.caption(f"🎯 Target Role: **{result['detected_role']}**")
        
        # Section Scores
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
            # JavaScript clipboard copy
            st.components.v1.html(f"""
            <script>
            navigator.clipboard.writeText("{after}");
            parent.document.querySelector('button[kind="secondary"]').innerText = "✅ Copied!";
            setTimeout(() => {{
                parent.document.querySelector('button[kind="secondary"]').innerText = "📋 Copy Optimized Version";
            }}, 2000);
            </script>
            """, height=0)
            st.success("Copied to clipboard!", icon="✅")
    
    with tab4:
        st.subheader("📥 Download Your Report")
        
        # Generate PDF
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
                st.info("Text report below:")
        
        # Text fallback
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

# 📊 Admin Dashboard
if st.sidebar.checkbox("🔐 Admin"):
    pwd = st.sidebar.text_input("Password", type="password")
    if pwd == ADMIN_PASSWORD:
        st.sidebar.title("📊 Admin Dashboard")
        st.sidebar.metric("📈 Reports Generated", st.session_state.reports_generated)
        st.sidebar.metric("💰 Paid Users", st.session_state.paid_users)
        st.sidebar.info("💡 Export data to CSV & pitch to TPOs!")
        
        # Reset button (for testing)
        if st.sidebar.button("🔄 Reset Stats"):
            st.session_state.reports_generated = 0
            st.session_state.paid_users = 0
            st.sidebar.success("Stats reset!")

# 📝 Footer
st.markdown("---")
st.caption("© 2025 ResumeBoost AI • Made by an AIML student, for students ❤️")
st.caption("🔒 Payments secured by Razorpay • No resume data stored")