"""
Facet Architecture Analyzer - CORREGIDO v2
Herramienta de análisis UX + SEO para navegación facetada
Con visualización de Sistema de Navegación de dos capas
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
from io import BytesIO, StringIO
from datetime import datetime

from utils import DataProcessor, FacetAnalyzer, IndexationAnalyzer, LLMValidator, AnalysisResults, InsightGenerator, ReportGenerator

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN
# ═══════════════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="Facet Architecture Analyzer",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personalizado
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        background: linear-gradient(90deg, #00d9ff, #00ff88);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    .metric-card {
        background: linear-gradient(135deg, rgba(0,217,255,0.1), rgba(0,255,136,0.1));
        border-radius: 10px;
        padding: 1rem;
        border: 1px solid rgba(0,217,255,0.2);
    }
    .success-box {
        background: rgba(0, 255, 136, 0.1);
        border: 1px solid rgba(0, 255, 136, 0.3);
        border-radius: 10px;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    .warning-box {
        background: rgba(255, 217, 61, 0.1);
        border: 1px solid rgba(255, 217, 61, 0.3);
        border-radius: 10px;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    .error-box {
        background: rgba(255, 107, 107, 0.1);
        border: 1px solid rgba(255, 107, 107, 0.3);
        border-radius: 10px;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 10px 20px;
    }
    
    /* Estilos para las cards de facetas */
    .facet-card {
        background: #1a1a2e;
        border-radius: 12px;
        padding: 1.2rem;
        border: 1px solid rgba(255,255,255,0.1);
        margin-bottom: 1rem;
    }
    .facet-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 0.8rem;
    }
    .facet-title {
        font-size: 1.1rem;
        font-weight: 600;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    .facet-badge {
        padding: 0.2rem 0.6rem;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    .facet-desc {
        color: #a0a0b0;
        font-size: 0.85rem;
        margin-bottom: 0.8rem;
    }
    .facet-values {
        display: flex;
        flex-wrap: wrap;
        gap: 0.4rem;
        margin-bottom: 0.8rem;
    }
    .facet-value {
        padding: 0.3rem 0.6rem;
        border-radius: 6px;
        font-size: 0.8rem;
        background: rgba(255,255,255,0.1);
    }
    .facet-value.highlighted {
        background: rgba(0,217,255,0.3);
        border: 1px solid rgba(0,217,255,0.5);
    }
    .facet-url {
        font-family: monospace;
        font-size: 0.8rem;
        color: #00d9ff;
        margin-top: 0.5rem;
    }
    .facet-content {
        font-size: 0.8rem;
        color: #888;
    }
    
    /* Estilos para tabla de indexación */
    .index-table {
        width: 100%;
        border-collapse: collapse;
    }
    .index-table th {
        background: rgba(0,217,255,0.1);
        color: #00d9ff;
        padding: 0.8rem;
        text-align: left;
        font-size: 0.8rem;
        text-transform: uppercase;
        border-bottom: 1px solid rgba(255,255,255,0.1);
    }
    .index-table td {
        padding: 0.8rem;
        border-bottom: 1px solid rgba(255,255,255,0.05);
    }
    .index-yes {
        color: #00ff88;
        font-weight: 600;
    }
    .index-no {
        color: #ff6b6b;
        font-weight: 600;
    }
    
    /* Noindex cards */
    .noindex-section {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 1rem;
        margin-top: 1rem;
    }
    .noindex-card {
        background: #1a1a2e;
        border-radius: 12px;
        padding: 1.2rem;
        border-top: 3px solid #ff6b6b;
    }
    .noindex-title {
        font-weight: 700;
        margin-bottom: 0.5rem;
        color: #ff6b6b;
    }
    .noindex-examples {
        font-family: monospace;
        font-size: 0.8rem;
        color: #888;
    }
    .noindex-action {
        margin-top: 0.8rem;
        font-size: 0.85rem;
        color: #a0a0b0;
    }
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# SESSION STATE
# ═══════════════════════════════════════════════════════════════════════════════

def init_session_state():
    defaults = {
        'processor': None,
        'analyzer': None,
        'data_loaded': False,
        'analysis_complete': False,
        'llm_validator': None,
        'category': 'televisores',
        'insights_data': None,
        'reports_generated': False
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


# ═══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════════════════════════

def render_sidebar():
    with st.sidebar:
        st.markdown("## ⚙️ Configuración")
        
        category = st.text_input(
            "Categoría a analizar",
            value=st.session_state.get('category', 'televisores'),
            help="Keyword de la categoría (ej: televisores, portatiles, moviles)"
        )
        st.session_state.category = category
        
        st.markdown("---")
        st.markdown("## 📁 Cargar Datos")
        
        with st.expander("ℹ️ Formatos esperados"):
            st.markdown("""
            **Top Query (BigQuery):** CSV con columnas `url`, `url_total_clicks`, `top_query`...
            
            **GSC Consultas/Páginas:** Export directo de Search Console (español)
            
            **Keyword Research:** Export de Google Keyword Planner (UTF-16)
            
            **Uso Filtros:** Export de Adobe Analytics con formato `faceta:valor,sesiones`
            """)
        
        top_query_file = st.file_uploader("📊 Top Query por URL", type=['csv'], key='tq')
        gsc_queries_file = st.file_uploader("🔍 GSC Consultas", type=['csv'], key='gscq')
        gsc_pages_file = st.file_uploader("📄 GSC Páginas", type=['csv'], key='gscp')
        keyword_file = st.file_uploader("🔑 Keyword Research", type=['csv', 'tsv'], key='kw')
        
        st.markdown("**📈 Uso de Filtros (Adobe Analytics)**")
        
        st.markdown("*Search Filters* - Qué facetas usan los usuarios:")
        filter_sf_all = st.file_uploader("Search Filters - Todo tráfico", type=['csv'], key='sf_all')
        filter_sf_seo = st.file_uploader("Search Filters - Solo SEO", type=['csv'], key='sf_seo')
        
        st.markdown("*Page Full URL* - Arquitectura de URLs:")
        filter_url_all = st.file_uploader("Page Full URL - Todo tráfico", type=['csv'], key='url_all')
        filter_url_seo = st.file_uploader("Page Full URL - Solo SEO", type=['csv'], key='url_seo')
        
        st.markdown("---")
        
        with st.expander("🔑 API Keys (Validación IA)"):
            anthropic_key = st.text_input("Anthropic API Key", type="password", key='ant_key')
            openai_key = st.text_input("OpenAI API Key", type="password", key='oai_key')
            
            if anthropic_key or openai_key:
                st.session_state.llm_validator = LLMValidator(
                    anthropic_key=anthropic_key or None,
                    openai_key=openai_key or None
                )
                st.success("✅ API Keys configuradas")
        
        st.markdown("---")
        
        if st.button("🚀 Procesar Datos", type="primary", use_container_width=True):
            process_files(
                category=category,
                top_query_file=top_query_file,
                gsc_queries_file=gsc_queries_file,
                gsc_pages_file=gsc_pages_file,
                keyword_file=keyword_file,
                filter_sf_all=filter_sf_all,
                filter_sf_seo=filter_sf_seo,
                filter_url_all=filter_url_all,
                filter_url_seo=filter_url_seo
            )
        
        return category


def process_files(category, **files):
    """Procesa todos los archivos subidos"""
    with st.spinner("Procesando datos..."):
        processor = DataProcessor(category_keyword=category)
        errors = []
        loaded = []
        
        if files.get('top_query_file'):
            try:
                df = pd.read_csv(files['top_query_file'])
                processor.load_top_query(df)
                loaded.append("Top Query")
            except Exception as e:
                errors.append(f"Top Query: {e}")
        
        if files.get('gsc_queries_file'):
            try:
                df = pd.read_csv(files['gsc_queries_file'])
                processor.load_gsc_queries(df)
                loaded.append("GSC Consultas")
            except Exception as e:
                errors.append(f"GSC Consultas: {e}")
        
        if files.get('gsc_pages_file'):
            try:
                df = pd.read_csv(files['gsc_pages_file'])
                processor.load_gsc_pages(df)
                loaded.append("GSC Páginas")
            except Exception as e:
                errors.append(f"GSC Páginas: {e}")
        
        if files.get('keyword_file'):
            try:
                content = files['keyword_file'].read()
                processor.load_keyword_research(content)
                loaded.append("Keyword Research")
            except Exception as e:
                errors.append(f"Keyword Research: {e}")
        
        if files.get('filter_sf_all'):
            try:
                content = files['filter_sf_all'].read().decode('utf-8', errors='ignore')
                processor.load_filter_usage(content, 'all')
                loaded.append("Search Filters (Todo)")
            except Exception as e:
                errors.append(f"Search Filters (Todo): {e}")
        
        if files.get('filter_sf_seo'):
            try:
                content = files['filter_sf_seo'].read().decode('utf-8', errors='ignore')
                processor.load_filter_usage(content, 'seo')
                loaded.append("Search Filters (SEO)")
            except Exception as e:
                errors.append(f"Search Filters (SEO): {e}")
        
        if files.get('filter_url_all'):
            try:
                content = files['filter_url_all'].read().decode('utf-8', errors='ignore')
                processor.load_filter_usage_url(content, 'all')
                loaded.append("Page Full URL (Todo)")
            except Exception as e:
                errors.append(f"Page Full URL (Todo): {e}")
        
        if files.get('filter_url_seo'):
            try:
                content = files['filter_url_seo'].read().decode('utf-8', errors='ignore')
                processor.load_filter_usage_url(content, 'seo')
                loaded.append("Page Full URL (SEO)")
            except Exception as e:
                errors.append(f"Page Full URL (SEO): {e}")
        
        if loaded:
            st.session_state.processor = processor
            st.session_state.analyzer = FacetAnalyzer(processor)
            st.session_state.data_loaded = True
            st.session_state.insights_data = None  # Reset insights
            st.success(f"✅ Cargados: {', '.join(loaded)}")
        
        if errors:
            for error in errors:
                st.error(f"❌ {error}")


# ═══════════════════════════════════════════════════════════════════════════════
# TABS DE ANÁLISIS
# ═══════════════════════════════════════════════════════════════════════════════

def run_analysis():
    """Ejecuta todos los análisis"""
    if not st.session_state.data_loaded:
        return False
    
    analyzer = st.session_state.analyzer
    processor = st.session_state.processor
    
    with st.spinner("Ejecutando análisis completo..."):
        if 'filter_usage_all' in processor.data:
            analyzer.analyze_filter_usage('all')
        elif 'filter_usage_seo' in processor.data:
            analyzer.analyze_filter_usage('seo')
        
        if 'top_query' in processor.data:
            analyzer.analyze_url_distribution(processor.data['top_query'])
            analyzer.detect_cannibalization()
            analyzer.analyze_facet_performance()
        
        analyzer.analyze_ux_seo_matrix()
        
        kw_df = processor.data.get('keyword_research')
        tq_df = processor.data.get('top_query')
        if kw_df is not None:
            analyzer.detect_gaps(kw_df, tq_df)
        
        analyzer.generate_recommendations()
        analyzer.generate_summary()
        
        st.session_state.analysis_complete = True
    
    return True


def render_overview_tab():
    """Tab de resumen ejecutivo"""
    st.markdown("### 📊 Resumen Ejecutivo")
    
    if not st.session_state.data_loaded:
        st.info("👈 Carga los datos desde la barra lateral")
        return
    
    if not st.session_state.analysis_complete:
        if st.button("▶️ Ejecutar Análisis"):
            run_analysis()
            st.rerun()
        return
    
    analyzer = st.session_state.analyzer
    summary = analyzer.results.summary
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("URLs Analizadas", f"{summary.get('total_urls', 0):,}")
    with col2:
        st.metric("Filtros", f"{summary.get('filters_count', 0):,}")
    with col3:
        st.metric("Artículos", f"{summary.get('articles_count', 0):,}")
    with col4:
        rate = summary.get('cannibalization_rate', 0)
        st.metric("Canibalización", f"{rate:.1f}%", 
                 delta="OK" if rate < 5 else "Alto", delta_color="inverse" if rate >= 5 else "normal")
    
    st.markdown("---")
    
    if summary.get('facet_order'):
        st.markdown("### 🎯 Orden Óptimo de Facetas (UX)")
        order_html = " → ".join([f"**{f.title()}**" for f in summary['facet_order']])
        st.markdown(f"Basado en comportamiento de usuarios: {order_html}")
        
        if summary.get('top_facet'):
            st.markdown(f"*{summary['top_facet'].title()}* representa el **{summary['top_facet_pct']:.1f}%** del uso de filtros")
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📈 Distribución por Tipo de URL")
        url_df = analyzer.results.url_classification
        if not url_df.empty:
            clicks_col = 'clicks' if 'clicks' in url_df.columns else 'url_total_clicks'
            dist = url_df.groupby('url_type')[clicks_col].sum().reset_index()
            dist.columns = ['Tipo', 'Clics']
            
            fig = px.pie(dist, values='Clics', names='Tipo', 
                        color_discrete_sequence=['#00d9ff', '#00ff88', '#ffd93d', '#ff6b6b'])
            fig.update_layout(height=300, margin=dict(t=20, b=20, l=20, r=20))
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown("### 🔄 Uso de Facetas (UX)")
        usage_df = analyzer.results.facet_usage
        if not usage_df.empty:
            fig = px.bar(usage_df.head(6), x='facet_type', y='pct_usage',
                        color='pct_usage', color_continuous_scale='Viridis',
                        labels={'facet_type': 'Faceta', 'pct_usage': '% Uso'})
            fig.update_layout(height=300, margin=dict(t=20, b=20, l=20, r=20), showlegend=False)
            st.plotly_chart(fig, use_container_width=True)


def render_navigation_system_tab():
    """Tab de Sistema de Navegación con las dos capas visuales"""
    st.markdown("### 🏗️ Sistema de Navegación (Dos Capas)")
    
    if not st.session_state.data_loaded:
        st.info("Carga los datos primero en la barra lateral")
        return
    
    processor = st.session_state.processor
    analyzer = st.session_state.analyzer
    category = st.session_state.category
    
    # Generar insights si no existen
    if st.session_state.insights_data is None:
        with st.spinner("Generando sistema de navegación..."):
            st.session_state.insights_data = InsightGenerator.generate_all_insights(processor, analyzer)
    
    insights_data = st.session_state.insights_data
    nav_system = insights_data.get('navigation_system', {})
    
    if not nav_system:
        st.warning("⚠️ Carga 'Search Filters' para generar el sistema de navegación")
        return
    
    # ═══════════════════════════════════════════════════════════════════════════
    # CAPA 1: SISTEMA DE NAVEGACIÓN (UX)
    # ═══════════════════════════════════════════════════════════════════════════
    st.markdown("---")
    st.markdown("## 👤 Capa 1: Sistema de Navegación (UX)")
    st.markdown("*Basado en datos de uso interno: cómo navegan realmente los usuarios*")
    
    layer1 = nav_system.get('layer1_ux', {})
    facets = layer1.get('facets', [])
    
    if facets:
        # Primera fila: Tamaño, Marca, Precio (los principales)
        cols = st.columns(3)
        main_facets = facets[:3] if len(facets) >= 3 else facets
        
        for i, facet in enumerate(main_facets):
            with cols[i]:
                render_facet_card(facet, category)
        
        # Segunda fila: Tecnología, Por Uso, Características
        if len(facets) > 3:
            cols2 = st.columns(3)
            secondary_facets = facets[3:6] if len(facets) >= 6 else facets[3:]
            
            for i, facet in enumerate(secondary_facets):
                with cols2[i]:
                    render_facet_card(facet, category, is_secondary=True)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # CAPA 2: REGLAS DE INDEXACIÓN (SEO)
    # ═══════════════════════════════════════════════════════════════════════════
    st.markdown("---")
    st.markdown("## 🔍 Capa 2: Reglas de Indexación (SEO)")
    st.markdown("*Qué URLs indexar y con qué condiciones*")
    
    layer2 = nav_system.get('layer2_seo', {})
    index_rules = layer2.get('index_rules', [])
    noindex_rules = layer2.get('noindex_rules', {})
    
    # Tabla de reglas INDEX
    if index_rules:
        st.markdown("### ✅ URLs a INDEXAR")
        
        # Crear tabla HTML
        table_html = """
        <table style="width: 100%; border-collapse: collapse; background: #1a1a2e; border-radius: 12px; overflow: hidden;">
            <thead>
                <tr style="background: rgba(0,217,255,0.1);">
                    <th style="padding: 1rem; text-align: left; color: #00d9ff; font-size: 0.8rem; text-transform: uppercase;">Tipo de página</th>
                    <th style="padding: 1rem; text-align: left; color: #00d9ff; font-size: 0.8rem; text-transform: uppercase;">Indexar</th>
                    <th style="padding: 1rem; text-align: left; color: #00d9ff; font-size: 0.8rem; text-transform: uppercase;">Contenido mínimo</th>
                    <th style="padding: 1rem; text-align: left; color: #00d9ff; font-size: 0.8rem; text-transform: uppercase;">Condición</th>
                </tr>
            </thead>
            <tbody>
        """
        
        for rule in index_rules:
            index_badge = '<span style="color: #00ff88; font-weight: 600;">✓ INDEX</span>' if rule.get('index') else '<span style="color: #ff6b6b;">✗ NOINDEX</span>'
            table_html += f"""
                <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
                    <td style="padding: 1rem; font-family: monospace; color: #a0a0b0;">{rule.get('pattern', '')}</td>
                    <td style="padding: 1rem;">{index_badge}</td>
                    <td style="padding: 1rem; color: #888;">{rule.get('min_content', '-')}</td>
                    <td style="padding: 1rem; color: #888;">{rule.get('condition', '')}</td>
                </tr>
            """
        
        table_html += "</tbody></table>"
        st.markdown(table_html, unsafe_allow_html=True)
    
    # Reglas NOINDEX
    st.markdown("### ❌ NO INDEXAR")
    
    if noindex_rules:
        cols = st.columns(3)
        
        noindex_items = [
            ('3+_attributes', '3+ ATRIBUTOS', '#ff6b6b'),
            ('parameters', 'PARÁMETROS', '#ffd93d'),
            ('redundant', 'REDUNDANTES', '#ff6b6b')
        ]
        
        for i, (key, title, color) in enumerate(noindex_items):
            if key in noindex_rules:
                rule = noindex_rules[key]
                with cols[i]:
                    examples_html = "<br>".join(rule.get('examples', [])[:6])
                    st.markdown(f"""
                    <div style="background: #1a1a2e; border-radius: 12px; padding: 1.5rem; border-top: 3px solid {color}; height: 100%;">
                        <div style="font-weight: 700; color: {color}; margin-bottom: 0.5rem; font-size: 0.9rem;">{title}</div>
                        <div style="font-family: monospace; font-size: 0.8rem; color: #888; line-height: 1.8;">
                            {examples_html}
                        </div>
                        <div style="margin-top: 1rem; font-size: 0.85rem; color: #a0a0b0; border-top: 1px solid rgba(255,255,255,0.1); padding-top: 0.8rem;">
                            <strong>canonical →</strong> {rule.get('action', '')}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
    
    # Regla de URLs
    url_rule = layer2.get('url_rule', '')
    if url_rule:
        st.markdown("---")
        st.markdown(f"""
        <div style="background: linear-gradient(90deg, rgba(255,217,61,0.1), rgba(255,217,61,0.05)); border: 1px solid rgba(255,217,61,0.3); border-radius: 12px; padding: 1rem; margin-top: 1rem;">
            <strong style="color: #ffd93d;">📋 Regla de URLs:</strong><br>
            <code style="color: #00d9ff;">{url_rule}</code>
        </div>
        """, unsafe_allow_html=True)


