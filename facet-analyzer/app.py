"""
Facet Architecture Analyzer - v3.1 (CORREGIDO)
Herramienta de análisis de navegación facetada
- Demanda Interna: Uso de filtros por usuarios de PcComponentes
- Demanda de Mercado: Volumen de búsquedas (Keyword Research)
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
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

# CSS - CONTRASTE MEJORADO
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
    
    /* Cards de facetas - ALTO CONTRASTE */
    .facet-card {
        background: #16213e;
        border-radius: 16px;
        padding: 1.5rem;
        border: 1px solid #1f4068;
        margin-bottom: 1rem;
        box-shadow: 0 4px 15px rgba(0,0,0,0.4);
    }
    .facet-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 1rem;
    }
    .facet-name {
        font-size: 1.3rem;
        font-weight: 700;
        color: #ffffff;
    }
    .facet-badge {
        padding: 0.4rem 1rem;
        border-radius: 20px;
        font-size: 0.9rem;
        font-weight: 700;
        color: #000;
    }
    .facet-desc {
        color: #e0e0e0;
        font-size: 0.95rem;
        margin-bottom: 1rem;
        line-height: 1.6;
    }
    .facet-values-container {
        display: flex;
        flex-wrap: wrap;
        gap: 0.5rem;
        margin: 1rem 0;
    }
    .facet-value-tag {
        padding: 0.5rem 1rem;
        border-radius: 8px;
        font-size: 0.9rem;
        font-weight: 600;
        color: #ffffff;
        background: #2d4a7c;
        border: 1px solid #3d5a8c;
    }
    .facet-value-tag.highlight {
        background: #0ea5e9;
        border-color: #38bdf8;
    }
    .facet-url-box {
        background: #0f172a;
        padding: 0.8rem 1rem;
        border-radius: 8px;
        margin-top: 1rem;
        border-left: 3px solid #00d9ff;
    }
    .facet-url-label {
        color: #94a3b8;
        font-size: 0.8rem;
        margin-bottom: 0.3rem;
    }
    .facet-url-value {
        color: #00d9ff;
        font-family: 'Consolas', 'Monaco', monospace;
        font-size: 0.95rem;
    }
    .facet-content-box {
        color: #cbd5e1;
        font-size: 0.9rem;
        margin-top: 0.8rem;
        padding-left: 0.5rem;
        border-left: 2px solid #475569;
    }
    
    /* Niveles */
    .level-box {
        text-align: center;
        padding: 1.5rem;
        border-radius: 16px;
        background: #16213e;
        border: 3px solid;
    }
    .level-title {
        font-size: 1.5rem;
        font-weight: 800;
        margin-bottom: 0.3rem;
    }
    .level-pattern {
        font-family: 'Consolas', monospace;
        font-size: 0.85rem;
        color: #94a3b8;
        margin: 0.5rem 0;
    }
    .level-pct {
        font-size: 2.2rem;
        font-weight: 800;
    }
    .level-desc {
        color: #cbd5e1;
        font-size: 0.85rem;
        margin: 0.5rem 0;
    }
    .level-action {
        display: inline-block;
        padding: 0.4rem 1rem;
        border-radius: 8px;
        font-weight: 700;
        font-size: 0.85rem;
        margin-top: 0.5rem;
    }
    
    /* Noindex cards */
    .noindex-box {
        background: #1e1e2e;
        border-radius: 12px;
        padding: 1.2rem;
        border-left: 4px solid #ef4444;
    }
    .noindex-title {
        color: #ef4444;
        font-weight: 700;
        font-size: 1.1rem;
        margin-bottom: 0.8rem;
    }
    .noindex-item {
        color: #e2e8f0;
        font-family: 'Consolas', monospace;
        font-size: 0.9rem;
        padding: 0.3rem 0;
    }
    .noindex-action {
        color: #94a3b8;
        font-size: 0.85rem;
        margin-top: 1rem;
        padding-top: 0.8rem;
        border-top: 1px solid #334155;
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
        'insights_data': None
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


# ═══════════════════════════════════════════════════════════════════════════════
# SIDEBAR - RESTAURADO COMPLETO
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
            
            **Demanda Interna:** Export de Adobe Analytics con formato `faceta:valor,sesiones`
            """)
        
        # Datos SEO
        st.markdown("### 📊 Datos SEO")
        top_query_file = st.file_uploader("📊 Top Query por URL", type=['csv'], key='tq')
        gsc_queries_file = st.file_uploader("🔍 GSC Consultas", type=['csv'], key='gscq')
        gsc_pages_file = st.file_uploader("📄 GSC Páginas", type=['csv'], key='gscp')
        keyword_file = st.file_uploader("🔑 Keyword Research", type=['csv', 'tsv'], key='kw')
        
        # Demanda Interna
        st.markdown("### 🏠 Demanda Interna (Adobe)")
        st.caption("*Search Filters* - Qué facetas usan los usuarios:")
        filter_sf_all = st.file_uploader("Search Filters - Todo tráfico", type=['csv'], key='sf_all')
        filter_sf_seo = st.file_uploader("Search Filters - Solo SEO", type=['csv'], key='sf_seo')
        
        st.caption("*Page Full URL* - Arquitectura de URLs:")
        filter_url_all = st.file_uploader("Page Full URL - Todo tráfico", type=['csv'], key='url_all')
        filter_url_seo = st.file_uploader("Page Full URL - Solo SEO", type=['csv'], key='url_seo')
        
        st.markdown("---")
        
        # API Keys - RESTAURADO
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
            st.session_state.insights_data = None
            st.success(f"✅ Cargados: {', '.join(loaded)}")
        
        if errors:
            for error in errors:
                st.error(f"❌ {error}")


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


