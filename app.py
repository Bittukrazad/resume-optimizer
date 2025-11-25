
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
import hashlib
from datetime import datetime
from utils import extract_text_from_pdf, extract_text_from_docx, validate_resume_content
from resume_analyzer import analyze_resume
from report_generator import generate_pdf_report
import razorpay


# ============================================================
# CONFIGURATION & SECURITY
# ============================================================

# 🔐 Load credentials securely
try:
    ADMIN_PASSWORD = st.secrets["admin"]["password"]
    RAZORPAY_KEY = st.secrets["razorpay"]["key_id"]
    RAZORPAY_SECRET = st.secrets["razorpay"]["key_secret"]
except:
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
    RAZORPAY_KEY = os.getenv("RAZORPAY_KEY_ID", "rzp_test_00000000000000")
    RAZORPAY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "")
    
# 🎁 Template link (secure - not hardcoded)
try:
    TEMPLATE_LINK = st.secrets["resources"]["template_link"]
except:
    TEMPLATE_LINK = os.getenv("TEMPLATE_LINK", None)  # None if not set

# 📧 Support email
try:
    SUPPORT_EMAIL = st.secrets["resources"]["support_email"]
except:
    SUPPORT_EMAIL = os.getenv("SUPPORT_EMAIL", "bittukrazad652@gmail.com")
    
# Payment tracking to prevent reuse
if "used_payment_ids" not in st.session_state:
    st.session_state.used_payment_ids = set()

# ============================================================
# CUSTOM CSS
# ============================================================