def render_facet_card(facet: dict, category: str, is_secondary: bool = False):
    """Renderiza una card de faceta"""
    name = facet.get('name', 'Faceta')
    icon = facet.get('icon', '📦')
    color = facet.get('color', '#888888')
    usage_pct = facet.get('usage_pct', 0)
    description = facet.get('description', '')
    top_values = facet.get('top_values', [])[:8]
    highlighted = facet.get('highlighted_values', [])[:3]
    url_pattern = facet.get('url_pattern', '')
    content_suggestion = facet.get('content_suggestion', '')
    generates_url = facet.get('generates_url', True)
    is_curated = facet.get('is_curated', False)
    noindex_reason = facet.get('noindex_reason')
    
    # Badge
    if is_curated:
        badge_html = '<span style="background: rgba(168,85,247,0.3); color: #a855f7; padding: 0.2rem 0.6rem; border-radius: 12px; font-size: 0.75rem; font-weight: 600;">Curadas</span>'
    elif is_secondary:
        badge_html = '<span style="background: rgba(136,136,136,0.3); color: #888; padding: 0.2rem 0.6rem; border-radius: 12px; font-size: 0.75rem; font-weight: 600;">Secundario</span>'
    else:
        badge_html = f'<span style="background: rgba(0,217,255,0.2); color: {color}; padding: 0.2rem 0.6rem; border-radius: 12px; font-size: 0.75rem; font-weight: 600;">{usage_pct:.1f}% uso</span>'
    
    # Values HTML
    values_html = ""
    for val in top_values:
        is_highlighted = str(val) in [str(h) for h in highlighted]
        style = f"background: rgba(0,217,255,0.3); border: 1px solid {color};" if is_highlighted else "background: rgba(255,255,255,0.1);"
        values_html += f'<span style="{style} padding: 0.3rem 0.6rem; border-radius: 6px; font-size: 0.8rem; margin-right: 0.3rem; margin-bottom: 0.3rem; display: inline-block;">{val}</span>'
    
    if len(top_values) > 0:
        values_html += '<span style="color: #666; font-size: 0.75rem;">+más</span>'
    
    # URL pattern
    url_html = ""
    if generates_url and url_pattern:
        url_html = f'<div style="font-family: monospace; font-size: 0.8rem; color: #00d9ff; margin-top: 0.8rem;"><strong>URL:</strong> {url_pattern}</div>'
    elif noindex_reason:
        url_html = f'<div style="font-size: 0.8rem; color: #ff6b6b; margin-top: 0.8rem;"><strong>URL:</strong> ❌ {noindex_reason}</div>'
    
    # Content suggestion
    content_html = ""
    if content_suggestion:
        content_html = f'<div style="font-size: 0.8rem; color: #888; margin-top: 0.5rem;"><strong>Contenido:</strong> {content_suggestion}</div>'
    
    st.markdown(f"""
    <div style="background: #1a1a2e; border-radius: 12px; padding: 1.2rem; border: 1px solid rgba(255,255,255,0.1); height: 100%;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.8rem;">
            <span style="font-size: 1.1rem; font-weight: 600; display: flex; align-items: center; gap: 0.5rem;">
                <span style="color: {color};">{icon}</span> {name}
            </span>
            {badge_html}
        </div>
        <div style="color: #a0a0b0; font-size: 0.85rem; margin-bottom: 0.8rem;">{description}</div>
        <div style="margin-bottom: 0.8rem;">{values_html}</div>
        {url_html}
        {content_html}
    </div>
    """, unsafe_allow_html=True)