# ═══════════════════════════════════════════════════════════════════════════════
# TAB: RESUMEN
# ═══════════════════════════════════════════════════════════════════════════════

def render_overview_tab():
    """Tab de resumen ejecutivo"""
    st.markdown("### 📊 Resumen Ejecutivo")
    
    if not st.session_state.data_loaded:
        st.info("👈 Carga los datos desde la barra lateral")
        return
    
    if not st.session_state.analysis_complete:
        if st.button("▶️ Ejecutar Análisis", type="primary"):
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
                 delta="Alto" if rate >= 5 else "OK",
                 delta_color="inverse" if rate >= 5 else "normal")
    
    st.markdown("---")
    
    if summary.get('facet_order'):
        st.markdown("### 🎯 Prioridad de Facetas (Demanda Interna)")
        icons = {'size': '📐', 'brand': '🏷️', 'technology': '⚡', 'price': '💰', 'connectivity': '📡', 'use_case': '🎯'}
        
        cols = st.columns(min(5, len(summary['facet_order'])))
        for i, facet in enumerate(summary['facet_order'][:5]):
            with cols[i]:
                st.markdown(f"""
                <div style="text-align:center; padding:1rem; background:#16213e; border-radius:12px;">
                    <div style="font-size:2rem;">{icons.get(facet, '📦')}</div>
                    <div style="font-weight:700; color:#fff; margin-top:0.5rem;">{facet.title()}</div>
                    <div style="color:#888;">#{i+1}</div>
                </div>
                """, unsafe_allow_html=True)
        
        if summary.get('top_facet'):
            st.caption(f"*{summary['top_facet'].title()}* representa el **{summary.get('top_facet_pct', 0):.1f}%** del uso de filtros")
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📈 Distribución por Tipo URL")
        url_df = analyzer.results.url_classification
        if not url_df.empty:
            clicks_col = 'clicks' if 'clicks' in url_df.columns else 'url_total_clicks'
            if clicks_col in url_df.columns:
                dist = url_df.groupby('url_type')[clicks_col].sum().reset_index()
                dist.columns = ['Tipo', 'Clics']
                fig = px.pie(dist, values='Clics', names='Tipo', 
                            color_discrete_sequence=['#00d9ff', '#00ff88', '#ffd93d', '#ff6b6b', '#a855f7'])
                fig.update_layout(height=300, margin=dict(t=20, b=20, l=20, r=20))
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Carga Top Query para ver distribución")
    
    with col2:
        st.markdown("### 🔄 Uso de Facetas (Demanda Interna)")
        usage_df = analyzer.results.facet_usage
        if not usage_df.empty:
            fig = px.bar(usage_df.head(6), x='facet_type', y='pct_usage',
                        color='pct_usage', color_continuous_scale='Viridis',
                        labels={'facet_type': 'Faceta', 'pct_usage': '% Uso'})
            fig.update_layout(height=300, margin=dict(t=20, b=20, l=20, r=20), showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Carga Search Filters para ver uso")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB: ARQUITECTURA - NIVELES VISUALES
# ═══════════════════════════════════════════════════════════════════════════════

def render_architecture_tab():
    """Tab de Arquitectura de URLs con niveles visuales"""
    st.markdown("### 🏗️ Arquitectura de URLs por Niveles")
    st.caption("Estructura de navegación y reglas de indexación")
    
    if not st.session_state.data_loaded:
        st.info("Carga los datos primero")
        return
    
    processor = st.session_state.processor
    analyzer = st.session_state.analyzer
    category = st.session_state.category
    
    if st.session_state.insights_data is None:
        with st.spinner("Analizando arquitectura..."):
            st.session_state.insights_data = InsightGenerator.generate_all_insights(processor, analyzer)
    
    arch = st.session_state.insights_data.get('architecture', {})
    rec_arch = arch.get('recommended_architecture', {})
    url_struct = rec_arch.get('url_structure', {})
    
    n0_pct = url_struct.get('N0', {}).get('pct', 5)
    n1_pct = url_struct.get('N1', {}).get('pct', 45)
    n2_pct = url_struct.get('N2', {}).get('pct', 35)
    n3_pct = url_struct.get('N3+', {}).get('pct', 15)
    
    # VISUALIZACIÓN DE NIVELES
    st.markdown("#### 📊 Estructura de Niveles de Profundidad")
    
    cols = st.columns(4)
    
    levels = [
        {'name': 'N0', 'pattern': f'/{category}', 'pct': n0_pct, 'color': '#22c55e', 
         'action': 'INDEX', 'action_bg': '#22c55e', 'desc': 'Categoría principal'},
        {'name': 'N1', 'pattern': f'/{category}/{{faceta}}', 'pct': n1_pct, 'color': '#0ea5e9',
         'action': 'INDEX', 'action_bg': '#0ea5e9', 'desc': 'Un atributo'},
        {'name': 'N2', 'pattern': f'/{category}/{{f1}}/{{f2}}', 'pct': n2_pct, 'color': '#eab308',
         'action': 'SELECTIVO', 'action_bg': '#eab308', 'desc': 'Dos atributos'},
        {'name': 'N3+', 'pattern': f'/{category}/{{...}}/{{...}}/{{...}}', 'pct': n3_pct, 'color': '#ef4444',
         'action': 'NOINDEX', 'action_bg': '#ef4444', 'desc': 'Tres o más'}
    ]
    
    for i, lvl in enumerate(levels):
        with cols[i]:
            st.markdown(f"""
            <div class="level-box" style="border-color: {lvl['color']};">
                <div class="level-title" style="color: {lvl['color']};">{lvl['name']}</div>
                <div class="level-pattern">{lvl['pattern']}</div>
                <div class="level-pct" style="color: {lvl['color']};">{lvl['pct']:.0f}%</div>
                <div class="level-desc">{lvl['desc']}</div>
                <span class="level-action" style="background: {lvl['action_bg']}; color: #000;">{lvl['action']}</span>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("#### 📈 Distribución del Tráfico")
        
        level_df = pd.DataFrame({
            'Nivel': ['N0 - Categoría', 'N1 - Un atributo', 'N2 - Dos atributos', 'N3+ - Tres o más'],
            'Porcentaje': [n0_pct, n1_pct, n2_pct, n3_pct],
            'Acción': ['INDEX', 'INDEX', 'SELECTIVO', 'NOINDEX']
        })
        
        fig = px.bar(level_df, x='Nivel', y='Porcentaje', color='Acción',
                    color_discrete_map={'INDEX': '#22c55e', 'SELECTIVO': '#eab308', 'NOINDEX': '#ef4444'})
        fig.update_layout(height=300, xaxis_tickangle=0)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown("#### 📋 Resumen")
        indexable = n0_pct + n1_pct + (n2_pct * 0.3)
        
        st.metric("✅ Tráfico Indexable", f"{indexable:.0f}%")
        st.metric("❌ Tráfico NOINDEX", f"{100-indexable:.0f}%")
        
        st.markdown("""
        **Recomendación:**
        - ✅ N0 y N1: Siempre indexar
        - ⚠️ N2: Solo si hay demanda
        - ❌ N3+: Nunca indexar
        """)
    
    # TABLA DE REGLAS - DATAFRAME NATIVO
    st.markdown("---")
    st.markdown("#### 📑 Reglas de Indexación")
    
    rules_df = pd.DataFrame({
        'Patrón URL': [
            f'/{category}',
            f'/{category}/{{tamaño}}',
            f'/{category}/{{marca}}',
            f'/{category}/{{tecnología}}',
            f'/{category}/{{tamaño}}/{{tech}}',
            f'/{category}/{{tamaño}}/{{marca}}',
            'URLs con 3+ facetas',
            'URLs con ?order=, ?page='
        ],
        'Indexar': ['✅ SÍ', '✅ SÍ', '✅ SÍ', '✅ SÍ', '⚠️ Selectivo', '⚠️ Selectivo', '❌ NO', '❌ NO'],
        'Contenido Mínimo': ['500 palabras + FAQ', '150 palabras + FAQ', '200 palabras', '150 palabras', '80 palabras', '80 palabras', '-', '-'],
        'Condición': [
            'Siempre',
            'Todos los tamaños estándar',
            'Marcas con demanda >50 clics',
            'Tech diferenciadas (no /led, /4k)',
            'Demanda KW >200 ó clics >500',
            'Demanda KW >100 ó clics >500',
            'Canonical → padre N2',
            'Canonical → sin parámetro'
        ]
    })
    
    st.dataframe(rules_df, use_container_width=True, hide_index=True)
    
    # NOINDEX
    st.markdown("---")
    st.markdown("#### ❌ URLs que NO INDEXAR")
    
    cols = st.columns(3)
    
    noindex_items = [
        {
            'title': '3+ ATRIBUTOS',
            'items': ['/55/oled/lg', '/65/samsung/qled', '/32/smart-tv/lg'],
            'action': 'canonical → mejor padre N2'
        },
        {
            'title': 'PARÁMETROS',
            'items': ['?order=price_asc', '?page=2', '?price_from=500'],
            'action': 'canonical → URL sin parámetro'
        },
        {
            'title': 'REDUNDANTES',
            'items': ['/4k (95% productos)', '/hdr', '/led', '/wifi'],
            'action': 'No diferencian, no indexar'
        }
    ]
    
    for i, item in enumerate(noindex_items):
        with cols[i]:
            items_html = ''.join([f'<div class="noindex-item">{x}</div>' for x in item['items']])
            st.markdown(f"""
            <div class="noindex-box">
                <div class="noindex-title">{item['title']}</div>
                {items_html}
                <div class="noindex-action">→ {item['action']}</div>
            </div>
            """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB: NAVEGACIÓN - FACETAS
# ═══════════════════════════════════════════════════════════════════════════════

def render_navigation_tab():
    """Tab de Sistema de Navegación - Facetas"""
    st.markdown("### 🧭 Sistema de Navegación por Facetas")
    st.caption("Ordenadas por Demanda Interna (uso real de usuarios en PcComponentes)")
    
    if not st.session_state.data_loaded:
        st.info("Carga los datos primero")
        return
    
    processor = st.session_state.processor
    analyzer = st.session_state.analyzer
    category = st.session_state.category
    
    if st.session_state.insights_data is None:
        with st.spinner("Generando sistema de navegación..."):
            st.session_state.insights_data = InsightGenerator.generate_all_insights(processor, analyzer)
    
    nav = st.session_state.insights_data.get('navigation_system', {})
    
    if not nav:
        st.warning("⚠️ Carga 'Search Filters' para ver el sistema de navegación")
        return
    
    layer1 = nav.get('layer1_ux', {})
    facets = layer1.get('facets', [])
    
    if not facets:
        st.info("No hay datos de facetas")
        return
    
    # Renderizar en filas de 3
    for row_start in range(0, min(len(facets), 9), 3):
        cols = st.columns(3)
        for i, facet in enumerate(facets[row_start:row_start+3]):
            with cols[i]:
                render_facet_card(facet, category)


def render_facet_card(facet: dict, category: str):
    """Card de faceta con ALTO CONTRASTE"""
    name = facet.get('name', 'Faceta')
    icon = facet.get('icon', '📦')
    color = facet.get('color', '#0ea5e9')
    usage_pct = facet.get('usage_pct', 0)
    description = facet.get('description', '')
    top_values = facet.get('top_values', [])[:6]
    highlighted = facet.get('highlighted_values', [])[:3]
    url_pattern = facet.get('url_pattern', '')
    content = facet.get('content_suggestion', '')
    generates_url = facet.get('generates_url', True)
    noindex_reason = facet.get('noindex_reason')
    
    # Values HTML
    values_html = ""
    for val in top_values:
        is_hl = str(val) in [str(h) for h in highlighted]
        cls = "highlight" if is_hl else ""
        values_html += f'<span class="facet-value-tag {cls}">{val}</span>'
    
    if top_values:
        values_html += '<span style="color:#64748b; font-size:0.8rem; margin-left:0.5rem;">+más</span>'
    
    # URL section
    if generates_url and url_pattern:
        url_html = f'''
        <div class="facet-url-box">
            <div class="facet-url-label">URL:</div>
            <div class="facet-url-value">{url_pattern}</div>
        </div>
        '''
    elif noindex_reason:
        url_html = f'<div style="color:#ef4444; margin-top:1rem;">❌ {noindex_reason}</div>'
    else:
        url_html = ""
    
    # Content
    content_html = f'<div class="facet-content-box">📝 {content}</div>' if content else ""
    
    st.markdown(f"""
    <div class="facet-card">
        <div class="facet-header">
            <div class="facet-name">
                <span style="color:{color}; margin-right:0.5rem;">{icon}</span>{name}
            </div>
            <span class="facet-badge" style="background:{color};">{usage_pct:.1f}% uso</span>
        </div>
        <div class="facet-desc">{description}</div>
        <div class="facet-values-container">{values_html}</div>
        {url_html}
        {content_html}
    </div>
    """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB: DEMANDA - Interna vs Mercado
# ═══════════════════════════════════════════════════════════════════════════════

def render_demand_tab():
    """Tab de comparación Demanda Interna vs Demanda de Mercado"""
    st.markdown("### 📊 Comparativa de Demanda")
    st.caption("Demanda Interna (PcComponentes) vs Demanda de Mercado (Google)")
    
    if not st.session_state.data_loaded:
        st.info("Carga los datos primero")
        return
    
    processor = st.session_state.processor
    
    has_internal = 'filter_usage_all' in processor.data or 'filter_usage_seo' in processor.data
    has_market = 'keyword_research' in processor.data
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 🏠 Demanda Interna")
        st.caption("Uso de filtros por usuarios de PcComponentes")
        
        if has_internal:
            df = processor.data.get('filter_usage_all', processor.data.get('filter_usage_seo'))
            if df is not None and not df.empty:
                grouped = df.groupby('facet_type')['sessions'].sum().reset_index()
                grouped = grouped[~grouped['facet_type'].isin(['total', 'sorting', 'other', 'search filters'])]
                grouped = grouped.sort_values('sessions', ascending=False).head(10)
                
                fig = px.bar(grouped, x='facet_type', y='sessions', color='sessions',
                            color_continuous_scale='Blues', labels={'facet_type': 'Faceta', 'sessions': 'Sesiones'})
                fig.update_layout(height=350, showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
                
                total = df['sessions'].sum()
                st.metric("Total Interacciones", f"{total:,}")
        else:
            st.info("📤 Carga 'Search Filters' para ver demanda interna")
    
    with col2:
        st.markdown("#### 🌐 Demanda de Mercado")
        st.caption("Volumen de búsquedas mensuales (Google)")
        
        if has_market:
            df = processor.data.get('keyword_research')
            if df is not None and not df.empty:
                vol_col = 'volume' if 'volume' in df.columns else None
                kw_col = 'keyword' if 'keyword' in df.columns else df.columns[0]
                
                if vol_col:
                    top = df.nlargest(10, vol_col)[[kw_col, vol_col]]
                    top.columns = ['Keyword', 'Volumen']
                    
                    fig = px.bar(top, x='Keyword', y='Volumen', color='Volumen',
                                color_continuous_scale='Greens')
                    fig.update_layout(height=350, showlegend=False, xaxis_tickangle=-45)
                    st.plotly_chart(fig, use_container_width=True)
                    
                    st.metric("Volumen Total", f"{df[vol_col].sum():,}")
        else:
            st.info("📤 Carga 'Keyword Research' para ver demanda de mercado")
    
    # Insights cruzados
    if has_internal and has_market:
        st.markdown("---")
        st.markdown("#### 💡 Oportunidades")
        st.info("El cruce de demanda interna + mercado identifica facetas con potencial SEO no explotado")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB: CANIBALIZACIÓN
# ═══════════════════════════════════════════════════════════════════════════════

def render_cannibalization_tab():
    """Tab de canibalización"""
    st.markdown("### 🔴 Análisis de Canibalización")
    st.caption("Artículos rankeando para queries que deberían llevar a filtros")
    
    if not st.session_state.analysis_complete:
        st.info("Ejecuta el análisis primero en la pestaña Resumen")
        return
    
    analyzer = st.session_state.analyzer
    cannib = analyzer.results.cannibalization
    
    if cannib.empty:
        st.success("✅ No se detectó canibalización significativa")
        return
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Casos Detectados", len(cannib))
    with col2:
        st.metric("Clics Afectados", f"{cannib['impact_score'].sum():,.0f}")
    with col3:
        high = len(cannib[cannib['impact_score'] > 50])
        st.metric("Alto Impacto (>50 clics)", high)
    
    st.markdown("---")
    
    display = cannib[['top_query', 'impact_score', 'url', 'suggested_filter']].copy()
    display.columns = ['Query Transaccional', 'Clics/mes', 'Artículo Actual', 'Filtro Sugerido']
    display['Artículo Actual'] = display['Artículo Actual'].str.replace('https://www.pccomponentes.com/', '/', regex=False)
    display = display.sort_values('Clics/mes', ascending=False)
    
    st.dataframe(display.head(20), use_container_width=True, hide_index=True)
    
    with st.expander("ℹ️ ¿Qué es la canibalización?"):
        st.markdown("""
        **Canibalización** ocurre cuando un artículo informativo (guía, comparativa) rankea 
        para una query transaccional que debería llevar a un filtro de categoría.
        
        **Solución:** Crear/optimizar el filtro y ajustar el TITLE del artículo.
        """)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB: INSIGHTS
# ═══════════════════════════════════════════════════════════════════════════════

def render_insights_tab():
    """Tab de Insights"""
    st.markdown("### 💡 Insights Automáticos")
    st.caption("Hallazgos clave detectados del análisis de datos")
    
    if not st.session_state.data_loaded:
        st.info("Carga los datos primero")
        return
    
    processor = st.session_state.processor
    analyzer = st.session_state.analyzer
    
    if st.session_state.insights_data is None:
        with st.spinner("Generando insights..."):
            st.session_state.insights_data = InsightGenerator.generate_all_insights(processor, analyzer)
    
    insights = st.session_state.insights_data.get('insights', [])
    metrics = st.session_state.insights_data.get('metrics', {})
    sources = st.session_state.insights_data.get('data_sources', [])
    
    # Fuentes
    st.markdown("#### 📂 Fuentes Cargadas")
    if sources:
        cols = st.columns(min(len(sources), 4))
        for i, s in enumerate(sources):
            cols[i % 4].success(f"✅ {s}")
    else:
        st.warning("No hay datos cargados")
        return
    
    st.markdown("---")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Interacciones Internas", f"{metrics.get('total_internal_sessions', 0):,}")
    with col2:
        st.metric("Ratio SEO", f"{metrics.get('seo_ratio', 0):.1f}%")
    with col3:
        st.metric("URLs GSC", f"{metrics.get('total_urls', 0):,}")
    with col4:
        st.metric("Insights", len(insights))
    
    st.markdown("---")
    
    if insights:
        high = [i for i in insights if i.get('priority') == 'HIGH']
        medium = [i for i in insights if i.get('priority') == 'MEDIUM']
        low = [i for i in insights if i.get('priority') == 'LOW']
        
        if high:
            st.markdown("#### 🔴 Prioridad Alta")
            for ins in high:
                with st.expander(f"⚠️ {ins.get('title')}", expanded=True):
                    st.markdown(f"**{ins.get('description', '')}**")
                    if ins.get('action'):
                        st.info(f"💡 Acción: {ins.get('action')}")
        
        if medium:
            st.markdown("#### 🟡 Prioridad Media")
            for ins in medium:
                with st.expander(f"📌 {ins.get('title')}"):
                    st.markdown(ins.get('description', ''))
                    if ins.get('action'):
                        st.info(f"💡 {ins.get('action')}")
        
        if low:
            st.markdown("#### 🟢 Información")
            for ins in low[:5]:
                with st.expander(f"ℹ️ {ins.get('title')}"):
                    st.markdown(ins.get('description', ''))
    else:
        st.info("Carga más fuentes de datos para generar insights")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB: RECOMENDACIONES - RESTAURADA
# ═══════════════════════════════════════════════════════════════════════════════

def render_recommendations_tab():
    """Tab de recomendaciones priorizadas"""
    st.markdown("### 🚀 Recomendaciones Priorizadas")
    st.caption("Acciones concretas ordenadas por impacto")
    
    if not st.session_state.analysis_complete:
        st.info("Ejecuta el análisis primero en la pestaña Resumen")
        return
    
    analyzer = st.session_state.analyzer
    recs = analyzer.results.recommendations
    
    if not recs:
        st.info("No hay recomendaciones disponibles")
        return
    
    priority_labels = {
        0: ("🏆 Arquitectura", "#00d9ff"),
        1: ("🔴 Canibalización", "#ff6b6b"),
        2: ("🟡 Gaps Demanda", "#ffd93d"),
        3: ("🔵 Gap Interno/Externo", "#4ecdc4"),
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


# ═══════════════════════════════════════════════════════════════════════════════
# TAB: EXPORTAR
# ═══════════════════════════════════════════════════════════════════════════════

def render_export_tab():
    """Tab de exportación"""
    st.markdown("### 📥 Exportar Resultados")
    
    if not st.session_state.analysis_complete and not st.session_state.insights_data:
        st.info("Ejecuta el análisis primero")
        return
    
    analyzer = st.session_state.analyzer
    category = st.session_state.category
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 📄 Datos CSV")
        
        if analyzer and not analyzer.results.cannibalization.empty:
            csv = analyzer.results.cannibalization.to_csv(index=False)
            st.download_button("📥 Canibalización", csv, "canibalizacion.csv", "text/csv")
        
        if analyzer and not analyzer.results.gaps.empty:
            csv = analyzer.results.gaps.to_csv(index=False)
            st.download_button("📥 Gaps de Demanda", csv, "gaps.csv", "text/csv")
        
        if analyzer and not analyzer.results.facet_usage.empty:
            csv = analyzer.results.facet_usage.to_csv(index=False)
            st.download_button("📥 Uso Facetas", csv, "facetas.csv", "text/csv")
        
        if analyzer and not analyzer.results.ux_seo_matrix.empty:
            csv = analyzer.results.ux_seo_matrix.to_csv(index=False)
            st.download_button("📥 Matriz Demanda", csv, "matriz_demanda.csv", "text/csv")
    
    with col2:
        st.markdown("#### 📊 Reportes HTML")
        
        if st.session_state.insights_data:
            report = ReportGenerator(category, st.session_state.insights_data)
            
            html = report.generate_executive_summary()
            st.download_button("📋 Resumen Ejecutivo", html, f"resumen-{category}.html", "text/html")
            
            html = report.generate_architecture_report()
            st.download_button("🏗️ Arquitectura", html, f"arquitectura-{category}.html", "text/html")
            
            html = report.generate_market_share_report()
            st.download_button("🏆 Market Share", html, f"market-share-{category}.html", "text/html")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    init_session_state()
    
    st.markdown('<h1 class="main-header">🏗️ Facet Architecture Analyzer</h1>', unsafe_allow_html=True)
    st.markdown('<p style="text-align:center; color:#888;">Demanda Interna (PcComponentes) + Demanda de Mercado (Google)</p>', unsafe_allow_html=True)
    
    render_sidebar()
    
    tabs = st.tabs([
        "📊 Resumen",
        "🏗️ Arquitectura",
        "🧭 Navegación",
        "📈 Demanda",
        "🔴 Canibalización",
        "💡 Insights",
        "🚀 Recomendaciones",
        "📥 Exportar"
    ])
    
    with tabs[0]:
        render_overview_tab()
    with tabs[1]:
        render_architecture_tab()
    with tabs[2]:
        render_navigation_tab()
    with tabs[3]:
        render_demand_tab()
    with tabs[4]:
        render_cannibalization_tab()
    with tabs[5]:
        render_insights_tab()
    with tabs[6]:
        render_recommendations_tab()
    with tabs[7]:
        render_export_tab()


if __name__ == "__main__":
    main()
