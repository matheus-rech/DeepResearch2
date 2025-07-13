"""
Streamlit UI for Systematic Review Screener
Provides interface for uploading citations, configuring criteria, and reviewing results
"""
import streamlit as st
import pandas as pd
import json
import os
import threading
import time
from datetime import datetime
from dotenv import load_dotenv

import parsers
import database as db
from deep_research import run_systematic_screening
import ice_critic

# Load environment variables
load_dotenv()

# Configuration
MCP_URL = os.getenv("MCP_URL", "http://localhost:8001/sse/")

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

        # Progress indicator
        progress_steps = ["upload", "criteria", "screen", "results"]
        current_idx = progress_steps.index(st.session_state.current_step)
        progress = (current_idx + 1) / len(progress_steps)
        st.progress(progress)

        # Step indicators
        steps = {
            "upload": "1. Upload Citations",
            "criteria": "2. Define Criteria", 
            "screen": "3. Run Screening",
            "results": "4. Review Results"
        }

        for i, (step_key, step_name) in enumerate(steps.items()):
            if st.session_state.current_step == step_key:
                st.success(f"**→ {step_name}**")
            elif i < current_idx:
                st.info(f"✓ {step_name}")
            else:
                st.text(step_name)

        st.divider()

        # Corpus statistics
        if st.session_state.citations_loaded:
            stats = db.get_corpus_stats()
            st.metric("Total Citations", stats["total_citations"])

            if stats["year_distribution"]:
                st.subheader("Year Distribution")
                year_df = pd.DataFrame(stats["year_distribution"])
                if not year_df.empty:
                    st.bar_chart(year_df.set_index("year")["count"])
                    
        # Help section
        st.divider()
        with st.expander("💡 Help"):
            st.markdown("""
            **Quick Guide:**
            1. **Upload**: Import citations from PubMed, RIS, CSV
            2. **Criteria**: Define PICOTT and inclusion/exclusion rules
            3. **Screen**: AI analyzes each citation
            4. **Results**: Review and export findings
            
            **Tips:**
            - Use multi-agent mode for thorough screening
            - Check ICE analysis for quality issues
            - Export results in multiple formats
            """)

    # Main content area
    if st.session_state.current_step == "upload":
        show_upload_step()
    elif st.session_state.current_step == "criteria":
        show_criteria_step()
    elif st.session_state.current_step == "screen":
        show_screening_step()
    elif st.session_state.current_step == "results":
        show_results_step()



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
                st.session_state.current_step = "criteria"
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

    # Citation Browser (if citations exist)
    if st.session_state.citations_loaded or corpus_stats["total_citations"] > 0:
        st.divider()
        st.subheader("📄 Browse Your Citations")

        # Get citations from database
        with db.get_db() as database:
            citations_query = database.query(db.Citation).limit(100).all()  # Limit for performance

            if citations_query:
                # Convert to DataFrame for easier handling
                citations_data = []
                for citation in citations_query:
                    citations_data.append({
                        'id': citation.id,
                        'title': citation.title,
                        'abstract': citation.abstract[:200] + "..." if citation.abstract and len(citation.abstract) > 200 else citation.abstract,
                        'year': citation.year,
                        'journal': citation.journal,
                        'authors': citation.authors,
                        'doi': citation.doi
                    })

                df = pd.DataFrame(citations_data)

                # Search and filter options
                col1, col2 = st.columns(2)

                with col1:
                    search_query = st.text_input("🔍 Search titles/abstracts", placeholder="Enter keywords...")

                with col2:
                    if df['year'].notna().any():
                        min_year = int(df['year'].min())
                        max_year = int(df['year'].max())
                        year_range = st.slider("Publication Year Range", min_year, max_year, (min_year, max_year))
                    else:
                        year_range = None

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

                st.write(f"Showing {len(filtered_df)} of {len(df)} citations")

                # Display citations (show first 10)
                display_count = min(10, len(filtered_df))
                for idx, citation in filtered_df.head(display_count).iterrows():
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
                                            for author in authors[:5]:  # Show first 5 authors
                                                st.write(f"• {author}")
                                            if len(authors) > 5:
                                                st.write(f"... and {len(authors) - 5} more")
                                except (json.JSONDecodeError, TypeError):
                                    st.markdown(f"**Authors:** {citation['authors'][:50]}...")

                if len(filtered_df) > display_count:
                    st.info(f"Showing first {display_count} citations. Use search to narrow results.")

                # Continue button
                st.divider()
                if st.button("Continue to Define Criteria →", type="primary", use_container_width=True):
                    st.session_state.current_step = "criteria"
                    st.rerun()


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
            st.session_state.current_step = "upload"
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
                  delta=f"{stats['inclusion_rate']*100:.1f}%",
                  delta_color="normal")
    with col3:
        st.metric("Excluded", stats["excluded"],
                  delta=f"{(1-stats['inclusion_rate'])*100:.1f}%",
                  delta_color="inverse")
    with col4:
        confidence = stats["confidence_breakdown"]
        high_conf_pct = (confidence['high'] / stats['total_screened'] * 100) if stats['total_screened'] > 0 else 0
        st.metric("High Confidence", 
                  f"{confidence['high']}/{stats['total_screened']}",
                  delta=f"{high_conf_pct:.1f}%")

    # Add visualization section
    st.divider()
    with st.expander("📊 Screening Overview", expanded=True):
        col_vis1, col_vis2 = st.columns(2)
        
        with col_vis1:
            # Pie chart for inclusion/exclusion
            pie_data = pd.DataFrame({
                'Status': ['Included', 'Excluded'],
                'Count': [stats['included'], stats['excluded']]
            })
            st.subheader("Inclusion vs Exclusion")
            st.bar_chart(pie_data.set_index('Status'))
        
        with col_vis2:
            # Confidence distribution
            conf_data = pd.DataFrame({
                'Confidence': ['High', 'Medium', 'Low'],
                'Count': [confidence['high'], confidence['medium'], confidence['low']]
            })
            st.subheader("Confidence Distribution")
            st.bar_chart(conf_data.set_index('Confidence'))
    
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





if __name__ == "__main__":
    main()