def render_ux_seo_tab():
    """Tab de cruce UX + SEO"""
    st.markdown("### 🔄 Matriz UX + SEO")
    st.markdown("*Cruce entre comportamiento de navegación (UX) y visibilidad en buscadores (SEO)*")
    
    if not st.session_state.analysis_complete:
        st.info("Ejecuta el análisis primero en la pestaña Overview")
        return
    
    analyzer = st.session_state.analyzer
    matrix = analyzer.results.ux_seo_matrix
    
    if matrix.empty:
        st.warning("No hay datos suficientes para el cruce UX + SEO")
        st.info("Necesitas cargar tanto 'Uso de Filtros' como 'Top Query'")
        return
    
    st.markdown("#### Mapa de Oportunidades")
    
    fig = px.scatter(
        matrix[matrix['total_sessions'] > 0],
        x='ux_share',
        y='seo_share',
        size='total_sessions',
        color='ux_seo_gap',
        hover_name='facet_type',
        color_continuous_scale='RdYlGn',
        labels={
            'ux_share': '% Navegación Interna (UX)',
            'seo_share': '% Tráfico SEO',
            'ux_seo_gap': 'Gap UX-SEO'
        }
    )
    
    fig.add_shape(type="line", x0=0, y0=0, x1=50, y1=50,
                  line=dict(color="gray", dash="dash", width=1))
    
    fig.update_layout(height=400)
    st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("""
    **Interpretación:**
    - 🟢 Puntos cerca de la diagonal = Equilibrio UX-SEO
    - 🔴 Puntos arriba de la diagonal = Alta SEO, Baja UX (revisar navegación)
    - 🔵 Puntos debajo de la diagonal = Alta UX, Baja SEO (oportunidad de visibilidad)
    """)
    
    st.markdown("---")
    st.markdown("#### Análisis por Tipo de Faceta")
    
    display_df = matrix[['facet_type', 'total_sessions', 'ux_share', 'seo_clicks', 
                         'seo_share', 'ux_seo_gap', 'opportunity']].copy()
    display_df.columns = ['Faceta', 'Sesiones UX', '% UX', 'Clics SEO', '% SEO', 'Gap', 'Oportunidad']
    
    st.dataframe(display_df, use_container_width=True, hide_index=True)