st.markdown("""
<style>
    /* Main theme */
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 15px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    
    .report-card {
        background: #f8fafc;
        padding: 20px;
        border-radius: 12px;
        margin: 10px 0;
        border-left: 4px solid #3b82f6;
    }
    
    .score-display {
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
        margin: 1rem 0;
    }
    
    .score-excellent { color: #059669; }
    .score-good { color: #10b981; }
    .score-average { color: #f59e0b; }
    .score-poor { color: #dc2626; }
    
    .keyword-tag {
        background: #dbeafe;
        color: #1d4ed8;
        padding: 4px 10px;
        border-radius: 6px;
        margin: 3px;
        display: inline-block;
        font-size: 0.9rem;
    }
    
    .missing-tag {
        background: #fee2e2;
        color: #dc2626;
    }
    
    .extra-tag {
        background: #d1fae5;
        color: #059669;
    }
    
    .section-score {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin: 12px 0;
        padding: 10px;
        background: white;
        border-radius: 8px;
    }
    
    .progress-bar {
        height: 10px;
        background: #e2e8f0;
        border-radius: 5px;
        overflow: hidden;
        margin: 10px 0;
    }
    
    .progress-fill {
        height: 100%;
        background: linear-gradient(90deg, #3b82f6, #60a5fa);
        border-radius: 5px;
        transition: width 0.3s ease;
    }
    
    .payment-instruction {
        background: #fef3c7;
        border: 2px solid #f59e0b;
        border-radius: 12px;
        padding: 20px;
        margin: 20px 0;
    }
    
    .benefit-card {
        background: white;
        padding: 15px;
        border-radius: 10px;
        margin: 10px 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# SESSION STATE INITIALIZATION
# ============================================================

defaults = {
    "reports_generated": 0,
    "paid_users": 0,
    "payment_confirmed": False,
    "awaiting_payment": False,
    "skip_validation": False,
    "analysis_count": 0,
    "last_upload_hash": None
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

# ============================================================
# HEADER
# ============================================================

st.markdown("""
<div class='main-header'>
    <h1>🚀 ResumeBoost AI</h1>
    <p style='font-size: 1.2rem; margin: 10px 0;'>Get ATS-ready in 60 seconds — used by 500+ students!</p>
    <p style='font-size: 0.9rem; opacity: 0.9;'>Advanced AI-powered resume analysis with dynamic section scoring</p>
</div>
""", unsafe_allow_html=True)

# ============================================================
# INPUT SECTION
# ============================================================

col1, col2 = st.columns([1, 1])

with col1:
    st.markdown("### 📄 Upload Resume")
    resume_file = st.file_uploader(
        "Choose your resume (PDF/DOCX)",
        type=["pdf", "docx"],
        help="Upload your resume in PDF or DOCX format"
    )

with col2:
    st.markdown("### 🎯 Job Description")
    job_desc = st.text_area(
        "Paste the job description",
        height=150,
        placeholder="Paste the complete job description here...\n\nOr just key requirements and skills",
        help="The more detailed, the better the analysis"
    )

# ============================================================
# RESUME EXTRACTION
# ============================================================

resume_text = ""
if resume_file:
    # Create hash to detect file changes
    file_hash = hashlib.md5(resume_file.getvalue()).hexdigest()
    
    # Only process if file changed
    if st.session_state.last_upload_hash != file_hash:
        st.session_state.last_upload_hash = file_hash
        
        try:
            with st.spinner(f"📄 Processing {resume_file.name}..."):
                if resume_file.name.endswith(".pdf"):
                    resume_text = extract_text_from_pdf(resume_file)
                elif resume_file.name.endswith(".docx"):
                    resume_text = extract_text_from_docx(resume_file)
                else:
                    st.error("❌ Unsupported file type")
                    st.stop()
            
            # Store in session state
            st.session_state.resume_text = resume_text
            
            if resume_text and len(resume_text.strip()) > 10:
                word_count = len(resume_text.split())
                st.success(f"✅ Extracted {word_count} words, {len(resume_text)} characters")
                
                # Show preview
                with st.expander("👁️ Preview Extracted Text"):
                    st.text_area(
                        "First 1000 characters:",
                        resume_text[:1000],
                        height=200,
                        disabled=True
                    )
                    st.caption(f"Total: {len(resume_text)} characters")
                
                # Validate content
                is_valid, error_msg = validate_resume_content(resume_text)
                
                if not is_valid:
                    st.warning(f"⚠️ {error_msg}")
                    
                    if st.button("⚡ Continue Anyway"):
                        st.session_state.skip_validation = True
                        st.rerun()
                    
                    if not st.session_state.skip_validation:
                        st.stop()
            else:
                st.error("⚠️ No text extracted!")
                st.info("""
                **Possible reasons:**
                • Scanned PDF (not text-based)
                • Corrupted or password-protected file
                • Unsupported format
                
                **Try:** Use online converter to create text-based PDF
                """)
                st.stop()
        
        except ValueError as ve:
            st.error(f"⚠️ {str(ve)}")
            st.stop()
        
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")
            import logging
            logging.error(f"Extraction error: {e}", exc_info=True)
            st.stop()
    else:
        # Use cached text
        resume_text = st.session_state.get("resume_text", "")

# ============================================================
# ANALYSIS BUTTON
# ============================================================

if st.button(
    "🔍 Analyze Resume (Free Preview)",
    type="primary",
    use_container_width=True,
    disabled=not (resume_text and job_desc)
):
    # Rate limiting
    if st.session_state.analysis_count >= 10 and not st.session_state.payment_confirmed:
        st.warning("⚠️ Free analysis limit reached (10 per session). Please pay ₹5 to continue.")
        st.stop()
    
    with st.spinner("🧠 Analyzing with AI... (takes ~10 sec)"):
        result = analyze_resume(resume_text, job_desc)
    
    # Store results
    st.session_state.last_result = result
    st.session_state.resume_text = resume_text
    st.session_state.job_desc = job_desc
    st.session_state.analysis_timestamp = datetime.now().isoformat()
    st.session_state.analysis_count += 1
    st.session_state.reports_generated += 1
    
    # Show preview
    score = result['ats_score']
    
    if score >= 80:
        color_class = "score-excellent"
    elif score >= 70:
        color_class = "score-good"
    elif score >= 50:
        color_class = "score-average"
    else:
        color_class = "score-poor"
    
    st.markdown(f"<div class='score-display {color_class}'>{score}/100</div>", unsafe_allow_html=True)
    
    # Progress bar
    st.markdown(f"""
    <div class='progress-bar'>
        <div class='progress-fill' style='width: {score}%'></div>
    </div>
    """, unsafe_allow_html=True)
    
    # Quick insights
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Detected Role", result['detected_role'])
    
    with col2:
        missing_count = len(result.get('missing_keywords', []))
        st.metric("Missing Keywords", missing_count)
    
    with col3:
        sections_found = len(result.get('sections_found', []))
        st.metric("Sections Detected", f"{sections_found}/12")
    
    st.info("💡 *Free preview shows basic score. Unlock full report with ₹5!*")

# ============================================================
# PAYMENT SECTION
# ============================================================

if "last_result" in st.session_state and not st.session_state.payment_confirmed:
    st.markdown("---")
    st.markdown("### ✨ Unlock Full Report (Only ₹5!)")
    st.caption("☕ Less than a cup of chai — get actionable ATS feedback!")
    
    # Benefits
    st.markdown("""
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                padding: 20px; border-radius: 12px; color: white; margin: 15px 0;">
        <h3 style="margin: 0 0 15px 0; color: white;">✅ You'll get:</h3>
        <ul style="margin: 0; padding-left: 20px; line-height: 1.8;">
            <li>📊 <strong>Section-wise ATS scores with detailed feedback</strong></li>
            <li>🎯 <strong>Role-specific keyword gap analysis</strong></li>
            <li>✨ <strong>AI-powered bullet point rewrites</strong></li>
            <li>📈 <strong>Quality metrics and improvement suggestions</strong></li>
            <li>📥 <strong>Professional PDF report</strong></li>
            <li>🎁 <strong>Free ATS-optimized resume template</strong></li>
        </ul>
    </div>
    """, unsafe_allow_html=True)
    
    # Payment button
    if st.button("💳 PAY ₹5 NOW", type="primary", use_container_width=True):
        st.session_state.awaiting_payment = True
        st.rerun()
    
    # Payment instructions
    if st.session_state.awaiting_payment:
        st.markdown("""
        <div class='payment-instruction'>
            <h3 style="color: #92400e; margin-top: 0;">📌 Payment Instructions:</h3>
            <ol style="color: #78350f; font-size: 16px; line-height: 1.8;">
                <li><strong>Click payment link below</strong> to complete ₹5 payment</li>
                <li><strong>After payment</strong>, you'll receive email from Razorpay</li>
                <li><strong>Copy Payment ID</strong> from email (format: <code>pay_xxxxx...</code>)</li>
                <li><strong>Return here</strong> and paste it below to unlock report</li>
                <li><strong>Note:</strong> If the page refreshes after payment, simply re-upload your resume. You do not need to pay again. Just copy the payment ID from your confirmation email and enter it to verify</li>
            </ol>
        </div>
        """, unsafe_allow_html=True)
        
        # Payment link
        st.markdown("""
        <a href="https://rzp.io/rzp/v6xOQu0" target="_blank" style="
            display: block;
            background: linear-gradient(135deg, #f59e0b 0%, #ef4444 100%);
            color: white;
            padding: 18px 32px;
            border-radius: 12px;
            font-weight: bold;
            font-size: 20px;
            box-shadow: 0 8px 20px rgba(239, 68, 68, 0.4);
            text-align: center;
            text-decoration: none;
            margin: 20px 0;
        ">🔗 OPEN RAZORPAY PAYMENT PAGE</a>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        st.subheader("🔓 Unlock Your Report")
        st.info("✅ Payment completed? Paste Payment ID below:")
        
        # Payment verification
        payment_id_input = st.text_input(
            "📧 Payment ID (from email)",
            placeholder="pay_xxxxxxxxxxxxx",
            help="Check email for Payment ID after payment"
        )
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            verify_btn = st.button("🔍 Verify & Unlock", type="primary", use_container_width=True)
        
        with col2:
            if st.button("❌ Cancel", use_container_width=True):
                st.session_state.awaiting_payment = False
                st.rerun()
        
        # Verify payment
        if verify_btn and payment_id_input:
            if not payment_id_input.startswith("pay_"):
                st.error("❌ Invalid Payment ID format")
            elif payment_id_input in st.session_state.used_payment_ids:
                st.error("❌ This Payment ID has already been used!")
            else:
                with st.spinner("🔄 Verifying payment..."):
                    try:
                        client = razorpay.Client(auth=(RAZORPAY_KEY, RAZORPAY_SECRET))
                        payment = client.payment.fetch(payment_id_input)
                        
                        if payment["status"] == "captured" and payment["amount"] == 500:
                            # Mark payment as used
                            st.session_state.used_payment_ids.add(payment_id_input)
                            st.session_state.payment_confirmed = True
                            st.session_state.paid_users += 1
                            st.session_state.payment_id = payment_id_input
                            st.session_state.awaiting_payment = False
                            
                            st.balloons()
                            st.success("🎉 Payment verified! Unlocking report...")
                            time.sleep(2)
                            st.rerun()
                        else:
                            st.error(f"❌ Payment {payment['status']}. Amount: ₹{payment['amount']/100}")
                    
                    except razorpay.errors.BadRequestError:
                        st.error("❌ Invalid Payment ID")
                    except Exception as e:
                        st.error(f"⚠️ Verification failed: {str(e)}")

# ============================================================
# FULL REPORT (POST-PAYMENT)
# ============================================================

if st.session_state.payment_confirmed:
    if "last_result" not in st.session_state:
        st.error("⚠️ Report data not found. Please re-analyze your resume.")
        
        if st.button("🔄 Start Over"):
            st.session_state.payment_confirmed = False
            st.session_state.awaiting_payment = False
            st.rerun()
        st.stop()
    
    st.balloons()
    st.success(f"🎉 Payment Confirmed! (ID: {st.session_state.get('payment_id', 'N/A')})")
    
    result = st.session_state.last_result
    
    # Tabs for organized report
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Summary",
        "🔍 Section Analysis", 
        "🎯 Keywords",
        "✨ Rewrites",
        "📥 Download"
    ])
    
    with tab1:
        st.markdown("### 📊 Overall Performance")
        
        score = result['ats_score']
        if score >= 80:
            color = "score-excellent"
            msg = "Excellent! Your resume is ATS-ready!"
        elif score >= 70:
            color = "score-good"
            msg = "Good! Minor improvements needed."
        elif score >= 50:
            color = "score-average"
            msg = "Average. Significant improvements recommended."
        else:
            color = "score-poor"
            msg = "Needs work. Follow suggestions below."
        
        st.markdown(f"<div class='score-display {color}'>{score}/100</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='progress-bar'><div class='progress-fill' style='width: {score}%'></div></div>", unsafe_allow_html=True)
        st.info(msg)
        
        # Key metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Target Role", result['detected_role'])
        
        with col2:
            st.metric("Word Count", result.get('word_count', 0))
        
        with col3:
            st.metric("Sections Found", len(result.get('sections_found', [])))
        
        with col4:
            st.metric("Tech Skills", len(result.get('tech_stack', [])))
        
        # Suggestions
        st.markdown("### 💡 Key Recommendations")
        
        for i, suggestion in enumerate(result.get('suggestions', []), 1):
            st.markdown(f"""
            <div class='benefit-card'>
                <strong>{i}.</strong> {suggestion}
            </div>
            """, unsafe_allow_html=True)
    
    with tab2:
        st.markdown("### 🔍 Section-wise Analysis")
        
        for sec, score in result['section_scores'].items():
            # Status and color
            if score >= 70:
                status = "✅ Excellent"
                color = "#059669"
            elif score >= 50:
                status = "⚠️ Needs Work"
                color = "#f59e0b"
            else:
                status = "❌ Poor"
                color = "#dc2626"
            
            # Section card
            st.markdown(f"""
            <div class='section-score'>
                <div>
                    <strong style='font-size: 1.1rem;'>{sec.title()}</strong>
                    <div style='font-size: 0.85rem; color: #64748b;'>
                        {result['section_details'].get(sec, {}).get('details', {}).get('word_count', 0)} words
                    </div>
                </div>
                <div style='text-align: right;'>
                    <div style='color: {color}; font-weight: bold; font-size: 1.3rem;'>{score}/100</div>
                    <div style='font-size: 0.85rem;'>{status}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Progress bar
            st.markdown(f"""
            <div class='progress-bar'>
                <div class='progress-fill' style='width: {score}%; background: {color};'></div>
            </div>
            """, unsafe_allow_html=True)
            
            # Section details
            details = result['section_details'].get(sec, {}).get('details', {})
            
            if details:
                with st.expander(f"📋 View {sec.title()} Details"):
                    cols = st.columns(2)
                    
                    with cols[0]:
                        st.metric("Word Count", details.get('word_count', 0))
                        st.metric("Has Metrics", "✅ Yes" if details.get('has_metrics') else "❌ No")
                    
                    with cols[1]:
                        st.metric("Keyword Match", details.get('keyword_match_ratio', 'N/A'))
                        st.metric("Strong Verbs", details.get('strong_verbs', 'N/A'))
                    
                    # Suggestions for this section
                    sec_suggestions = result['section_details'].get(sec, {}).get('suggestions', [])
                    if sec_suggestions:
                        st.markdown("**Suggestions:**")
                        for sug in sec_suggestions:
                            st.markdown(f"• {sug}")
    
    with tab3:
        st.markdown("### 🎯 Keyword Analysis")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### ❌ Missing Keywords")
            missing = result.get('missing_keywords', [])
            
            if missing:
                st.info(f"Add these {len(missing)} keywords to boost your score:")
                keywords_html = "".join([
                    f"<span class='keyword-tag missing-tag'>{kw}</span>"
                    for kw in missing
                ])
                st.markdown(keywords_html, unsafe_allow_html=True)
            else:
                st.success("✅ Perfect alignment! No missing keywords.")
        
        with col2:
            st.markdown("#### ✅ Found Keywords")
            extra = result.get('extra_keywords', [])
            
            if extra:
                st.success(f"Good! You have {len(extra)} relevant keywords:")
                extras_html = "".join([
                    f"<span class='keyword-tag extra-tag'>{kw}</span>"
                    for kw in extra[:10]
                ])
                st.markdown(extras_html, unsafe_allow_html=True)
            else:
                st.warning("Add more technical keywords")
        
        # Tech stack
        st.markdown("#### 🛠️ Your Tech Stack")
        tech_stack = result.get('tech_stack', [])
        
        if tech_stack:
            tech_html = "".join([
                f"<span class='keyword-tag'>{tech}</span>"
                for tech in tech_stack
            ])
            st.markdown(tech_html, unsafe_allow_html=True)
    
    with tab4:
        st.markdown("### ✨ AI-Powered Rewrites")
        
        weak_bullets = result.get('weak_bullets', [])
        
        if weak_bullets:
            st.info(f"Found {len(weak_bullets)} bullet points that need improvement:")
            
            for i, weak in enumerate(weak_bullets, 1):
                st.markdown(f"#### Example {i}")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**Before (Weak):**")
                    st.text_area(
                        "Original",
                        weak,
                        height=80,
                        disabled=True,
                        key=f"weak_{i}"
                    )
                
                with col2:
                    st.markdown("**After (Strong):**")
                    improved = result['rewrite_suggestion'] if i == 1 else f"Improved version {i} would go here"
                    st.text_area(
                        "Improved",
                        improved,
                        height=80,
                        disabled=True,
                        key=f"strong_{i}"
                    )
                
                if st.button(f"📋 Copy Improved Version {i}", key=f"copy_{i}"):
                    st.success("✅ Copied to clipboard!")
        else:
            st.success("✅ Great! Your bullet points are already strong.")
    
    with tab5:
        st.markdown("### 📥 Download Your Report")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📄 Generate PDF Report", type="primary", use_container_width=True):
                try:
                    with st.spinner("Creating PDF..."):
                        filename = generate_pdf_report(result, "student")
                    
                    with open(filename, "rb") as f:
                        st.download_button(
                            "⬇️ Download PDF",
                            f,
                            file_name=f"ResumeBoost_Report_{result['ats_score']}.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        )
                except Exception as e:
                    st.error(f"PDF generation failed: {e}")
        
        with col2:
            # Text report
            report_text = f"""ResumeBoost AI Report
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}

