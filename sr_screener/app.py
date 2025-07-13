"""
Streamlit UI for Systematic Review Screener
Provides interface for uploading citations, configuring criteria, and reviewing results
"""
import streamlit as st
import pandas as pd
import json
import os
import time
from datetime import datetime
from dotenv import load_dotenv

import parsers
import database as db
from deep_research import run_systematic_screening
import ice_critic
from data_validator import CitationValidator
from pubmed_export import export_citations
from multi_agent_research import run_multi_agent_screening

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
    st.header("Step 1: Load Citations")
    
    # Create tabs for different input methods
    tab1, tab2 = st.tabs(["📁 Upload File", "🔍 Search Academic Databases"])
    
    with tab1:
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

                            # Validate citations
                            validator = CitationValidator()
                            validated_df, validation_report = validator.validate_citations(df)
                        
                            # Show validation warnings
                            if validation_report["critical_issues"]["missing_abstracts"] > 0:
                                st.warning(f"""
                                ⚠️ **Abstract Coverage Warning**
                                - {validation_report['critical_issues']['missing_abstracts']} citations ({validation_report['critical_issues']['missing_abstracts_pct']:.1f}%) are missing abstracts
                                - Abstracts are critical for accurate AI screening
                                
                                **Recommendation**: Consider using a different export format that includes full abstracts
                                """)
                            
                            # Show data quality score
                            quality_score = validation_report["quality_score"]
                            if quality_score < 80:
                                st.error(f"📊 Data Quality Score: {quality_score:.1f}% - Below recommended threshold")
                            else:
                                st.info(f"📊 Data Quality Score: {quality_score:.1f}% - Good quality for screening")
                            
                            # Show CrossRef enrichment status
                            if validation_report["summary"].get("enhanced", 0) > 0:
                                st.success(f"🔍 CrossRef Enrichment: Added abstracts to {validation_report['summary']['enhanced']} citations")
                            
                            # Show recommendations
                            if validation_report.get("recommendations"):
                                with st.expander("📋 Data Quality Recommendations"):
                                    for rec in validation_report["recommendations"]:
                                        st.write(f"• {rec}")
                            
                            # Show problematic citations
                            if validation_report.get("problematic_citations"):
                                with st.expander("⚠️ Citations with Issues"):
                                    for issue in validation_report["problematic_citations"][:5]:
                                        if isinstance(issue, dict) and "citation_id" in issue:
                                            st.write(f"**{issue['citation_id']}**: {issue.get('title', 'Unknown')}")
                                            for prob in issue.get('issues', []):
                                                st.write(f"  - {prob}")
                                        elif "note" in issue:
                                            st.write(issue["note"])

                            # Display sample
                            st.subheader("Preview (first 5 citations)")
                            preview_df = validated_df[['id', 'title', 'year', 'journal']].head()
                            st.dataframe(preview_df, use_container_width=True)

                            # Save to database
                            with st.spinner("Loading validated citations into database..."):
                                db.init_db()
                                stats = db.bulk_insert_citations(validated_df)

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
    
    with tab2:
        st.markdown("""
        Search academic databases directly to ensure high-quality citations with abstracts:
        - **ArXiv**: Preprints in physics, mathematics, computer science, and more
        - **PubMed**: Biomedical and life science literature
        """)
        
        # Check if LlamaIndex readers are available
        if parsers.LLAMA_READERS_AVAILABLE:
            search_source = st.radio(
                "Select Database",
                ["ArXiv", "PubMed"],
                horizontal=True
            )
            
            col1, col2 = st.columns([3, 1])
            
            with col1:
                if search_source == "ArXiv":
                    search_query = st.text_input(
                        "ArXiv Search Query",
                        placeholder="e.g., quantum computing, au:Karpathy, cat:cs.AI",
                        help="Use standard ArXiv search syntax"
                    )
                else:
                    search_query = st.text_input(
                        "PubMed Search Query",
                        placeholder="e.g., diabetes type 2, cancer immunotherapy",
                        help="Use standard PubMed search terms"
                    )
            
            with col2:
                max_results = st.number_input(
                    "Max Results",
                    min_value=1,
                    max_value=100,
                    value=20,
                    help="Number of papers to fetch"
                )
            
            if st.button("🔎 Search & Load", type="primary", use_container_width=True):
                if search_query:
                    with st.spinner(f"Searching {search_source} for papers..."):
                        try:
                            # Use the appropriate parser
                            if search_source == "ArXiv":
                                df = parsers.parse_arxiv_search(search_query, max_results)
                            else:
                                df = parsers.parse_pubmed_search(search_query, max_results)
                            
                            st.success(f"Found {len(df)} papers from {search_source}!")
                            
                            # Validate citations
                            validator = CitationValidator()
                            validated_df, validation_report = validator.validate_citations(df)
                            
                            # Show data quality (should be high for academic sources)
                            quality_score = validation_report["quality_score"]
                            st.success(f"📊 Data Quality Score: {quality_score:.1f}% - Excellent quality from {search_source}")
                            
                            # Display preview
                            st.subheader("Preview (first 5 papers)")
                            preview_df = validated_df[['id', 'title', 'year', 'journal']].head()
                            st.dataframe(preview_df, use_container_width=True)
                            
                            # Save to database
                            with st.spinner("Loading into database..."):
                                db.init_db()
                                stats = db.bulk_insert_citations(validated_df)
                            
                            # Show results
                            if stats['inserted'] > 0:
                                st.success(f"✅ Added {stats['inserted']} new papers!")
                            if stats['updated'] > 0:
                                st.info(f"📝 Updated {stats['updated']} existing papers")
                            if stats['skipped'] > 0:
                                st.warning(f"⚠️ Skipped {stats['skipped']} papers due to errors")
                            
                            st.session_state.citations_loaded = True
                            st.rerun()
                            
                        except Exception as e:
                            st.error(f"Error searching {search_source}: {str(e)}")
                            if "llama-index-readers-papers" in str(e):
                                st.info("💡 Tip: Make sure llama-index-readers-papers is installed")
                else:
                    st.warning("Please enter a search query")
        else:
            st.warning("""
            ⚠️ Academic database search is not available.
            
            To enable this feature, install the required package:
            ```
            pip install llama-index-readers-papers
            ```
            """)

    # Option to skip if citations already loaded
    corpus_stats = db.get_corpus_stats()
    if corpus_stats["total_citations"] > 0:
        st.divider()
        st.info(f"ℹ️ Database contains {corpus_stats['total_citations']} citations (no limits - all will be screened)")

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
            # Get total count first
            total_count = database.query(db.Citation).count()
            
            # Only limit if we have a very large corpus (>1000) for UI performance
            if total_count > 1000:
                st.info(f"Showing first 1000 of {total_count} citations for browsing. All citations will be included in screening.")
                citations_query = database.query(db.Citation).limit(1000).all()
            else:
                citations_query = database.query(db.Citation).all()

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
    
    # Check abstract coverage before proceeding
    stats = db.get_corpus_stats()
    with db.get_db() as database:
        # Count citations with abstracts
        citations_with_abstract = database.query(db.Citation).filter(
            db.Citation.abstract.isnot(None),
            db.Citation.abstract != '',
            db.func.length(db.Citation.abstract) > 50
        ).count()
        
        abstract_coverage = (citations_with_abstract / stats["total_citations"] * 100) if stats["total_citations"] > 0 else 0
        
        # Show warning if abstract coverage is low
        if abstract_coverage < 80:
            st.warning(f"""
            ⚠️ **Low Abstract Coverage**: Only {citations_with_abstract}/{stats["total_citations"]} citations ({abstract_coverage:.1f}%) have sufficient abstracts.
            
            **Impact**: AI screening accuracy will be significantly reduced for citations without abstracts.
            Consider uploading a more complete dataset for better results.
            """)
        else:
            st.success(f"✅ Good abstract coverage: {abstract_coverage:.1f}% of citations have abstracts")

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
        col_adv1, col_adv2 = st.columns(2)
        
        with col_adv1:
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
        
        with col_adv2:
            search_mode = st.selectbox(
                "Search Mode",
                options=["fulltext", "semantic"],
                index=0,
                key='search_mode',
                help="Choose between keyword-based full-text search or AI-powered semantic search"
            )
            
            if search_mode == "semantic":
                st.info("""
                **Semantic Search Mode:**
                - Uses OpenAI embeddings to find conceptually similar citations
                - Finds related papers even with different terminology
                - Better for broad concept exploration
                """)
                
                # Check if embeddings are available
                stats = db.get_corpus_stats()
                if stats['total_citations'] > 0:
                    with db.get_db() as database:
                        embedded_count = database.query(db.Citation).filter(
                            db.Citation.embedding != None
                        ).count()
                    
                    if embedded_count == 0:
                        st.warning("⚠️ No embeddings generated yet. Semantic search will fall back to full-text search.")
                        if st.button("Generate Embeddings"):
                            with st.spinner("Generating embeddings... This may take a few minutes."):
                                embedding_stats = db.generate_citation_embeddings()
                                st.success(f"Generated {embedding_stats['generated']} embeddings!")
                                st.rerun()
                    else:
                        st.success(f"✓ {embedded_count}/{stats['total_citations']} citations have embeddings")
            else:
                st.info("""
                **Full-text Search Mode:**
                - Traditional keyword-based search
                - Fast and precise for specific terms
                - Best for targeted searches
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
            # Capture session state values before processing
            pico_criteria = st.session_state.get('pico_criteria', {})
            inclusion_criteria = st.session_state.get('inclusion_criteria', [])
            exclusion_criteria = st.session_state.get('exclusion_criteria', [])
            use_multi_agent = st.session_state.get('use_multi_agent', False)
            search_mode = st.session_state.get('search_mode', 'fulltext')
            
            # Validate criteria exist
            if not pico_criteria:
                st.error("No PICO criteria found! Please complete the criteria step first.")
                return
            
            # Create a container for progress updates
            progress_container = st.container()
            progress_placeholder = progress_container.empty()
            
            # Show initial progress
            progress_placeholder.info("🚀 Starting screening process...")
            
            try:
                # Define progress callback that works with Streamlit
                def update_progress(message):
                    # Parse message for progress info
                    if "Launch" in message:
                        progress_placeholder.info(f"🚀 {message}")
                    elif "Poll" in message or "progress" in message.lower():
                        progress_placeholder.info(f"⏳ {message}")
                    elif "Complete" in message or "Success" in message:
                        progress_placeholder.success(f"✅ {message}")
                    elif "Error" in message or "Failed" in message:
                        progress_placeholder.error(f"❌ {message}")
                    else:
                        progress_placeholder.info(f"🔄 {message}")
                
                # Show screening mode
                mode = "multi-agent" if use_multi_agent else "single-agent"
                progress_placeholder.info(f"Starting {mode} screening process...")
                
                # Run screening directly (no threading)
                with st.spinner("Screening in progress... This may take several minutes."):
                    results = run_systematic_screening(
                        pico_criteria,
                        inclusion_criteria,
                        exclusion_criteria,
                        stats['total_citations'],
                        MCP_URL,
                        callback=update_progress,
                        use_multi_agent=use_multi_agent,
                        search_mode=search_mode
                    )
                
                # Validate results
                if not results or "included_citations" not in results:
                    raise ValueError("Invalid screening results received")
                
                # Save results to session state
                st.session_state.screening_results = results
                st.session_state.screening_timestamp = datetime.now()
                
                # Show success message
                progress_placeholder.success(f"✅ Screening completed! Found {results['statistics']['included']} relevant citations.")
                time.sleep(2)  # Brief pause to show success message
                
                # Navigate to results
                st.session_state.current_step = "results"
                st.rerun()
                
            except Exception as e:
                error_msg = str(e)
                if "API" in error_msg or "key" in error_msg.lower():
                    progress_placeholder.error("❌ API Key Error: Please check your OpenAI API key in secrets")
                elif "connection" in error_msg.lower():
                    progress_placeholder.error("❌ Connection Error: Please check MCP server is running on port 8001")
                else:
                    progress_placeholder.error(f"❌ Screening failed: {error_msg}")
                
                with st.expander("Error Details"):
                    st.exception(e)


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

        # Export section with PubMed formats
        st.markdown("### Export Included Citations")
        
        # Citation selection
        export_set = st.radio(
            "Select citations to export:",
            ["Included citations only", "Excluded citations only", "All citations"],
            index=0
        )
        
        # PubMed export formats
        export_format = st.selectbox(
            "Export format:",
            [
                "PubMed Summary (text)",
                "PubMed Format",
                "PMID List",
                "Abstract (text)",
                "CSV",
                "Citation Manager (.nbib)",
                "JSON (Full screening data)",
                "PRISMA Flow Data"
            ],
            help="Choose from native PubMed export formats or comprehensive screening data"
        )
        
        # Prepare citations for export based on selection
        if export_set == "Included citations only":
            citations_to_export = []
            for result in results["results"]:
                if result["decision"] == "include":
                    # Fetch full citation details
                    citation = db.fetch_citation(result["citation_id"])
                    if citation:
                        citations_to_export.append(citation)
        elif export_set == "Excluded citations only":
            citations_to_export = []
            for result in results["results"]:
                if result["decision"] == "exclude":
                    citation = db.fetch_citation(result["citation_id"])
                    if citation:
                        citations_to_export.append(citation)
        else:  # All citations
            citations_to_export = []
            for result in results["results"]:
                citation = db.fetch_citation(result["citation_id"])
                if citation:
                    citations_to_export.append(citation)
        
        # Generate export based on format
        if export_format == "JSON (Full screening data)":
            # Comprehensive export data
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
            content = json.dumps(export_data, indent=2)
            filename = f"screening_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            mime_type = "application/json"
            
        elif export_format == "PRISMA Flow Data":
            # PRISMA flow diagram data
            prisma_data = {
                "identification": stats["total_screened"],
                "screening": stats["total_screened"],
                "included": stats["included"],
                "excluded": stats["excluded"],
                "exclusion_reasons": {}
            }
            
            # Count exclusion reasons
            for result in results["results"]:
                if result["decision"] == "exclude":
                    reason = result.get("reason", "Not specified")
                    if reason not in prisma_data["exclusion_reasons"]:
                        prisma_data["exclusion_reasons"][reason] = 0
                    prisma_data["exclusion_reasons"][reason] += 1
            
            content = json.dumps(prisma_data, indent=2)
            filename = f"prisma_flow_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            mime_type = "application/json"
            
        else:
            # PubMed format exports
            format_map = {
                "PubMed Summary (text)": "summary",
                "PubMed Format": "pubmed",
                "PMID List": "pmid",
                "Abstract (text)": "abstract",
                "CSV": "csv",
                "Citation Manager (.nbib)": "nbib"
            }
            
            format_key = format_map.get(export_format)
            if format_key and citations_to_export:
                content, filename, mime_type = export_citations(citations_to_export, format_key)
            else:
                st.warning("No citations available for export in the selected set.")
                content = ""
                filename = "empty_export.txt"
                mime_type = "text/plain"
        
        # Download button
        if content:
            st.download_button(
                label=f"📥 Download {export_format}",
                data=content,
                file_name=filename,
                mime=mime_type,
                use_container_width=True
            )
            
            # Show preview for text formats
            if mime_type == "text/plain" and len(content) < 5000:
                with st.expander("Preview export content"):
                    st.text(content[:2000] + "..." if len(content) > 2000 else content)
        
        # Additional export info
        st.divider()
        st.info(f"""
        **Export Summary:**
        - Format: {export_format}
        - Citations: {len(citations_to_export)} {export_set.lower()}
        - Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        
        **PubMed Format Notes:**
        - Summary (text): NLM citation style, suitable for bibliographies
        - PubMed Format: MEDLINE format with full metadata
        - PMID List: Simple list of PubMed IDs for batch operations
        - Abstract (text): Full abstracts with citation details
        - CSV: Spreadsheet-compatible format with all fields
        - .nbib: Compatible with EndNote, Mendeley, Zotero, etc.
        """)

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