def render_cannibalization_tab():
    """Tab de canibalización"""
    st.markdown("### 🔴 Análisis de Canibalización")
    
    if not st.session_state.analysis_complete:
        st.info("Ejecuta el análisis primero")
        return
    
    analyzer = st.session_state.analyzer
    cannib = analyzer.results.cannibalization
    
    if cannib.empty:
        st.success("✅ No se detectó canibalización")
        return
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Casos", len(cannib))
    with col2:
        st.metric("Clics Afectados", f"{cannib['impact_score'].sum():.0f}")
    with col3:
        high = len(cannib[cannib['impact_score'] > 10])
        st.metric("Alto Impacto", high)
    
    st.markdown("---")
    
    display = cannib[['top_query', 'impact_score', 'url', 'suggested_filter']].copy()
    display.columns = ['Query Transaccional', 'Clics', 'Artículo Rankeando', 'Filtro Sugerido']
    display['Artículo Rankeando'] = display['Artículo Rankeando'].str.replace(
        'https://www.pccomponentes.com/', '/', regex=False
    )
    
    st.dataframe(display.head(20), use_container_width=True, hide_index=True)


def render_gaps_tab():
    """Tab de gaps de demanda"""
    st.markdown("### 🎯 Gaps de Demanda")
    
    if not st.session_state.analysis_complete:
        st.info("Ejecuta el análisis primero")
        return
    
    analyzer = st.session_state.analyzer
    gaps = analyzer.results.gaps
    
    if gaps.empty:
        st.info("No se detectaron gaps (o no se cargó Keyword Research)")
        return
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Gaps Totales", len(gaps))
    with col2:
        high = len(gaps[gaps['priority'] == 'HIGH'])
        st.metric("Alta Prioridad", high)
    
    priority = st.multiselect("Prioridad", ['HIGH', 'MEDIUM', 'LOW'], default=['HIGH', 'MEDIUM'])
    filtered = gaps[gaps['priority'].isin(priority)]
    
    fig = px.bar(filtered.head(15), x='keyword', y='volume', color='priority',
                color_discrete_map={'HIGH': '#ff6b6b', 'MEDIUM': '#ffd93d', 'LOW': '#4ecdc4'})
    fig.update_layout(xaxis_tickangle=-45, height=400)
    st.plotly_chart(fig, use_container_width=True)
    
    st.dataframe(
        filtered[['keyword', 'volume', 'suggested_filter', 'priority']],
        use_container_width=True,
        hide_index=True
    )