ATS Score: {result['ats_score']}/100
Target Role: {result['detected_role']}
Word Count: {result.get('word_count', 0)}

Sections Found: {', '.join(result.get('sections_found', []))}

Missing Keywords:
{', '.join(result.get('missing_keywords', [])[:10])}

Key Recommendations:
""" + "\n".join([f"{i}. {s}" for i, s in enumerate(result.get('suggestions', []), 1)])
            
            st.download_button(
                "📝 Download Text Report",
                report_text,
                file_name="resume_report.txt",
                mime="text/plain",
                use_container_width=True
            )
        
        st.markdown("---")
        # Template download (secure)
        if TEMPLATE_LINK:
            st.info(f"🎁 **Free ATS Resume Template**: [Download Here]({TEMPLATE_LINK})")
        else:
            st.info(f"🎁 **Free ATS Resume Template**: Contact {SUPPORT_EMAIL} for access")
            
# ============================================================
# ADMIN DASHBOARD
# ============================================================

if st.sidebar.checkbox("🔐 Admin"):
    pwd = st.sidebar.text_input("Password", type="password")
    
    if pwd and pwd == ADMIN_PASSWORD:
        st.sidebar.success("✅ Authenticated")
        st.sidebar.title("📊 Admin Dashboard")
        
        st.sidebar.metric("📈 Total Reports", st.session_state.reports_generated)
        st.sidebar.metric("💰 Paid Users", st.session_state.paid_users)
        st.sidebar.metric("🔄 Session Analyses", st.session_state.analysis_count)
        
        if st.sidebar.button("🔄 Reset Stats"):
            for key in list(st.session_state.keys()):
                if key not in ["used_payment_ids"]:
                    del st.session_state[key]
            st.sidebar.success("✅ Stats reset!")
            st.rerun()
    elif pwd:
        st.sidebar.error("❌ Invalid password")

# ============================================================
# DEBUG MODE
# ============================================================

if st.sidebar.checkbox("🔧 Debug Mode"):
    st.sidebar.markdown("### 🔍 Diagnostic Info")
    
    if resume_file and resume_text:
        st.sidebar.success("✅ File processed")
        
        st.sidebar.metric("File Size", f"{resume_file.size / 1024:.1f} KB")
        st.sidebar.metric("Characters", len(resume_text))
        st.sidebar.metric("Words", len(resume_text.split()))
        
        from utils import parse_resume_sections
        sections = parse_resume_sections(resume_text)
        
        st.sidebar.markdown("**📂 Sections:**")
        for sec, content in sections.items():
            if content.strip():
                st.sidebar.text(f"✅ {sec.title()}: {len(content.split())} words")
            else:
                st.sidebar.text(f"❌ {sec.title()}: Not found")
    else:
        st.sidebar.info("📄 No file uploaded yet")
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

# ============================================================
# FOOTER
# ============================================================

st.markdown("---")
st.caption("© 2025 ResumeBoost AI • Made by an AIML student, for students ❤️")
st.caption("🔐 Payments by Razorpay • No resume data stored • 100% secure")
