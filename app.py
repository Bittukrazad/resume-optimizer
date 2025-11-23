# Pre-download model during build
import os
from sentence_transformers import SentenceTransformer

if not os.path.exists("./model_cache"):
    os.makedirs("./model_cache", exist_ok=True)
    print("📥 Pre-downloading model...")
    model = SentenceTransformer(
        "sentence-transformers/all-MiniLM-L6-v2",
        cache_folder="./model_cache"
    )
    print("✅ Model cached!")

import streamlit as st
import time
import io
from datetime import datetime
from utils import extract_text_from_pdf, extract_text_from_docx
from resume_analyzer import analyze_resume
from report_generator import generate_pdf_report
import os
import razorpay

# 🔐 Load credentials securely
try:
    ADMIN_PASSWORD = st.secrets["admin"]["password"]
    RAZORPAY_KEY = st.secrets["razorpay"]["key_id"]
    RAZORPAY_SECRET = st.secrets["razorpay"]["key_secret"]
except:
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "test123")
    RAZORPAY_KEY = os.getenv("RAZORPAY_KEY_ID", "rzp_test_00000000000000")
    RAZORPAY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "")

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
    .payment-instruction { 
        background: #fef3c7; 
        border: 2px solid #f59e0b; 
        border-radius: 12px; 
        padding: 20px; 
        margin: 20px 0;
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
if "awaiting_payment" not in st.session_state:
    st.session_state.awaiting_payment = False

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
        # Show processing message
        with st.spinner(f"📄 Processing {resume_file.name}..."):
            if resume_file.name.endswith(".pdf"):
                resume_text = extract_text_from_pdf(resume_file)
            elif resume_file.name.endswith(".docx"):
                resume_text = extract_text_from_docx(resume_file)
            else:
                st.error("❌ Unsupported file type. Please upload PDF or DOCX.")
                st.stop()
        
        # Debug: Show raw extraction first
        if resume_text and len(resume_text.strip()) > 10:
            word_count = len(resume_text.split())
            st.success(f"✅ Text extracted! ({word_count} words, {len(resume_text)} characters)")
            
            # Always show preview for transparency
            with st.expander("👁️ Preview Extracted Text (First 1000 chars)"):
                st.text_area("Extracted content:", resume_text[:1000], height=200, disabled=True)
                st.caption(f"Total length: {len(resume_text)} characters")
        else:
            st.error("⚠️ No text could be extracted from the file!")
            st.info("**Possible reasons:**\n"
                   "• File is a scanned image (not text-based PDF)\n"
                   "• File is corrupted or password-protected\n"
                   "• File format is not supported\n\n"
                   "**Try this:** Use an online converter to convert to text-based PDF")
            st.stop()
        
        # Validate extracted content (optional - can be disabled)
        from utils import validate_resume_content
        is_valid, error_msg = validate_resume_content(resume_text)
        
        if not is_valid:
            st.warning(f"⚠️ Validation Warning: {error_msg}")
            
            # Show what was found
            st.info("**Debug Info:**\n"
                   f"• Text length: {len(resume_text)} characters\n"
                   f"• Word count: {len(resume_text.split())} words\n"
                   f"• First 200 chars: `{resume_text[:200]}`")
            
            # Give option to continue anyway
            if st.button("⚡ Continue Anyway (Skip Validation)", type="secondary"):
                st.session_state.skip_validation = True
                st.rerun()
            
            if not st.session_state.get('skip_validation', False):
                st.stop()
            
    except ValueError as ve:
        # Specific error from extraction functions
        st.error(f"⚠️ {str(ve)}")
        st.info("💡 **Troubleshooting:**\n"
               "• Try saving your resume as a new file\n"
               "• Use 'Save As PDF' from Word/Google Docs\n"
               "• Ensure text is selectable (not scanned image)\n"
               "• Try the other format (PDF → DOCX or vice versa)")
    except Exception as e:
        # Unexpected errors
        st.error(f"❌ Unexpected error: {str(e)}")
        st.warning("🔧 **Please try:**\n"
                  "1. Re-uploading the file\n"
                  "2. Converting to the other format\n"
                  "3. Creating a new resume from a template\n"
                  "4. Contact support if issue persists")
        
        # Log for debugging
        import logging
        logging.error(f"Resume parsing error: {e}", exc_info=True)

# ✅ Analyze Button
if st.button("🔍 Analyze Resume (Free Preview)", type="primary", use_container_width=True) and resume_text and job_desc:
    with st.spinner("Analyzing... (takes ~5 sec)"):
        result = analyze_resume(resume_text, job_desc)
    
    # Store ALL necessary data in session state
    st.session_state.last_result = result
    st.session_state.resume_text = resume_text
    st.session_state.job_desc = job_desc
    st.session_state.analysis_timestamp = datetime.now().isoformat()
    
    score_color = "score-good" if result['ats_score'] >= 70 else "score-bad"
    st.markdown(f"<div class='score-display {score_color}'>{result['ats_score']}/100</div>", unsafe_allow_html=True)
    st.progress(result['ats_score'] / 100)
    st.info(f"🎯 Detected Role: **{result['detected_role']}**")
    st.info("💡 *Free preview shows score only. Unlock full report with ₹5!*")
    st.session_state.reports_generated += 1

# 💰 Razorpay Payment Section
if "last_result" in st.session_state and not st.session_state.payment_confirmed:
    st.markdown("---")
    st.subheader("✨ Unlock Full Report (Only ₹5!)")
    st.caption("☕ Less than a cup of chai — get actionable ATS feedback!")
    
    # Create an eye-catching card for benefits
    st.markdown("""
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                padding: 20px; border-radius: 12px; color: white; margin: 15px 0;">
        <h3 style="margin: 0 0 15px 0; color: white;">✅ You'll get:</h3>
        <ul style="margin: 0; padding-left: 20px;">
            <li style="margin: 8px 0;">🔍 <strong>Section-wise ATS scores</strong></li>
            <li style="margin: 8px 0;">🎯 <strong>Role-specific keyword gaps</strong></li>
            <li style="margin: 8px 0;">✨ <strong>AI rewrite suggestions</strong></li>
            <li style="margin: 8px 0;">📥 <strong>PDF report + ATS template</strong></li>
        </ul>
    </div>
    """, unsafe_allow_html=True)
    
    # Payment Button
    if st.button("💳 PAY ₹5 NOW", type="primary", use_container_width=True, key="payment_btn"):
        st.session_state.awaiting_payment = True
        st.rerun()
    
    # Enhanced Instructions when payment is initiated
    if st.session_state.awaiting_payment:
        st.markdown("""
        <div class='payment-instruction'>
            <h3 style="color: #92400e; margin-top: 0;">📌 Payment Instructions:</h3>
            <ol style="color: #78350f; font-size: 16px; line-height: 1.8;">
                <li><strong>Click the payment link below</strong> to complete ₹5 payment via Razorpay</li>
                <li><strong>After successful payment</strong>, you'll receive an <strong>email from Razorpay</strong></li>
                <li><strong>Copy the Payment ID</strong> from that email (format: <code>pay_xxxxxxxxxxxxx</code>)</li>
                <li><strong>Come back here</strong> and paste it in the box below to unlock your report</li>
            </ol>
        </div>
        """, unsafe_allow_html=True)
        
        # Payment Link
        st.markdown("""
        <a href="https://rzp.io/rzp/v6xOQu0" target="_blank" style="
            display: block;
            background: linear-gradient(135deg, #f59e0b 0%, #ef4444 100%);
            color: white;
            padding: 18px 32px;
            border-radius: 12px;
            font-weight: bold;
            width: 100%;
            font-size: 20px;
            box-shadow: 0 8px 20px rgba(239, 68, 68, 0.4);
            text-align: center;
            text-decoration: none;
            margin: 20px 0;
        ">🔗 OPEN RAZORPAY PAYMENT PAGE</a>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        st.subheader("🔓 Unlock Your Report")
        st.info("✅ Payment completed? Paste your Payment ID below:")
        
        # Payment ID Input
        payment_id_input = st.text_input(
            "📧 Payment ID (from email)",
            placeholder="pay_xxxxxxxxxxxxx",
            help="Check your email for the Payment ID after completing payment"
        )
        
        col1, col2 = st.columns([3, 1])
        with col1:
            verify_btn = st.button("🔍 Verify Payment & Unlock Report", type="primary", use_container_width=True)
        with col2:
            if st.button("❌ Cancel", use_container_width=True):
                st.session_state.awaiting_payment = False
                st.rerun()
        
        # Verify Payment
        if verify_btn and payment_id_input:
            if not payment_id_input.startswith("pay_"):
                st.error("❌ Invalid Payment ID format. It should start with 'pay_'")
            else:
                with st.spinner("🔄 Verifying your payment..."):
                    try:
                        client = razorpay.Client(auth=(RAZORPAY_KEY, RAZORPAY_SECRET))
                        payment = client.payment.fetch(payment_id_input)
                        
                        # Check payment status and amount
                        if payment["status"] == "captured" and payment["amount"] >= 500:
                            st.session_state.payment_confirmed = True
                            st.session_state.paid_users += 1
                            st.session_state.payment_id = payment_id_input
                            st.session_state.awaiting_payment = False
                            
                            st.balloons()
                            st.success("🎉 Payment verified successfully! Unlocking your full report...")
                            time.sleep(2)
                            st.rerun()
                        else:
                            st.error(f"❌ Payment {payment['status']}. Amount: ₹{payment['amount']/100}")
                            st.warning("Please ensure payment is completed successfully.")
                            
                    except razorpay.errors.BadRequestError:
                        st.error("❌ Invalid Payment ID. Please check and try again.")
                    except Exception as e:
                        st.error(f"⚠️ Verification failed: {str(e)}")
                        st.info("💡 If payment was successful, please contact support with your Payment ID.")

# 🎉 Post-payment: Full Report
if st.session_state.payment_confirmed:
    # Check if we have the required data
    if "last_result" not in st.session_state:
        st.error("⚠️ Report data not found. This may happen if:")
        st.info("1. You cleared your browser cache\n2. The session expired\n3. You opened the link in a new browser")
        st.info("👉 **Solution**: Please upload your resume again and re-analyze to generate a new report.")
        
        # Reset payment confirmation
        if st.button("🔄 Start Over"):
            st.session_state.payment_confirmed = False
            st.session_state.awaiting_payment = False
            st.rerun()
        st.stop()
    
    st.markdown('<div id="full-report"></div>', unsafe_allow_html=True)
    st.balloons()
    st.success(f"🎉 Payment confirmed! (Payment ID: {st.session_state.get('payment_id', 'N/A')})")
    st.success("Here's your full report:")
    
    result = st.session_state.last_result
    
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
        st.subheader("🔍 Keyword Gap Analysis")
        
        missing = result.get("missing_keywords", [])
        extra = result.get("extra_keywords", [])
        
        if missing:
            st.write("Add these to boost your score:")
            keywords_html = "".join([
                f"<span class='keyword-tag missing-tag'>{kw}</span>" 
                for kw in missing[:8]
            ])
            st.markdown(keywords_html, unsafe_allow_html=True)
        else:
            st.info("✅ Perfect alignment! No missing keywords found.")
        
        if extra:
            st.write("Good extras (keep these!):")
            extras_html = "".join([
                f"<span class='keyword-tag'>{kw}</span>" 
                for kw in extra[:5]
            ])
            st.markdown(extras_html, unsafe_allow_html=True)
        
    with tab3:
        st.subheader("✨ AI Rewrite Suggestion")
        
        result = st.session_state.last_result
        job_desc = st.session_state.job_desc
        
        bullets = result.get("weak_bullets", [])
        tech = result.get("tech_stack", ["Python"])
        metric = result.get("metric", "measurable impact")
        
        if bullets:
            before = bullets[0]
            action = "Developed" if "ml" in job_desc.lower() else "Built"
            tech_str = ", ".join(tech[:2]) if len(tech) > 1 else tech[0]
            after = f"{action} a {result['detected_role']} solution using {tech_str}, achieving {metric}."
        else:
            before = "Built a project."
            after = f"Designed and implemented a {result['detected_role']}-aligned solution with quantifiable results."
        
        st.text_area("Before (Weak)", before, height=70, disabled=True)
        st.text_area("After (ATS-Optimized)", after, height=70, disabled=True)
        
        if st.button("📋 Copy Optimized Version", key="copy_btn_rewrite"):
            st.components.v1.html(f'<script>navigator.clipboard.writeText("{after}");</script>', height=0)
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
Missing Keywords: {', '.join(result.get('missing_keywords', [])[:8])}

Suggestions:
""" + "\n".join([f"- {s}" for s in result.get('suggestions', [])])
        
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
            for key in ["reports_generated", "paid_users", "payment_confirmed", "last_result", "awaiting_payment"]:
                st.session_state.pop(key, None)
            st.sidebar.success("✅ Stats reset!")
            
# SIDEBAR for debugging
st.sidebar.markdown("---")
if st.sidebar.checkbox("🔧 Debug Mode"):
    st.sidebar.markdown("### 🔍 Diagnostic Info")
    
    if resume_file and resume_text:
        st.sidebar.success("✅ File uploaded & processed")
        
        # File info
        st.sidebar.metric("File Size", f"{resume_file.size / 1024:.1f} KB")
        st.sidebar.metric("File Type", resume_file.name.split('.')[-1].upper())
        
        # Extraction info
        st.sidebar.metric("Characters Extracted", len(resume_text))
        st.sidebar.metric("Word Count", len(resume_text.split()))
        st.sidebar.metric("Line Count", len(resume_text.split('\n')))
        
        # Show sections detected
        from utils import parse_resume_sections
        sections = parse_resume_sections(resume_text)
        
        st.sidebar.markdown("**📂 Sections Detected:**")
        for sec, content in sections.items():
            if content.strip():
                word_count = len(content.split())
                st.sidebar.text(f"• {sec.title()}: {word_count} words")
            else:
                st.sidebar.text(f"• {sec.title()}: ❌ Not found")
        
        # Quick keyword check
        tech_found = []
        for keyword in ['python', 'java', 'javascript', 'react', 'sql', 'machine learning', 'ai']:
            if keyword in resume_text.lower():
                tech_found.append(keyword)
        
        if tech_found:
            st.sidebar.markdown(f"**🔑 Tech Keywords Found:** {', '.join(tech_found[:5])}")
        else:
            st.sidebar.warning("⚠️ No common tech keywords found")
            
    elif resume_file:
        st.sidebar.warning("⚠️ File uploaded but no text extracted")
        st.sidebar.info(f"File: {resume_file.name}\nSize: {resume_file.size} bytes")
    else:
        st.sidebar.info("📁 No file uploaded yet")
    
    # Test button
    st.sidebar.markdown("---")
    if st.sidebar.button("🧪 Test Extraction", help="Re-extract text from uploaded file"):
        if resume_file:
            try:
                file.seek(0)
                if resume_file.name.endswith(".pdf"):
                    test_text = extract_text_from_pdf(resume_file)
                else:
                    test_text = extract_text_from_docx(resume_file)
                
                st.sidebar.success(f"✅ Extracted {len(test_text)} chars")
                st.sidebar.text_area("Raw text:", test_text[:500], height=150)
            except Exception as e:
                st.sidebar.error(f"❌ {str(e)}")
                
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

# 📝 Footer
st.markdown("---")
st.caption("© 2025 ResumeBoost AI • Made by an AIML student, for students ❤️")
st.caption("🔒 Payments powered by Razorpay • No resume data stored")



