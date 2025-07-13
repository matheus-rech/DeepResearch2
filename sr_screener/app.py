"""
Streamlit UI for Systematic Review Screener
Provides interface for uploading citations, configuring criteria, and reviewing results
"""
import streamlit as st
import pandas as pd
import json
import os
import threading
from datetime import datetime
from dotenv import load_dotenv

import parsers
import database as db
from deep_research import run_systematic_screening
import ice_critic

# Load environment variables
load_dotenv()

# Configuration
MCP_URL = os.getenv("MCP_URL", "http://localhost:8000/sse/")

# Page configuration
st.set_page_config(
    page_title="Systematic Review Screener",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .stProgress > div > div > div > div {
        background-color: #4CAF50;
    }
    .included-citation {
        background-color: #e8f5e9;
        padding: 10px;
        border-radius: 5px;
        margin: 5px 0;
    }
    .excluded-citation {
        background-color: #ffebee;
        padding: 10px;
        border-radius: 5px;
        margin: 5px 0;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if "citations_loaded" not in st.session_state:
    st.session_state.citations_loaded = False
if "screening_results" not in st.session_state:
    st.session_state.screening_results = None
if "current_step" not in st.session_state:
    st.session_state.current_step = "upload"


def main():
    """Main application function."""
    st.title("📚 Systematic Review Screener")
    st.markdown("Automated screening tool powered by Deep Research AI")
    
    # Sidebar navigation
    with st.sidebar:
        st.header("Navigation")
        
        # Step indicators
        steps = {
            "upload": "1. Upload Citations",
            "visualize": "2. Visualize Data",
            "criteria": "3. Define Criteria", 
            "screen": "4. Run Screening",
            "results": "5. Review Results"
        }
        
        for step_key, step_name in steps.items():
            if st.session_state.current_step == step_key:
                st.success(f"**→ {step_name}**")
            else:
                st.info(step_name)
        
        st.divider()
        
        # Corpus statistics
        if st.session_state.citations_loaded:
            stats = db.get_corpus_stats()
            st.metric("Total Citations", stats["total_citations"])
            
            if stats["year_distribution"]:
                st.subheader("Year Distribution")
                year_df = pd.DataFrame(stats["year_distribution"])
                st.bar_chart(year_df.set_index("year")["count"])
    
    # Main content area
    if st.session_state.current_step == "upload":
        show_upload_step()
    elif st.session_state.current_step == "criteria":
        show_criteria_step()
    elif st.session_state.current_step == "screen":
        show_screening_step()
    elif st.session_state.current_step == "results":
        show_results_step()
    elif st.session_state.current_step == "visualize":
        show_visualization_step()


def show_upload_step():
    """Show the citation upload interface."""
    st.header("Step 1: Upload Citations")
    st.markdown("""
    Upload your citation export file. Supported formats:
    - **PubMed XML** (.xml) - From PubMed export
    - **RIS** (.ris) - From EndNote, Mendeley, etc.
    - **CSV** (.csv) - Generic format with standard columns
    - **EndNote XML** (.xml) - From EndNote library
    """)
    
    uploaded_file = st.file_uploader(
        "Choose a citation file",
        type=['xml', 'ris', 'csv', 'nbib'],
        help="Upload your exported citations from reference management software"
    )
    
    if uploaded_file:
        st.info(f"File uploaded: {uploaded_file.name} ({uploaded_file.size:,} bytes)")
        
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("📥 Parse & Load", type="primary", use_container_width=True):
                with st.spinner("Parsing citations..."):
                    try:
                        # Parse the file
                        df = parsers.parse_citations(uploaded_file, uploaded_file.name)
                        
                        # Show preview
                        st.success(f"Successfully parsed {len(df)} citations!")
                        
                        # Display sample
                        st.subheader("Preview (first 5 citations)")
                        preview_df = df[['id', 'title', 'year', 'journal']].head()
                        st.dataframe(preview_df, use_container_width=True)
                        
                        # Save to database
                        with st.spinner("Loading into database..."):
                            db.init_db()
                            stats = db.bulk_insert_citations(df)
                        
                        # Show detailed results
                        if stats['inserted'] > 0:
                            st.success(f"✅ Added {stats['inserted']} new citations!")
                        if stats['updated'] > 0:
                            st.info(f"📝 Updated {stats['updated']} existing citations")
                        if stats['skipped'] > 0:
                            st.warning(f"⚠️ Skipped {stats['skipped']} citations due to errors")
                        st.session_state.citations_loaded = True
                        st.session_state.current_step = "visualize"
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"Error parsing file: {str(e)}")
                        st.exception(e)
    
    # Option to skip if citations already loaded
    corpus_stats = db.get_corpus_stats()
    if corpus_stats["total_citations"] > 0:
        st.divider()
        st.info(f"ℹ️ Database already contains {corpus_stats['total_citations']} citations")
        
        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            if st.button("Continue with existing corpus →", use_container_width=True):
                st.session_state.citations_loaded = True
                st.session_state.current_step = "visualize"
                st.rerun()
        
        with col2:
            if st.button("Add to existing corpus", use_container_width=True):
                st.info("Upload a file above to add more citations")
        
        with col3:
            if st.button("🗑️ Clear all", type="secondary", use_container_width=True):
                if st.session_state.get('confirm_clear', False):
                    count = db.clear_all_citations()
                    st.success(f"Cleared {count} citations from database")
                    st.session_state.confirm_clear = False
                    st.rerun()
                else:
                    st.session_state.confirm_clear = True
                    st.warning("Click again to confirm clearing all citations")


def show_criteria_step():
    """Show the screening criteria configuration interface."""
    st.header("Step 2: Define Screening Criteria")
    st.markdown("Configure your systematic review screening criteria below.")
    
    # PICOTT Criteria
    st.subheader("PICOTT Criteria")
    st.markdown("Define the key elements of your research question:")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        population = st.text_area(
            "**P**opulation",
            placeholder="e.g., Adults with type 2 diabetes",
            help="Who are the participants/patients?"
        )
        intervention = st.text_area(
            "**I**ntervention",
            placeholder="e.g., Continuous glucose monitoring",
            help="What is the intervention or exposure?"
        )
    
    with col2:
        comparator = st.text_area(
            "**C**omparator",
            placeholder="e.g., Standard blood glucose monitoring",
            help="What is the comparison or control?"
        )
        outcome = st.text_area(
            "**O**utcome",
            placeholder="e.g., Glycemic control (HbA1c levels)",
            help="What are the outcomes of interest?"
        )
    
    with col3:
        timeframe = st.text_area(
            "**T**imeframe",
            placeholder="e.g., Follow-up ≥ 6 months",
            help="What is the timeframe for outcomes?"
        )
        study_type = st.text_area(
            "Study **T**ype",
            placeholder="e.g., Randomized controlled trials",
            help="What types of studies to include?"
        )
    
    # Additional criteria
    st.divider()
    st.subheader("Additional Criteria")
    
    col3, col4 = st.columns(2)
    
    with col3:
        st.markdown("**Inclusion Criteria**")
        inclusion_criteria = []
        
        # Common inclusion criteria with checkboxes
        if st.checkbox("Randomized Controlled Trials (RCTs)"):
            inclusion_criteria.append("Study design: Randomized controlled trial")
        if st.checkbox("Prospective cohort studies"):
            inclusion_criteria.append("Study design: Prospective cohort study")
        if st.checkbox("English language"):
            inclusion_criteria.append("Published in English")
        if st.checkbox("Peer-reviewed publications"):
            inclusion_criteria.append("Published in peer-reviewed journal")
        
        # Year range
        year_filter = st.checkbox("Filter by publication year")
        if year_filter:
            year_range = st.slider(
                "Publication year range",
                min_value=1990,
                max_value=2025,
                value=(2015, 2025)
            )
            inclusion_criteria.append(f"Published between {year_range[0]} and {year_range[1]}")
        
        # Custom criteria
        custom_inclusion = st.text_area(
            "Additional inclusion criteria (one per line)",
            placeholder="e.g., Sample size ≥ 100\nFollow-up ≥ 6 months"
        )
        if custom_inclusion:
            inclusion_criteria.extend([c.strip() for c in custom_inclusion.split('\n') if c.strip()])
    
    with col4:
        st.markdown("**Exclusion Criteria**")
        exclusion_criteria = []
        
        # Common exclusion criteria
        if st.checkbox("Case reports"):
            exclusion_criteria.append("Study design: Case report or case series")
        if st.checkbox("Reviews and meta-analyses"):
            exclusion_criteria.append("Study type: Review, systematic review, or meta-analysis")
        if st.checkbox("Conference abstracts"):
            exclusion_criteria.append("Publication type: Conference abstract or poster")
        if st.checkbox("Protocols only"):
            exclusion_criteria.append("Study protocols without results")
        if st.checkbox("Animal studies"):
            exclusion_criteria.append("Non-human studies")
        
        # Custom exclusion
        custom_exclusion = st.text_area(
            "Additional exclusion criteria (one per line)",
            placeholder="e.g., Duplicate publications\nNo full text available"
        )
        if custom_exclusion:
            exclusion_criteria.extend([c.strip() for c in custom_exclusion.split('\n') if c.strip()])
    
    # Save criteria button
    st.divider()
    col5, col6, col7 = st.columns([1, 1, 2])
    
    with col5:
        if st.button("← Back", use_container_width=True):
            st.session_state.current_step = "visualize"
            st.rerun()
    
    with col6:
        if st.button("Save & Continue →", type="primary", use_container_width=True):
            # Validate criteria
            if not all([population, intervention, outcome]):
                st.error("Please fill in at least Population, Intervention, and Outcome")
            else:
                # Save criteria to session state
                st.session_state.pico_criteria = {
                    "population": population,
                    "intervention": intervention,
                    "comparator": comparator,
                    "outcome": outcome,
                    "timeframe": timeframe,
                    "study_type": study_type
                }
                st.session_state.inclusion_criteria = inclusion_criteria
                st.session_state.exclusion_criteria = exclusion_criteria
                st.session_state.current_step = "screen"
                st.rerun()


def show_screening_step():
    """Show the screening execution interface."""
    st.header("Step 3: Run Automated Screening")
    
    # Display configured criteria
    st.subheader("Review Your Criteria")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**PICOTT Criteria:**")
        pico = st.session_state.pico_criteria
        st.info(f"""
        - **P**opulation: {pico['population']}
        - **I**ntervention: {pico['intervention']}
        - **C**omparator: {pico['comparator'] or 'Not specified'}
        - **O**utcome: {pico['outcome']}
        - **T**imeframe: {pico.get('timeframe', 'Not specified') or 'Not specified'}
        - Study **T**ype: {pico.get('study_type', 'Not specified') or 'Not specified'}
        """)
    
    with col2:
        st.markdown("**Inclusion Criteria:**")
        if st.session_state.inclusion_criteria:
            for criterion in st.session_state.inclusion_criteria:
                st.write(f"✓ {criterion}")
        else:
            st.write("None specified")
        
        st.markdown("**Exclusion Criteria:**")
        if st.session_state.exclusion_criteria:
            for criterion in st.session_state.exclusion_criteria:
                st.write(f"✗ {criterion}")
        else:
            st.write("None specified")
    
    # Corpus info
    stats = db.get_corpus_stats()
    st.info(f"📊 Ready to screen {stats['total_citations']} citations")
    
    # Advanced options
    with st.expander("Advanced Options"):
        use_multi_agent = st.checkbox(
            "Use Multi-Agent Architecture",
            value=st.session_state.get('use_multi_agent', False),
            key='use_multi_agent',
            help="Enable multi-agent pipeline with specialized agents for triage, clarification, instruction building, and screening. This can improve quality but takes longer."
        )
        
        if use_multi_agent:
            st.info("""
            **Multi-Agent Pipeline:**
            1. **Triage Agent**: Evaluates criteria completeness
            2. **Clarifier Agent**: Generates clarification questions (if needed)
            3. **Instruction Builder**: Creates detailed screening protocol
            4. **Screening Agent**: Performs systematic screening
            
            This approach maximizes context window usage and optimizes each step.
            """)
    
    # Run screening button
    st.divider()
    col3, col4, col5 = st.columns([1, 2, 1])
    
    with col3:
        if st.button("← Back", use_container_width=True):
            st.session_state.current_step = "criteria"
            st.rerun()
    
    with col4:
        if st.button("🚀 Start Screening", type="primary", use_container_width=True):
            # Create a placeholder for progress updates
            progress_placeholder = st.empty()
            
            # Run screening in a separate thread to keep UI responsive
            def run_screening():
                def update_progress(message):
                    progress_placeholder.info(f"🔄 {message}")
                
                try:
                    results = run_systematic_screening(
                        st.session_state.pico_criteria,
                        st.session_state.inclusion_criteria,
                        st.session_state.exclusion_criteria,
                        stats['total_citations'],
                        MCP_URL,
                        callback=update_progress,
                        use_multi_agent=st.session_state.get('use_multi_agent', False)
                    )
                    
                    # Save results
                    st.session_state.screening_results = results
                    st.session_state.screening_timestamp = datetime.now()
                    
                    progress_placeholder.success("✅ Screening completed!")
                    st.session_state.current_step = "results"
                    st.rerun()
                    
                except Exception as e:
                    progress_placeholder.error(f"❌ Screening failed: {str(e)}")
                    st.exception(e)
            
            # Start screening
            screening_thread = threading.Thread(target=run_screening)
            screening_thread.start()
            
            # Show spinner while thread is running
            with st.spinner("Screening in progress... This may take several minutes."):
                screening_thread.join()


def show_results_step():
    """Show the screening results interface."""
    st.header("Step 4: Review Screening Results")
    
    if not st.session_state.screening_results:
        st.error("No screening results found!")
        if st.button("← Back to screening"):
            st.session_state.current_step = "screen"
            st.rerun()
        return
    
    results = st.session_state.screening_results
    stats = results["statistics"]
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Screened", stats["total_screened"])
    with col2:
        st.metric("Included", stats["included"], 
                  delta=f"{stats['inclusion_rate']*100:.1f}%")
    with col3:
        st.metric("Excluded", stats["excluded"])
    with col4:
        confidence = stats["confidence_breakdown"]
        st.metric("High Confidence", 
                  f"{confidence['high']}/{stats['total_screened']}")
    
    # Results tabs
    tab1, tab2, tab3, tab4 = st.tabs(["Included Citations", "Excluded Citations", 
                                       "ICE Analysis", "Export Results"])
    
    with tab1:
        st.subheader(f"Included Citations ({stats['included']})")
        
        # Filter options
        confidence_filter = st.selectbox(
            "Filter by confidence",
            ["All", "High", "Medium", "Low"],
            key="included_confidence"
        )
        
        # Display included citations
        for citation in results["included_citations"]:
            if confidence_filter == "All" or citation["confidence"].lower() == confidence_filter.lower():
                with st.expander(f"{citation['title'][:100]}..."):
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        st.markdown(f"**ID:** {citation['id']}")
                        st.markdown(f"**Decision Reasoning:** {citation['reason']}")
                        
                        # PICOTT elements with exact citations
                        if citation.get("picott"):
                            st.markdown("**PICOTT Elements (with exact citations):**")
                            picott = citation["picott"]
                            
                            # Display each PICOTT element with its citation
                            for element, quote in picott.items():
                                element_name = element.replace("studyType", "Study Type").capitalize()
                                if quote and quote != "Not found":
                                    st.markdown(f"- **{element_name}:** \"{quote}\"")
                                else:
                                    st.markdown(f"- **{element_name}:** Not found in abstract")
                        
                        # Inclusion criteria matches
                        if citation.get("inclusionCriteria"):
                            st.markdown("**Matched Inclusion Criteria:**")
                            for criterion in citation["inclusionCriteria"]:
                                st.markdown(f"- {criterion}")
                        
                        # Exclusion criteria matches (should be empty for included)
                        if citation.get("exclusionCriteria"):
                            st.markdown("**Matched Exclusion Criteria:**")
                            for criterion in citation["exclusionCriteria"]:
                                st.markdown(f"- {criterion}")
                    
                    with col2:
                        st.markdown(f"**Confidence:** {citation['confidence']}")
                        
                        # View full citation button
                        if st.button(f"View Full", key=f"view_{citation['id']}"):
                            full_citation = db.fetch_citation(citation['id'])
                            if full_citation:
                                st.json(full_citation)
    
    with tab2:
        st.subheader(f"Excluded Citations ({stats['excluded']})")
        
        # Group by exclusion reason
        reason_groups = {}
        for citation in results["excluded_citations"]:
            reason = citation['reason']
            if reason not in reason_groups:
                reason_groups[reason] = []
            reason_groups[reason].append(citation)
        
        # Display by reason
        for reason, citations in reason_groups.items():
            with st.expander(f"{reason} ({len(citations)} citations)"):
                for citation in citations[:5]:  # Show first 5 with details
                    with st.container():
                        st.markdown(f"**{citation['id']}**: {citation['title'][:80]}...")
                        
                        # Show exclusion criteria that were matched
                        if citation.get("exclusionCriteria"):
                            st.markdown("**Matched Exclusion Criteria:**")
                            for criterion in citation["exclusionCriteria"]:
                                st.markdown(f"- {criterion}")
                        
                        # Show PICOTT elements for context
                        if citation.get("picott") and st.checkbox(f"Show PICOTT elements", key=f"picott_{citation['id']}"):
                            for element, quote in citation["picott"].items():
                                if quote and quote != "Not found":
                                    element_name = element.replace("studyType", "Study Type").capitalize()
                                    st.markdown(f"- **{element_name}:** \"{quote[:100]}...\"" if len(quote) > 100 else f"- **{element_name}:** \"{quote}\"")
                        
                        st.divider()
                        
                if len(citations) > 5:
                    st.write(f"... and {len(citations) - 5} more citations")
    
    with tab3:
        st.subheader("ICE Analysis (Internal Consistency Evaluation)")
        
        # Run ICE analysis
        if st.button("Run ICE Analysis"):
            with st.spinner("Analyzing screening decisions..."):
                critique_results = ice_critic.analyze_screening_consistency(
                    results["results"],
                    st.session_state.pico_criteria
                )
                
                # Display critique results
                if critique_results["issues"]:
                    st.warning(f"Found {len(critique_results['issues'])} potential issues")
                    
                    # Group by severity
                    by_severity = {}
                    for issue in critique_results["issues"]:
                        severity = issue["severity"]
                        if severity not in by_severity:
                            by_severity[severity] = []
                        by_severity[severity].append(issue)
                    
                    # Display issues
                    for severity in ["high", "medium", "low"]:
                        if severity in by_severity:
                            st.subheader(f"{severity.capitalize()} Priority Issues")
                            for issue in by_severity[severity]:
                                with st.expander(f"{issue['type']}: {issue['citation_id']}"):
                                    st.write(issue["description"])
                                    st.info(f"Suggestion: {issue['suggestion']}")
                else:
                    st.success("No consistency issues found!")
                
                # Display summary statistics
                st.divider()
                st.json(critique_results["summary"])
    
    with tab4:
        st.subheader("Export Results")
        
        # Run ICE analysis automatically for export
        ice_results = ice_critic.analyze_screening_consistency(
            results["results"],
            st.session_state.pico_criteria
        )
        
        # Prepare comprehensive export data
        export_data = {
            "screening_date": st.session_state.screening_timestamp.isoformat(),
            "criteria": {
                "picott": st.session_state.pico_criteria,
                "inclusion": st.session_state.inclusion_criteria,
                "exclusion": st.session_state.exclusion_criteria
            },
            "statistics": stats,
            "results": results["results"],
            "ice_analysis": {
                "issues": ice_results["issues"],
                "summary": ice_results["summary"]
            }
        }
        
        # Export options
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # JSON export
            st.download_button(
                label="📥 Download JSON",
                data=json.dumps(export_data, indent=2),
                file_name=f"screening_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
        
        with col2:
            # CSV export for included citations
            included_df = pd.DataFrame(results["included_citations"])
            csv = included_df.to_csv(index=False)
            st.download_button(
                label="📥 Download Included (CSV)",
                data=csv,
                file_name=f"included_citations_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        
        with col3:
            # PRISMA flow diagram data
            prisma_data = {
                "identification": stats["total_screened"],
                "screening": stats["total_screened"],
                "included": stats["included"],
                "excluded": stats["excluded"]
            }
            st.download_button(
                label="📥 PRISMA Data",
                data=json.dumps(prisma_data, indent=2),
                file_name=f"prisma_flow_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
    
    # Navigation
    st.divider()
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("← New Screening"):
            # Reset to criteria step
            st.session_state.current_step = "criteria"
            st.session_state.screening_results = None
            st.rerun()
    
    with col2:
        if st.button("🏠 Start Over"):
            # Reset everything
            for key in ["citations_loaded", "screening_results", "pico_criteria", 
                       "inclusion_criteria", "exclusion_criteria"]:
                if key in st.session_state:
                    del st.session_state[key]
            st.session_state.current_step = "upload"
            st.rerun()


def show_visualization_step():
    """Show comprehensive visualization of the citation corpus."""
    st.header("Step 2: Visualize Your Citation Corpus")
    st.markdown("Explore and analyze your uploaded citations with interactive visualizations.")
    
    # Get all citations from database
    with db.get_db() as database:
        citations_query = database.query(db.Citation).all()
        
        if not citations_query:
            st.warning("No citations found in database. Please upload citations first.")
            if st.button("← Back to Upload"):
                st.session_state.current_step = "upload"
                st.rerun()
            return
        
        # Convert to DataFrame for analysis
        citations_data = []
        for citation in citations_query:
            citations_data.append({
                'id': citation.id,
                'title': citation.title,
                'abstract': citation.abstract[:200] + "..." if citation.abstract and len(citation.abstract) > 200 else citation.abstract,
                'year': citation.year,
                'journal': citation.journal,
                'authors': citation.authors,
                'doi': citation.doi,
                'created_at': citation.created_at
            })
        
        df = pd.DataFrame(citations_data)
    
    # Summary statistics
    st.subheader("📊 Corpus Overview")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Citations", len(df))
    with col2:
        valid_years = df[df['year'].notna()]['year']
        if len(valid_years) > 0:
            st.metric("Year Range", f"{int(valid_years.min())}-{int(valid_years.max())}")
        else:
            st.metric("Year Range", "N/A")
    with col3:
        unique_journals = df['journal'].nunique()
        st.metric("Unique Journals", unique_journals)
    with col4:
        with_abstracts = df['abstract'].notna().sum()
        st.metric("With Abstracts", f"{with_abstracts}/{len(df)}")
    
    # Tabs for different visualizations
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📅 Publication Timeline", 
        "📚 Journal Distribution", 
        "🔍 Citation Browser",
        "📝 Text Analysis",
        "📊 Data Quality"
    ])
    
    with tab1:
        st.subheader("Publication Timeline")
        
        # Year distribution
        if df['year'].notna().any():
            year_counts = df['year'].value_counts().sort_index()
            
            # Line chart
            st.markdown("**Publications by Year**")
            st.line_chart(year_counts)
            
            # Bar chart with better formatting
            col1, col2 = st.columns([3, 1])
            with col1:
                st.bar_chart(year_counts)
            
            with col2:
                st.markdown("**Top Years:**")
                top_years = year_counts.head(5)
                for year, count in top_years.items():
                    st.write(f"{int(year)}: {count} papers")
        else:
            st.info("No year information available in the citations.")
    
    with tab2:
        st.subheader("Journal Distribution")
        
        if df['journal'].notna().any():
            journal_counts = df['journal'].value_counts().head(20)
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.markdown("**Top 20 Journals**")
                st.bar_chart(journal_counts)
            
            with col2:
                st.markdown("**Journal Statistics:**")
                st.write(f"Unique journals: {df['journal'].nunique()}")
                st.write(f"Most cited journal: {journal_counts.index[0] if len(journal_counts) > 0 else 'N/A'}")
                st.write(f"Papers in top journal: {journal_counts.iloc[0] if len(journal_counts) > 0 else 0}")
                
                # Show top journals as table
                st.markdown("**Top Journals:**")
                top_journals_df = pd.DataFrame({
                    'Journal': journal_counts.head(10).index,
                    'Count': journal_counts.head(10).values
                })
                st.dataframe(top_journals_df, use_container_width=True)
        else:
            st.info("No journal information available in the citations.")
    
    with tab3:
        st.subheader("Citation Browser")
        
        # Search and filter options
        col1, col2, col3 = st.columns(3)
        
        with col1:
            search_query = st.text_input("🔍 Search titles/abstracts", placeholder="Enter keywords...")
        
        with col2:
            if df['year'].notna().any():
                min_year = int(df['year'].min())
                max_year = int(df['year'].max())
                year_range = st.slider("Publication Year Range", min_year, max_year, (min_year, max_year))
            else:
                year_range = None
        
        with col3:
            if df['journal'].notna().any():
                journals = ['All'] + sorted(df['journal'].dropna().unique().tolist())
                selected_journal = st.selectbox("Journal Filter", journals)
            else:
                selected_journal = 'All'
        
        # Apply filters
        filtered_df = df.copy()
        
        if search_query:
            mask = (
                filtered_df['title'].str.contains(search_query, case=False, na=False) |
                filtered_df['abstract'].str.contains(search_query, case=False, na=False)
            )
            filtered_df = filtered_df[mask]
        
        if year_range and df['year'].notna().any():
            filtered_df = filtered_df[
                (filtered_df['year'] >= year_range[0]) & 
                (filtered_df['year'] <= year_range[1])
            ]
        
        if selected_journal != 'All':
            filtered_df = filtered_df[filtered_df['journal'] == selected_journal]
        
        st.write(f"Showing {len(filtered_df)} of {len(df)} citations")
        
        # Pagination
        citations_per_page = 10
        total_pages = (len(filtered_df) + citations_per_page - 1) // citations_per_page
        
        if total_pages > 0:
            page = st.selectbox("Page", range(1, total_pages + 1))
            start_idx = (page - 1) * citations_per_page
            end_idx = start_idx + citations_per_page
            page_df = filtered_df.iloc[start_idx:end_idx]
            
            # Display citations
            for idx, citation in page_df.iterrows():
                with st.expander(f"📄 {citation['title'][:80]}... ({citation['year'] if pd.notna(citation['year']) else 'No year'})"):
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        st.markdown(f"**Title:** {citation['title']}")
                        if citation['abstract']:
                            st.markdown(f"**Abstract:** {citation['abstract']}")
                        st.markdown(f"**Journal:** {citation['journal'] if citation['journal'] else 'Not specified'}")
                        if citation['doi']:
                            st.markdown(f"**DOI:** {citation['doi']}")
                    
                    with col2:
                        st.markdown(f"**Year:** {int(citation['year']) if pd.notna(citation['year']) else 'N/A'}")
                        st.markdown(f"**ID:** {citation['id']}")
                        
                        # Authors info
                        if citation['authors']:
                            try:
                                authors = json.loads(citation['authors'])
                                if isinstance(authors, list) and len(authors) > 0:
                                    st.markdown(f"**Authors:** {len(authors)} authors")
                                    with st.expander("View authors"):
                                        for author in authors[:10]:  # Show first 10 authors
                                            st.write(f"• {author}")
                                        if len(authors) > 10:
                                            st.write(f"... and {len(authors) - 10} more")
                            except (json.JSONDecodeError, TypeError):
                                st.markdown(f"**Authors:** {citation['authors'][:50]}...")
        else:
            st.info("No citations match the current filters.")
    
    with tab4:
        st.subheader("Text Analysis")
        
        # Word cloud of titles
        if len(df) > 0:
            all_titles = ' '.join(df['title'].dropna().astype(str))
            
            # Simple word frequency analysis
            import re
            words = re.findall(r'\b[a-zA-Z]{3,}\b', all_titles.lower())
            
            # Filter out common words
            stop_words = {'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'had', 
                         'her', 'was', 'one', 'our', 'out', 'day', 'get', 'has', 'him', 'his', 
                         'how', 'its', 'may', 'new', 'now', 'old', 'see', 'two', 'who', 'boy', 
                         'did', 'she', 'use', 'way', 'who', 'oil', 'sit', 'set', 'own', 'under'}
            
            filtered_words = [word for word in words if word not in stop_words and len(word) > 3]
            word_freq = pd.Series(filtered_words).value_counts().head(30)
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Most Common Words in Titles**")
                st.bar_chart(word_freq)
            
            with col2:
                st.markdown("**Word Frequency Table**")
                word_df = pd.DataFrame({
                    'Word': word_freq.index,
                    'Frequency': word_freq.values
                })
                st.dataframe(word_df, use_container_width=True)
            
            # Abstract length analysis
            if df['abstract'].notna().any():
                abstract_lengths = df['abstract'].dropna().str.len()
                
                st.markdown("**Abstract Length Distribution**")
                st.histogram_chart(abstract_lengths, bins=30)
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Avg Abstract Length", f"{int(abstract_lengths.mean())} chars")
                with col2:
                    st.metric("Shortest Abstract", f"{abstract_lengths.min()} chars")
                with col3:
                    st.metric("Longest Abstract", f"{abstract_lengths.max()} chars")
    
    with tab5:
        st.subheader("Data Quality Assessment")
        
        # Missing data analysis
        st.markdown("**Data Completeness**")
        
        completeness_data = {
            'Field': ['Title', 'Abstract', 'Year', 'Journal', 'Authors', 'DOI'],
            'Complete': [
                df['title'].notna().sum(),
                df['abstract'].notna().sum(),
                df['year'].notna().sum(),
                df['journal'].notna().sum(),
                df['authors'].notna().sum(),
                df['doi'].notna().sum()
            ],
            'Missing': [
                df['title'].isna().sum(),
                df['abstract'].isna().sum(),
                df['year'].isna().sum(),
                df['journal'].isna().sum(),
                df['authors'].isna().sum(),
                df['doi'].isna().sum()
            ]
        }
        
        completeness_df = pd.DataFrame(completeness_data)
        completeness_df['Percentage'] = (completeness_df['Complete'] / len(df) * 100).round(1)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.dataframe(completeness_df, use_container_width=True)
        
        with col2:
            # Visualization of completeness
            import matplotlib.pyplot as plt
            fig, ax = plt.subplots()
            ax.barh(completeness_df['Field'], completeness_df['Percentage'])
            ax.set_xlabel('Completeness (%)')
            ax.set_title('Data Completeness by Field')
            st.pyplot(fig)
        
        # Duplicate detection
        st.markdown("**Duplicate Detection**")
        
        # Check for potential duplicates by title similarity
        title_duplicates = df['title'].duplicated().sum()
        doi_duplicates = df['doi'].duplicated().sum() if df['doi'].notna().any() else 0
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Exact Title Duplicates", title_duplicates)
        with col2:
            st.metric("DOI Duplicates", doi_duplicates)
        with col3:
            quality_score = (completeness_df['Percentage'].mean() - title_duplicates * 2).round(1)
            st.metric("Quality Score", f"{max(0, quality_score)}%")
        
        if title_duplicates > 0:
            st.warning(f"Found {title_duplicates} potential duplicate titles. Review before screening.")
            
            # Show duplicates
            duplicate_titles = df[df['title'].duplicated(keep=False)]['title'].unique()
            with st.expander("View Duplicate Titles"):
                for title in duplicate_titles[:10]:
                    st.write(f"• {title}")
                if len(duplicate_titles) > 10:
                    st.write(f"... and {len(duplicate_titles) - 10} more")
    
    # Navigation
    st.divider()
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("← Back to Upload", use_container_width=True):
            st.session_state.current_step = "upload"
            st.rerun()
    
    with col2:
        if st.button("Continue to Criteria →", type="primary", use_container_width=True):
            st.session_state.current_step = "criteria"
            st.rerun()


if __name__ == "__main__":
    main()