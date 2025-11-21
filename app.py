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

# 🔐 Load admin password securely
try:
    ADMIN_PASSWORD = st.secrets["admin"]["password"]
except:
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "test123")

# 🎨 Custom CSS
st.markdown("""
<style>
    .report-card { background: #f8fafc; padding: 20px; border-radius: 12px; margin: 10px 0; border-left: 4px solid #3b82f6; }
    .score-display { font-size: 2.5rem; font-weight: bold; text-align: center; margin: 1rem 0; }
    .score-good { color: #059669; }
    .score-bad { color: #dc2626; }
    .keyword-tag { background: #dbeafe; color: #1d4ed8; padding: 2px 8px; border-radius: 6px; margin: 2px; display: inline-block; }
    .missing-tag { background: #fee2e2; color: #dc2626; }
    .section-score { display: flex; justify-content: space-between; align-items: center; margin: 8px 0; }
    .progress-bar { height: 8px; background: #e2e8f0; border-radius: 4px; overflow: hidden; }
    .progress-fill { height: 100%; background: linear-gradient(90deg, #3b82f6, #60a5fa); border-radius: 4px; }
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
        placeholder="Paste job description or key skills..."
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
            st.error("⚠️ Could not extract text. Try a standard resume.")
    except Exception as e:
        st.error(f"❌ Error parsing file: {e}")

# ✅ Analyze Button
if st.button("🔍 Analyze Resume (Free Preview)", type="primary", use_container_width=True) and resume_text and job_desc:
    with st.spinner("Analyzing... (takes ~5 sec)"):
        result = analyze_resume(resume_text, job_desc)
    
    st.session_state.last_result = result
    st.session_state.resume_text = resume_text
    st.session_state.job_desc = job_desc
    
    score_color = "score-good" if result['ats_score'] >= 70 else "score-bad"
    st.markdown(f"<div class='score-display {score_color}'>{result['ats_score']}/100</div>", unsafe_allow_html=True)
    st.progress(result['ats_score'] / 100)
    st.info(f"🎯 Detected Role: **{result['detected_role']}**")
    st.info("💡 *Free preview shows score only. Unlock full report with ₹5!*")
    st.session_state.reports_generated += 1
    
       # ---------------------------
# 💰 Razorpay Payment (Standard Checkout)
    if "last_result" in st.session_state and not st.session_state.payment_confirmed:
        st.markdown("---")
        st.subheader("✨ Unlock Full Report (Only ₹5!)")
        st.caption("☕ Less than a cup of chai — get actionable ATS feedback!")
        
        st.markdown("""
        ✅ **You’ll get**:  
        - 🔍 Section-wise ATS scores  
        - 🎯 Role-specific keyword gaps  
        - ✨ AI rewrite suggestions  
        - 📥 PDF report + ATS template  
        """)
        
       # ✅ Razorpay Standard Checkout (Pre-filled ₹5)
        st.markdown(f"""
        <a href="https://rzp.io/rzp/v6xOQu0?amount=500&currency=INR&notes[service]=resume_report"
           style="
             display: inline-block;
             background: #2563eb;
             color: white;
             padding: 12px 24px;
             border-radius: 8px;
             font-weight: bold;
             text-decoration: none;
             width: 100%;
             text-align: center;
           ">
           💳 Pay ₹5 via Razorpay
        </a>
        <script>
        // Auto-redirect after payment
        const urlParams = new URLSearchParams(window.location.search);
        const payment_id = urlParams.get('payment_id');
        if (payment_id) {{
            window.parent.location.href = window.parent.location.pathname + '?payment_id=' + payment_id;
        }}
        </script>
        """, unsafe_allow_html=True)
        
# 🎉 Post-payment: Full Report
if st.session_state.payment_confirmed:
    # 🔗 ANCHOR FOR SCROLL
    st.markdown('<div id="full-report"></div>', unsafe_allow_html=True)
    st.balloons()
    st.success("🎉 Payment confirmed! Here’s your full report:")
    
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
            <script>navigator.clipboard.writeText("{after}");</script>
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

# 📊 Admin Dashboard
if st.sidebar.checkbox("🔐 Admin"):
    pwd = st.sidebar.text_input("Password", type="password")
    if pwd == ADMIN_PASSWORD:
        st.sidebar.title("📊 Admin Dashboard")
        st.sidebar.metric("📈 Reports Generated", st.session_state.reports_generated)
        st.sidebar.metric("💰 Paid Users", st.session_state.paid_users)
        if st.sidebar.button("🔄 Reset Stats"):
            for key in ["reports_generated", "paid_users", "payment_confirmed", "last_result"]:
                st.session_state.pop(key, None)
            st.sidebar.success("✅ Stats reset!")
                       
 # ================== LEGAL PAGES ==================

st.sidebar.markdown("### 📘 Legal & Support")

page = st.sidebar.radio(
    "Navigate",
    [
        "Home",
        "Terms & Conditions",
        "Privacy Policy",
        "Refund & Cancellation Policy",
        "Contact Us"
    ]
)

if page == "Terms & Conditions":
    st.title("📘 Terms & Conditions")
    st.markdown("""
    # Terms & Conditions

Welcome to ResumeBoost AI.

By using our website and services, you agree to the following terms:

1. Our platform provides resume analysis, resume optimization, and AI-based improvement suggestions.
2. We DO NOT collect, store, or save any resumes or personal data. All uploaded files are processed temporarily in-memory and automatically deleted after analysis.
3. Users are responsible for ensuring the correctness of the documents they upload.
4. Payments made for AI-based analysis are final and non-transferable.
5. Any misuse, abusive activity, or fraudulent behavior may result in denial of service.
6. As services are digital and delivered instantly, cancellations or reversals are not applicable.
7. Disputes, if any, will be handled under Jaipur, Rajasthan jurisdiction.

If you disagree with these terms, you may discontinue using the service.

    """)

elif page == "Privacy Policy":
    st.title("🔒 Privacy Policy")
    st.markdown("""
    # Privacy Policy

ResumeBoost AI values your privacy and follows a strict "No Data Collection, No Data Storage" policy.

## Information We Collect
We DO NOT collect:
- Personal details
- Resume contents
- User profile data
- Contact data
- Uploaded documents

All files uploaded (such as resumes) are processed **temporarily in-memory only**.  
They are **never saved**, **never stored**, **never logged**, and **automatically deleted** after generating results.

## Payment Data
We do NOT store any payment information.

All payment-related data (UPI, card, bank details) is handled securely by **Razorpay**, in accordance with RBI guidelines.  
We never have access to your bank details.

## How We Use Your Data
Since we do not store data, usage is limited to:
- Temporary processing of resumes
- Generating AI-based optimization results

## Data Storage
We store **nothing**:
- No databases
- No resume storage
- No profiling
- No logs containing personal data

## Third-Party Services
We use Razorpay solely for secure payment processing.
Razorpay may collect the minimum required transaction information.

## User Rights
Since we do not store any personal data, there is nothing to retrieve, modify, or delete.

For general privacy queries, contact us anytime.


    """)

elif page == "Refund & Cancellation Policy":
    st.title("💳 Refund & Cancellation Policy")
    st.markdown("""
    # Refund & Cancellation Policy

Thank you for using ResumeBoost AI.

## Cancellation
Our service is digital and delivered instantly.  
Once a payment is completed, cancellations are not possible.

## Refunds
We follow a **No Refund Policy**, except in special cases:
1. Duplicate payment
2. Payment deducted but service not delivered due to technical error

To request a refund, please provide:
- Payment ID
- Transaction screenshot
- Email or phone number used during payment

Refunds take **5–7 working days** to process.

## Important Note
As we do NOT store resumes or personal data, we cannot retrieve previously processed files.

    """)

elif page == "Contact Us":
    st.title("📞 Contact Us")
    st.markdown("""
    For support, queries or payment issues, contact us:

    **📧 Email:** bittukrazad652@gmail.com  
    **📞 Phone:** +918233659229  
    **📍 Address:** Jaipur, Rajasthan, India  

    Response time: within 24–48 hours.
    """)

   # 🔐 Razorpay Payment Verification (Auto-unlock)
payment_id = st.query_params.get("payment_id")
if payment_id and not st.session_state.payment_confirmed:
    with st.spinner("✅ Verifying payment with Razorpay..."):
        try:
            # Initialize client (safe with test keys)
            RAZORPAY_KEY = "rzp_test_00000000000000"  # Public test key (safe to commit)
            RAZORPAY_SECRET = "XXXXXXXXXXXXXXXX"     # Dummy (not used in client-side verify)
            client = razorpay.Client(auth=(RAZORPAY_KEY, RAZORPAY_SECRET))
            
            # Verify payment
            payment = client.payment.fetch(payment_id)
            if payment["status"] == "captured" and payment["amount"] == 500:
                st.session_state.payment_confirmed = True
                st.session_state.paid_users += 1
                st.success("🎉 ₹5 payment verified! Generating your full report...")
                st.rerun()
            else:
                st.error(f"❌ Payment failed: {payment['status']}")
        except Exception as e:
            st.error(f"⚠️ Verification failed: {e}")
           

# 📝 Footer
st.markdown("---")
st.caption("© 2025 ResumeBoost AI • Made by an AIML student, for students ❤️")
st.caption("🔒 Payments powered by Razorpay • No resume data stored")