def render_insights_tab():
    """Tab de Insights de Alto Valor"""
    st.markdown("### 💡 Insights Clave")
    st.markdown("*Hallazgos de alto valor combinando múltiples fuentes de datos*")
    
    if not st.session_state.data_loaded:
        st.info("Carga los datos primero en la barra lateral")
        return
    
    processor = st.session_state.processor
    analyzer = st.session_state.analyzer
    category = st.session_state.category
    
    if st.session_state.insights_data is None:
        with st.spinner("Generando insights..."):
            st.session_state.insights_data = InsightGenerator.generate_all_insights(processor, analyzer)
    
    insights_data = st.session_state.insights_data
    insights = insights_data.get('insights', [])
    metrics = insights_data.get('metrics', {})
    data_sources = insights_data.get('data_sources', [])
    
    # Fuentes de datos
    st.markdown("#### 📂 Fuentes de Datos Cargadas")
    
    if data_sources:
        cols = st.columns(len(data_sources))
        source_icons = {
            'Search Filters (Todo)': '🔍',
            'Search Filters (SEO)': '🔎',
            'Page Full URL (Todo)': '🔗',
            'Page Full URL (SEO)': '🌐',
            'Top Query (GSC)': '📊'
        }
        for i, source in enumerate(data_sources):
            icon = source_icons.get(source, '📁')
            cols[i].success(f"{icon} {source}")
    else:
        st.warning("⚠️ No hay datos cargados.")
        return
    
    # Métricas
    st.markdown("---")
    st.markdown("#### 📊 Métricas por Fuente")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_sf = metrics.get('total_internal_sessions', 0)
        if total_sf > 0:
            st.metric("🔍 Search Filters", f"{total_sf:,}" if total_sf < 1000000 else f"{total_sf/1000000:.1f}M")
        else:
            st.metric("🔍 Search Filters", "No cargado")
    
    with col2:
        total_url = metrics.get('total_url_sessions', 0)
        if total_url > 0:
            st.metric("🔗 Page Full URL", f"{total_url:,}" if total_url < 1000000 else f"{total_url/1000000:.1f}M")
        else:
            st.metric("🔗 Page Full URL", "No cargado")
    
    with col3:
        seo_ratio = metrics.get('seo_ratio', 0)
        st.metric("📈 Ratio SEO", f"{seo_ratio:.1f}%")
    
    with col4:
        st.metric("💡 Insights Detectados", len(insights))
    
    st.markdown("---")
    
    # Mostrar insights
    st.markdown("### 🎯 Hallazgos Clave")
    
    if insights:
        high_priority = [i for i in insights if i.get('priority') == 'HIGH']
        medium_priority = [i for i in insights if i.get('priority') == 'MEDIUM']
        low_priority = [i for i in insights if i.get('priority') == 'LOW']
        
        if high_priority:
            st.markdown("#### 🔴 Prioridad Alta")
            for insight in high_priority:
                source_badge = f"*[{insight.get('source', '')}]*" if insight.get('source') else ''
                with st.expander(f"⚠️ {insight.get('title', '')} {source_badge}", expanded=True):
                    st.markdown(f"**Descripción:** {insight.get('description', '')}")
                    if insight.get('action'):
                        st.markdown(f"**Acción recomendada:** {insight.get('action', '')}")
        
        if medium_priority:
            st.markdown("#### 🟡 Prioridad Media")
            for insight in medium_priority:
                source_badge = f"*[{insight.get('source', '')}]*" if insight.get('source') else ''
                with st.expander(f"📌 {insight.get('title', '')} {source_badge}"):
                    st.markdown(f"**Descripción:** {insight.get('description', '')}")
                    if insight.get('action'):
                        st.markdown(f"**Acción recomendada:** {insight.get('action', '')}")
        
        if low_priority:
            st.markdown("#### 🟢 Información")
            for insight in low_priority[:5]:
                source_badge = f"*[{insight.get('source', '')}]*" if insight.get('source') else ''
                with st.expander(f"ℹ️ {insight.get('title', '')} {source_badge}"):
                    st.markdown(f"**Descripción:** {insight.get('description', '')}")
    else:
        st.info("Carga más datos para generar insights automáticos")


def render_recommendations_tab():
    """Tab de recomendaciones"""
    st.markdown("### 🚀 Recomendaciones Priorizadas")
    
    if not st.session_state.analysis_complete:
        st.info("Ejecuta el análisis primero")
        return
    
    analyzer = st.session_state.analyzer
    recs = analyzer.results.recommendations
    
    if not recs:
        st.info("No hay recomendaciones")
        return
    
    priority_labels = {
        0: ("🏆 Arquitectura", "#00d9ff"),
        1: ("🔴 Canibalización", "#ff6b6b"),
        2: ("🟡 Gaps Demanda", "#ffd93d"),
        3: ("🔵 UX/SEO Gap", "#4ecdc4"),
        4: ("⚪ Indexación", "#888")
    }
    
    for priority in sorted(set(r['priority'] for r in recs)):
        label, color = priority_labels.get(priority, (f"Prioridad {priority}", "#888"))
        priority_recs = [r for r in recs if r['priority'] == priority]
        
        st.markdown(f"#### {label}")
        
        for rec in priority_recs[:5]:
            with st.expander(f"{rec['type']}: {rec['action'][:60]}..."):
                st.markdown(f"**Acción:** {rec['action']}")
                st.markdown(f"**Razón:** {rec['reason']}")
                st.markdown(f"**Impacto:** {rec['impact']}")
        
        st.markdown("---")


def render_export_tab():
    """Tab de exportación"""
    st.markdown("### 📥 Exportar Resultados")
    
    if not st.session_state.analysis_complete:
        st.info("Ejecuta el análisis primero")
        return
    
    analyzer = st.session_state.analyzer
    category = st.session_state.category
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### CSV")
        
        if not analyzer.results.cannibalization.empty:
            csv = analyzer.results.cannibalization.to_csv(index=False)
            st.download_button("📥 Descargar Canibalización", csv, "cannibalization.csv", "text/csv")
        
        if not analyzer.results.gaps.empty:
            csv = analyzer.results.gaps.to_csv(index=False)
            st.download_button("📥 Descargar Gaps", csv, "gaps.csv", "text/csv")
        
        if not analyzer.results.ux_seo_matrix.empty:
            csv = analyzer.results.ux_seo_matrix.to_csv(index=False)
            st.download_button("📥 Descargar Matrix UX-SEO", csv, "ux_seo_matrix.csv", "text/csv")
    
    with col2:
        st.markdown("#### HTML Reports")
        
        if st.session_state.insights_data:
            report_gen = ReportGenerator(category, st.session_state.insights_data)
            
            html_arch = report_gen.generate_architecture_report()
            st.download_button("🏗️ Arquitectura de Facetas", html_arch, f"arquitectura-{category}.html", "text/html")
            
            html_market = report_gen.generate_market_share_report()
            st.download_button("🏆 Market Share", html_market, f"market-share-{category}.html", "text/html")
            
            html_summary = report_gen.generate_executive_summary()
            st.download_button("📋 Resumen Ejecutivo", html_summary, f"resumen-{category}.html", "text/html")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    init_session_state()
    
    st.markdown('<h1 class="main-header">🏗️ Facet Architecture Analyzer</h1>', unsafe_allow_html=True)
    st.markdown('<p style="text-align: center; color: #888;">Análisis UX + SEO para navegación facetada</p>', unsafe_allow_html=True)
    
    render_sidebar()
    
    tabs = st.tabs([
        "📊 Overview",
        "🏗️ Sistema Nav",
        "🔄 UX + SEO",
        "🔴 Canibalización",
        "🎯 Gaps",
        "💡 Insights",
        "🚀 Recomendaciones",
        "📥 Exportar"
    ])
    
    with tabs[0]:
        render_overview_tab()
    with tabs[1]:
        render_navigation_system_tab()
    with tabs[2]:
        render_ux_seo_tab()
    with tabs[3]:
        render_cannibalization_tab()
    with tabs[4]:
        render_gaps_tab()
    with tabs[5]:
        render_insights_tab()
    with tabs[6]:
        render_recommendations_tab()
    with tabs[7]:
        render_export_tab()


if __name__ == "__main__":
    main()
