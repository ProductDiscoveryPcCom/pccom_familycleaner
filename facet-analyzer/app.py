"""
Facet Architecture Analyzer - v6
100% Componentes nativos Streamlit (sin HTML problemático)
Validación dual en dos fases
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
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


def init_session_state():
    defaults = {
        'processor': None,
        'analyzer': None,
        'data_loaded': False,
        'analysis_complete': False,
        'llm_validator': None,
        'category': 'televisores',
        'insights_data': None,
        'validation_results': None
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


# ═══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════════════════════════

def render_sidebar():
    with st.sidebar:
        st.header("⚙️ Configuración")
        
        category = st.text_input(
            "Slug de Categoría", 
            value=st.session_state.get('category', 'televisores'),
            help="Slug de la URL de categoría (ej: 'televisores', 'smartphone-moviles', 'portatiles'). Se usa para clasificar URLs transaccionales (/{slug}/...) vs informacionales (blog)."
        )
        st.session_state.category = category
        
        st.divider()
        st.subheader("📁 Datos SEO")
        top_query_file = st.file_uploader("Top Query (BigQuery)", type=['csv'], key='tq')
        gsc_queries_file = st.file_uploader("GSC Consultas", type=['csv'], key='gscq')
        gsc_pages_file = st.file_uploader("GSC Páginas", type=['csv'], key='gscp')
        keyword_file = st.file_uploader("Keyword Research", type=['csv', 'tsv'], key='kw')
        
        st.subheader("🏠 Demanda Interna")
        filter_sf_all = st.file_uploader("Search Filters - Todo", type=['csv'], key='sf_all')
        filter_sf_seo = st.file_uploader("Search Filters - SEO", type=['csv'], key='sf_seo')
        filter_url_all = st.file_uploader("Page Full URL - Todo", type=['csv'], key='url_all')
        filter_url_seo = st.file_uploader("Page Full URL - SEO", type=['csv'], key='url_seo')
        
        st.subheader("🔍 Auditoría Técnica (Opcional)")
        screaming_frog_file = st.file_uploader(
            "Screaming Frog - Internal HTML", 
            type=['csv'], 
            key='sf_crawl',
            help="Export con integración GSC. Incluir extracción personalizada de productos si es posible."
        )
        if screaming_frog_file:
            st.success("✅ Auditoría técnica habilitada")
        
        st.divider()
        
        with st.expander("🔑 Validación Dual IA (2 Fases)"):
            st.caption("Fase 1: Análisis independiente | Fase 2: Revisión cruzada")
            anthropic_key = st.text_input("Anthropic API Key", type="password", key='ant_key')
            openai_key = st.text_input("OpenAI API Key", type="password", key='oai_key')
            
            if anthropic_key or openai_key:
                st.session_state.llm_validator = LLMValidator(
                    anthropic_key=anthropic_key or None,
                    openai_key=openai_key or None
                )
                status = st.session_state.llm_validator.get_status()
                if status['dual_validation_available']:
                    st.success("✅ Validación dual activa")
                elif status['anthropic_configured']:
                    st.info("Claude configurado")
                elif status['openai_configured']:
                    st.info("GPT configurado")
        
        st.divider()
        
        if st.button("🚀 Procesar", type="primary", use_container_width=True):
            process_files(
                category=category,
                top_query_file=top_query_file,
                gsc_queries_file=gsc_queries_file,
                gsc_pages_file=gsc_pages_file,
                keyword_file=keyword_file,
                filter_sf_all=filter_sf_all,
                filter_sf_seo=filter_sf_seo,
                filter_url_all=filter_url_all,
                filter_url_seo=filter_url_seo,
                screaming_frog_file=screaming_frog_file
            )


def process_files(category, **files):
    with st.spinner("Procesando..."):
        processor = DataProcessor(category_keyword=category)
        loaded = []
        
        if files.get('top_query_file'):
            try:
                df = pd.read_csv(files['top_query_file'])
                processor.load_top_query(df)
                loaded.append("Top Query")
            except Exception as e:
                st.error(f"Top Query: {e}")
        
        if files.get('gsc_queries_file'):
            try:
                df = pd.read_csv(files['gsc_queries_file'])
                processor.load_gsc_queries(df)
                loaded.append("GSC Consultas")
            except Exception as e:
                st.error(f"GSC Consultas: {e}")
        
        if files.get('gsc_pages_file'):
            try:
                df = pd.read_csv(files['gsc_pages_file'])
                processor.load_gsc_pages(df)
                loaded.append("GSC Páginas")
            except Exception as e:
                st.error(f"GSC Páginas: {e}")
        
        if files.get('keyword_file'):
            try:
                content = files['keyword_file'].read()
                processor.load_keyword_research(content)
                loaded.append("Keyword Research")
            except Exception as e:
                st.error(f"Keyword Research: {e}")
        
        for key, name, method in [
            ('filter_sf_all', 'Search Filters', 'load_filter_usage'),
            ('filter_sf_seo', 'Search Filters SEO', 'load_filter_usage'),
            ('filter_url_all', 'Page Full URL', 'load_filter_usage_url'),
            ('filter_url_seo', 'Page Full URL SEO', 'load_filter_usage_url')
        ]:
            if files.get(key):
                try:
                    content = files[key].read().decode('utf-8', errors='ignore')
                    src = 'all' if 'all' in key else 'seo'
                    getattr(processor, method)(content, src)
                    loaded.append(name)
                except Exception as e:
                    st.error(f"{name}: {e}")
        
        # Screaming Frog - Auditoría Técnica (Opcional)
        if files.get('screaming_frog_file'):
            try:
                df = pd.read_csv(files['screaming_frog_file'], low_memory=False)
                processor.load_screaming_frog(df)
                loaded.append("Screaming Frog (Auditoría)")
            except Exception as e:
                st.error(f"Screaming Frog: {e}")
        
        if loaded:
            st.session_state.processor = processor
            st.session_state.analyzer = FacetAnalyzer(processor)
            st.session_state.data_loaded = True
            st.session_state.insights_data = None
            st.session_state.validation_results = None
            st.success(f"✅ {', '.join(loaded)}")


def run_analysis():
    if not st.session_state.data_loaded:
        return False
    
    analyzer = st.session_state.analyzer
    processor = st.session_state.processor
    
    with st.spinner("Analizando..."):
        if 'filter_usage_all' in processor.data:
            analyzer.analyze_filter_usage('all')
        
        if 'top_query' in processor.data:
            analyzer.analyze_url_distribution(processor.data['top_query'])
            analyzer.detect_cannibalization()
            analyzer.analyze_facet_performance()
        
        analyzer.analyze_ux_seo_matrix()
        
        kw_df = processor.data.get('keyword_research')
        if kw_df is not None:
            analyzer.detect_gaps(kw_df, processor.data.get('top_query'))
        
        analyzer.generate_recommendations()
        analyzer.generate_summary()
        st.session_state.analysis_complete = True
        
        st.session_state.insights_data = InsightGenerator.generate_all_insights(processor, analyzer)
    
    # Validación dual si está configurada
    validator = st.session_state.llm_validator
    if validator and validator.is_configured():
        with st.spinner("Ejecutando validación dual (Fase 1 + Fase 2)..."):
            validation = validator.dual_validate(
                {
                    'facet_order': analyzer.results.facet_priority_order,
                    'metrics': analyzer.results.summary,
                    'facet_usage': st.session_state.insights_data.get('facet_usage', {})
                },
                'facet_priority'
            )
            st.session_state.validation_results = validation
    
    return True


# ═══════════════════════════════════════════════════════════════════════════════
# TAB: RESUMEN
# ═══════════════════════════════════════════════════════════════════════════════

def render_overview_tab():
    st.subheader("📊 Resumen Ejecutivo")
    
    if not st.session_state.data_loaded:
        st.info("👈 Carga los datos desde la barra lateral")
        return
    
    if not st.session_state.analysis_complete:
        if st.button("▶️ Ejecutar Análisis", type="primary"):
            run_analysis()
            st.rerun()
        return
    
    analyzer = st.session_state.analyzer
    processor = st.session_state.processor
    summary = analyzer.results.summary
    category = st.session_state.category
    
    # ═══════════════════════════════════════════════════════════════════════════
    # MÉTRICAS CON LEYENDA EXPLICATIVA
    # ═══════════════════════════════════════════════════════════════════════════
    c1, c2, c3, c4 = st.columns(4)
    
    with c1:
        st.metric("URLs Analizadas", f"{summary.get('total_urls', 0):,}")
        st.caption("Total de URLs únicas en Top Query (GSC)")
    
    with c2:
        st.metric("Filtros de Categoría", f"{summary.get('filters_count', 0):,}")
        st.caption("URLs de navegación facetada (/{category}/...)")
    
    with c3:
        st.metric("Artículos/Guías", f"{summary.get('articles_count', 0):,}")
        st.caption("Contenido editorial (comparativas, guías)")
    
    with c4:
        st.metric("Tasa Canibalización", f"{summary.get('cannibalization_rate', 0):.1f}%")
        st.caption("% clics en artículos por queries transaccionales")
    
    st.divider()
    
    # ═══════════════════════════════════════════════════════════════════════════
    # FACETAS CON MÁS USO - DEMANDA REAL (TOTAL + SEO) - GENÉRICO
    # ═══════════════════════════════════════════════════════════════════════════
    if summary.get('facet_order'):
        st.markdown("#### 🎯 Facetas con Más Uso (Demanda Real)")
        st.markdown("Ranking basado en interacciones reales de usuarios. Muestra **tráfico total** y **tráfico SEO** para cada tipo de faceta.")
        
        # Obtener datos de uso total y SEO
        filter_all = processor.data.get('filter_usage_all')
        filter_seo = processor.data.get('filter_usage_seo')
        insights_data = st.session_state.insights_data or {}
        facet_usage = insights_data.get('facet_usage', {})
        
        # Función para asignar icono basado en nombre de faceta
        def get_facet_icon(facet_name: str) -> str:
            facet_lower = facet_name.lower()
            if any(k in facet_lower for k in ['marca', 'brand']):
                return '🏷️'
            if any(k in facet_lower for k in ['precio', 'price']):
                return '💰'
            if any(k in facet_lower for k in ['color', 'cor']):
                return '🎨'
            if any(k in facet_lower for k in ['tamaño', 'talla', 'size', 'pulgadas', 'capacidad']):
                return '📐'
            if any(k in facet_lower for k in ['tecnolog', 'tipo', 'panel']):
                return '⚡'
            if any(k in facet_lower for k in ['estado', 'condition']):
                return '♻️'
            if any(k in facet_lower for k in ['conectiv', 'wifi', 'bluetooth']):
                return '📡'
            if any(k in facet_lower for k in ['memoria', 'ram', 'storage', 'almacenamiento']):
                return '💾'
            if any(k in facet_lower for k in ['sistema', 'os']):
                return '⚙️'
            if any(k in facet_lower for k in ['camara', 'camera']):
                return '📷'
            if any(k in facet_lower for k in ['bateria', 'battery']):
                return '🔋'
            return '📦'
        
        # Mostrar facetas en columnas
        cols = st.columns(min(4, len(summary['facet_order'])))
        
        for i, facet in enumerate(summary['facet_order'][:4]):
            icon = get_facet_icon(facet)
            
            # Obtener tráfico total y SEO
            usage_data = facet_usage.get(facet, {})
            total_sessions = usage_data.get('sessions_all', 0)
            seo_sessions = usage_data.get('sessions_seo', 0)
            
            # Si no hay datos en insights, intentar calcular
            if total_sessions == 0 and filter_all is not None and not filter_all.empty:
                facet_data = filter_all[filter_all['facet_type'] == facet]
                total_sessions = int(facet_data['sessions'].sum()) if not facet_data.empty else 0
            
            if seo_sessions == 0 and filter_seo is not None and not filter_seo.empty:
                facet_data_seo = filter_seo[filter_seo['facet_type'] == facet]
                seo_sessions = int(facet_data_seo['sessions'].sum()) if not facet_data_seo.empty else 0
            
            # Obtener valor ejemplo real del CSV
            example_value = ""
            if filter_all is not None and not filter_all.empty:
                facet_rows = filter_all[filter_all['facet_type'] == facet]
                if not facet_rows.empty:
                    top_val = facet_rows.nlargest(1, 'sessions').iloc[0].get('facet_value', '')
                    if top_val:
                        example_value = str(top_val).lower().replace(' ', '-')
            
            # Construir URL ejemplo dinámicamente
            url_example = f"/{category}/{example_value}" if example_value else f"/{category}/[valor]"
            
            with cols[i]:
                with st.container(border=True):
                    # Número de ranking
                    st.markdown(f"<div style='text-align:center; font-size:2rem; font-weight:700; color:#22d3ee;'>#{i+1}</div>", unsafe_allow_html=True)
                    st.markdown(f"<div style='text-align:center; font-size:0.9rem; color:#94a3b8;'>{icon} {facet.replace('_', ' ').title()}</div>", unsafe_allow_html=True)
                    
                    # Métricas de tráfico
                    st.markdown("---")
                    col_t, col_s = st.columns(2)
                    with col_t:
                        st.metric("Total", f"{total_sessions:,}", label_visibility="visible")
                    with col_s:
                        st.metric("SEO", f"{seo_sessions:,}", label_visibility="visible")
                    
                    # URL ejemplo
                    st.markdown("---")
                    st.caption("**Ejemplo URL:**")
                    st.code(url_example, language=None)
    
    # Validación dual
    if st.session_state.validation_results:
        val = st.session_state.validation_results
        st.divider()
        st.markdown("#### 🤖 Validación Dual IA (2 Fases)")
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Confianza", f"{val.get('confidence', 0)*100:.0f}%")
        c2.metric("Fuentes", ", ".join(val.get('sources_used', [])))
        c3.metric("Dual", "✅ Sí" if val.get('dual_validation') else "❌ No")
        
        if val.get('consensus_points'):
            with st.expander("Ver puntos de consenso"):
                for p in val['consensus_points'][:5]:
                    st.write(f"✅ {p}")
        
        if val.get('consolidated', {}).get('recommendations'):
            with st.expander("Ver recomendaciones validadas"):
                for rec in val['consolidated']['recommendations'][:5]:
                    priority = rec.get('priority', 'MEDIUM')
                    icon = "🔴" if priority == "HIGH" else "🟡" if priority == "MEDIUM" else "🟢"
                    st.write(f"{icon} **Recomendación:** {rec.get('action', '')}")
    
    st.divider()
    
    # ═══════════════════════════════════════════════════════════════════════════
    # GRÁFICOS CON EXPLICACIONES
    # ═══════════════════════════════════════════════════════════════════════════
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 📈 Distribución de Clics por Tipo de URL")
        st.caption("Porcentaje de clics SEO según el tipo de página (datos de Top Query/GSC)")
        
        url_df = analyzer.results.url_classification
        if not url_df.empty:
            clicks_col = 'clicks' if 'clicks' in url_df.columns else 'url_total_clicks'
            if clicks_col in url_df.columns:
                dist = url_df.groupby('url_type')[clicks_col].sum().reset_index()
                dist.columns = ['Tipo', 'Clics']
                total_clicks = dist['Clics'].sum()
                dist['% Clics'] = (dist['Clics'] / total_clicks * 100).round(1)
                
                fig = px.pie(dist, values='Clics', names='Tipo',
                            hover_data=['% Clics'],
                            labels={'Clics': 'Clics totales'})
                fig.update_traces(textposition='inside', textinfo='percent+label')
                fig.update_layout(
                    height=300, 
                    margin=dict(t=10, b=30, l=10, r=10),
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=-0.2,
                        xanchor="center",
                        x=0.5
                    )
                )
                st.plotly_chart(fig, use_container_width=True)
                st.caption(f"**Total:** {total_clicks:,} clics analizados")
    
    with col2:
        st.markdown("#### 🔄 Uso de Facetas")
        st.caption("Porcentaje de interacciones por tipo de filtro (Adobe Analytics: Search Filters)")
        
        usage_df = analyzer.results.facet_usage
        if not usage_df.empty:
            fig = px.bar(usage_df.head(6), x='facet_type', y='pct_usage',
                        labels={'facet_type': 'Faceta', 'pct_usage': '% Uso'})
            fig.update_layout(height=300, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB: ARQUITECTURA
# ═══════════════════════════════════════════════════════════════════════════════

def render_architecture_tab():
    st.subheader("🏗️ Arquitectura de URLs")
    
    if not st.session_state.data_loaded:
        st.info("Carga los datos primero")
        return
    
    processor = st.session_state.processor
    analyzer = st.session_state.analyzer
    category = st.session_state.category
    
    if st.session_state.insights_data is None:
        with st.spinner("Analizando..."):
            st.session_state.insights_data = InsightGenerator.generate_all_insights(processor, analyzer)
    
    arch = st.session_state.insights_data.get('architecture', {})
    rec = arch.get('recommended_architecture', {})
    url_struct = rec.get('url_structure', {})
    
    n0 = url_struct.get('N0', {}).get('pct', 5)
    n1 = url_struct.get('N1', {}).get('pct', 45)
    n2 = url_struct.get('N2', {}).get('pct', 35)
    n3 = url_struct.get('N3+', {}).get('pct', 15)
    
    st.markdown("#### Estructura de Niveles")
    c1, c2, c3, c4 = st.columns(4)
    
    with c1:
        st.metric("N0", f"{n0:.0f}%")
        st.success("INDEX")
        st.caption(f"/{category}")
    with c2:
        st.metric("N1", f"{n1:.0f}%")
        st.success("INDEX")
        st.caption(f"/{category}/{{faceta}}")
    with c3:
        st.metric("N2", f"{n2:.0f}%")
        st.warning("SELECTIVO")
        st.caption(f"/{category}/{{f1}}/{{f2}}")
    with c4:
        st.metric("N3+", f"{n3:.0f}%")
        st.error("NOINDEX")
        st.caption("3+ atributos")
    
    st.divider()
    
    col1, col2 = st.columns([2, 1])
    with col1:
        level_df = pd.DataFrame({
            'Nivel': ['N0', 'N1', 'N2', 'N3+'],
            'Porcentaje': [n0, n1, n2, n3],
            'Acción': ['INDEX', 'INDEX', 'SELECTIVO', 'NOINDEX']
        })
        fig = px.bar(level_df, x='Nivel', y='Porcentaje', color='Acción',
                    color_discrete_map={'INDEX': '#22c55e', 'SELECTIVO': '#eab308', 'NOINDEX': '#ef4444'})
        fig.update_layout(height=250)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        indexable = n0 + n1 + (n2 * 0.3)
        st.metric("✅ Indexable", f"{indexable:.0f}%")
        st.metric("❌ NOINDEX", f"{100-indexable:.0f}%")
    
    st.divider()
    st.markdown("#### 📑 Reglas de Indexación")
    rules = pd.DataFrame({
        'Patrón': [f'/{category}', f'/{category}/{{tamaño}}', f'/{category}/{{marca}}', 
                   f'/{category}/{{f1}}/{{f2}}', '3+ facetas', '?order=, ?page='],
        'Indexar': ['✅', '✅', '✅', '⚠️', '❌', '❌'],
        'Condición': ['Siempre', 'Tamaños estándar', 'Demanda >50', 'KW>200 ó clics>500', 'Canonical→N2', 'Canonical→base']
    })
    st.dataframe(rules, use_container_width=True, hide_index=True)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB: NAVEGACIÓN - COMPONENTES 100% NATIVOS
# ═══════════════════════════════════════════════════════════════════════════════

def render_navigation_tab():
    st.subheader("🧭 Sistema de Navegación")
    st.caption("Uso de filtros por usuarios (Demanda Interna)")
    
    if not st.session_state.data_loaded:
        st.info("Carga los datos primero")
        return
    
    processor = st.session_state.processor
    analyzer = st.session_state.analyzer
    category = st.session_state.category
    
    if st.session_state.insights_data is None:
        with st.spinner("Generando..."):
            st.session_state.insights_data = InsightGenerator.generate_all_insights(processor, analyzer)
    
    nav = st.session_state.insights_data.get('navigation_system', {})
    
    if not nav:
        st.warning("⚠️ Carga 'Search Filters' para ver navegación")
        return
    
    layer1 = nav.get('layer1_ux', {})
    facets = layer1.get('facets', [])
    
    if not facets:
        st.info("No hay datos de facetas")
        return
    
    # ═══════════════════════════════════════════════════════════════════════════
    # SECCIÓN 1: USO DE FACETAS (componentes nativos)
    # ═══════════════════════════════════════════════════════════════════════════
    st.markdown("#### 📊 Uso de Facetas")
    
    for i in range(0, min(len(facets), 9), 3):
        cols = st.columns(3)
        for j, facet in enumerate(facets[i:i+3]):
            with cols[j]:
                with st.container(border=True):
                    # Header con métricas nativas
                    col_h1, col_h2 = st.columns([3, 1])
                    with col_h1:
                        st.markdown(f"**{facet.get('icon', '📦')} {facet.get('name', 'Faceta')}**")
                    with col_h2:
                        st.metric("", f"{facet.get('usage_pct', 0):.1f}%", label_visibility="collapsed")
                    
                    # Descripción
                    if facet.get('description'):
                        st.caption(facet.get('description'))
                    
                    # Top valores (uso puro, sin concatenación)
                    top_vals = facet.get('top_values', [])[:5]
                    if top_vals:
                        st.markdown("**Top valores:**")
                        for val in top_vals:
                            st.write(f"• {val}")
                    
                    # URL pattern con st.code
                    if facet.get('generates_url') and facet.get('url_pattern'):
                        st.code(facet.get('url_pattern'), language=None)
                    elif not facet.get('generates_url'):
                        st.warning("No genera URL", icon="⚠️")
                    
                    # Contenido sugerido
                    if facet.get('content_suggestion'):
                        st.info(f"📝 {facet.get('content_suggestion')}")
    
    st.divider()
    
    # ═══════════════════════════════════════════════════════════════════════════
    # SECCIÓN 2: COMBINACIONES DE FILTROS
    # ═══════════════════════════════════════════════════════════════════════════
    st.markdown("#### 🔗 Combinaciones de Filtros Más Usadas")
    
    arch = st.session_state.insights_data.get('architecture', {})
    combos = arch.get('facet_combinations', [])
    
    if combos:
        combo_data = []
        for c in combos[:10]:
            comb = c.get('combination', ())
            if isinstance(comb, (list, tuple)):
                combo_str = ' + '.join([str(x).title() for x in comb])
            else:
                combo_str = str(comb)
            combo_data.append({
                'Combinación': combo_str,
                'Sesiones': f"{c.get('sessions', 0):,}",
                'URLs': c.get('url_count', 0)
            })
        
        if combo_data:
            combo_df = pd.DataFrame(combo_data)
            st.dataframe(combo_df, use_container_width=True, hide_index=True)
    else:
        st.info("Carga 'Page Full URL' para ver combinaciones")
    
    st.divider()
    
    # ═══════════════════════════════════════════════════════════════════════════
    # SECCIÓN 3: DESVIACIÓN DEMANDA INTERNA vs SEO
    # ═══════════════════════════════════════════════════════════════════════════
    st.markdown("#### 📊 Desviación: Demanda Interna vs SEO")
    
    facet_usage = st.session_state.insights_data.get('facet_usage', {})
    
    if facet_usage:
        deviation_data = []
        for facet, data in facet_usage.items():
            if facet not in ['total', 'sorting', 'other', 'search filters', 'price']:
                deviation_data.append({
                    'Faceta': facet.title(),
                    'Interna %': round(data.get('pct_all', 0), 1),
                    'SEO %': round(data.get('pct_seo', 0), 1),
                    'Ratio SEO': f"{data.get('seo_ratio', 0):.0f}%",
                    'Gap': round(data.get('pct_all', 0) - data.get('pct_seo', 0), 1)
                })
        
        if deviation_data:
            dev_df = pd.DataFrame(deviation_data)
            dev_df = dev_df.sort_values('Interna %', ascending=False)
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.dataframe(dev_df, use_container_width=True, hide_index=True)
            
            with col2:
                fig = go.Figure()
                fig.add_trace(go.Bar(name='Interna', x=dev_df['Faceta'], y=dev_df['Interna %'], marker_color='#3b82f6'))
                fig.add_trace(go.Bar(name='SEO', x=dev_df['Faceta'], y=dev_df['SEO %'], marker_color='#22c55e'))
                fig.update_layout(barmode='group', height=300, margin=dict(t=10, b=10))
                st.plotly_chart(fig, use_container_width=True)
            
            high_gaps = [d for d in deviation_data if d['Gap'] > 5]
            if high_gaps:
                st.success(f"💡 **Recomendación:** {', '.join([d['Faceta'] for d in high_gaps[:3]])} tienen más uso interno que visibilidad SEO")
    else:
        st.info("Carga Search Filters (Todo y SEO) para ver desviación")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB: DEMANDA - CON DATOS REALES
# ═══════════════════════════════════════════════════════════════════════════════

def render_demand_tab():
    st.subheader("📊 Comparativa de Demanda")
    
    if not st.session_state.data_loaded:
        st.info("Carga los datos primero")
        return
    
    processor = st.session_state.processor
    
    has_internal = 'filter_usage_all' in processor.data
    has_market = 'keyword_research' in processor.data
    
    col1, col2 = st.columns(2)
    
    # DEMANDA INTERNA
    with col1:
        st.markdown("#### 🏠 Demanda Interna")
        st.caption("Uso de filtros en PcComponentes")
        
        if has_internal:
            df = processor.data.get('filter_usage_all')
            if df is not None and not df.empty:
                grouped = df.groupby('facet_type')['sessions'].sum().reset_index()
                grouped = grouped[~grouped['facet_type'].isin(['total', 'sorting', 'other', 'search filters'])]
                grouped = grouped.sort_values('sessions', ascending=False).head(10)
                
                fig = px.bar(grouped, x='facet_type', y='sessions',
                            labels={'facet_type': 'Faceta', 'sessions': 'Sesiones'})
                fig.update_layout(height=300, showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
                
                st.metric("Total Interacciones", f"{df['sessions'].sum():,}")
        else:
            st.info("📤 Carga 'Search Filters'")
    
    # DEMANDA DE MERCADO - CORREGIDO
    with col2:
        st.markdown("#### 🌐 Demanda de Mercado")
        st.caption("Volumen búsquedas (Google)")
        
        if has_market:
            df = processor.data.get('keyword_research')
            if df is not None and not df.empty:
                # Buscar columna de volumen
                vol_col = None
                for col in df.columns:
                    col_lower = col.lower()
                    if 'volume' in col_lower or 'volumen' in col_lower or 'búsquedas' in col_lower or 'searches' in col_lower:
                        vol_col = col
                        break
                
                # Buscar columna de keyword
                kw_col = None
                for col in df.columns:
                    col_lower = col.lower()
                    if 'keyword' in col_lower or 'palabra' in col_lower:
                        kw_col = col
                        break
                
                if not kw_col:
                    kw_col = df.columns[0]
                
                if vol_col:
                    df_clean = df[[kw_col, vol_col]].copy()
                    df_clean.columns = ['Keyword', 'Volumen']
                    
                    # Limpiar volumen (manejar formatos como "1K", "10K", etc.)
                    def parse_vol(v):
                        if pd.isna(v):
                            return 0
                        v = str(v).upper().strip().replace(',', '').replace(' ', '')
                        try:
                            if 'K' in v:
                                return int(float(v.replace('K', '')) * 1000)
                            elif 'M' in v:
                                return int(float(v.replace('M', '')) * 1000000)
                            return int(float(v))
                        except:
                            return 0
                    
                    df_clean['Volumen'] = df_clean['Volumen'].apply(parse_vol)
                    df_clean = df_clean[df_clean['Volumen'] > 0]
                    
                    if not df_clean.empty:
                        top = df_clean.nlargest(10, 'Volumen')
                        
                        fig = px.bar(top, x='Keyword', y='Volumen')
                        fig.update_layout(height=300, showlegend=False, xaxis_tickangle=-45)
                        st.plotly_chart(fig, use_container_width=True)
                        
                        st.metric("Volumen Total", f"{df_clean['Volumen'].sum():,}")
                    else:
                        st.warning("Sin datos de volumen válidos")
                        st.caption(f"Columnas detectadas: {list(df.columns)[:5]}")
                else:
                    st.warning("No se encontró columna de volumen")
                    st.caption(f"Columnas: {list(df.columns)}")
        else:
            st.info("📤 Carga 'Keyword Research'")
    
    st.divider()
    
    # OPORTUNIDADES - CON DATOS REALES
    st.markdown("#### 💡 Oportunidades Detectadas")
    
    if st.session_state.insights_data:
        insights = st.session_state.insights_data
        
        # Market Share por marca
        brand_data = insights.get('brand_analysis', [])
        if brand_data:
            st.markdown("##### 🏆 Market Share por Marca")
            
            col1, col2 = st.columns(2)
            
            with col1:
                brand_df = pd.DataFrame(brand_data[:8])
                if not brand_df.empty and 'internal_sessions' in brand_df.columns:
                    fig = px.pie(brand_df, values='internal_sessions', names='brand', title='Demanda Interna')
                    fig.update_layout(height=280, margin=dict(t=30, b=10))
                    st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                if brand_data:
                    display_brands = []
                    for b in brand_data[:8]:
                        display_brands.append({
                            'Marca': b.get('brand', '').title(),
                            'Interna %': f"{b.get('internal_share', 0):.1f}",
                            'SEO %': f"{b.get('seo_share', 0):.1f}",
                            'Gap': f"{b.get('gap', 0):+.1f}"
                        })
                    st.dataframe(pd.DataFrame(display_brands), use_container_width=True, hide_index=True)
            
            # Oportunidades de marca
            high_gap = [b for b in brand_data if b.get('gap', 0) > 3]
            if high_gap:
                brands_str = ', '.join([b['brand'].title() for b in high_gap[:3]])
                st.success(f"🎯 **Recomendación SEO:** {brands_str} tienen más demanda interna que visibilidad")
        else:
            st.info("Carga Search Filters para ver market share por marca")
        
        # Tamaños top
        size_data = insights.get('size_analysis', [])
        if size_data:
            st.markdown("##### 📐 Tamaños Más Demandados")
            top_sizes = [f"{s['size']}\"" for s in size_data[:5] if s.get('size')]
            if top_sizes:
                st.write(f"**Top 5:** {', '.join(top_sizes)}")
                
                size_df = pd.DataFrame([{
                    'Tamaño': f"{s['size']}\"",
                    'Sesiones': f"{s.get('sessions_all', 0):,}",
                    'Ratio SEO': f"{s.get('seo_ratio', 0):.0f}%"
                } for s in size_data[:5]])
                st.dataframe(size_df, use_container_width=True, hide_index=True)
        
        # Tecnologías
        tech_data = insights.get('tech_analysis', [])
        if tech_data:
            st.markdown("##### ⚡ Tecnologías Más Buscadas")
            tech_df = pd.DataFrame([{
                'Tecnología': t.get('technology', '').upper(),
                'Sesiones': f"{t.get('sessions_all', 0):,}"
            } for t in tech_data[:5]])
            st.dataframe(tech_df, use_container_width=True, hide_index=True)
    else:
        st.info("Ejecuta el análisis para ver oportunidades")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB: CANIBALIZACIÓN - SIN TEXTO EXPLICATIVO
# ═══════════════════════════════════════════════════════════════════════════════

def render_cannibalization_tab():
    st.subheader("🔴 Canibalización")
    
    if not st.session_state.analysis_complete:
        st.info("Ejecuta el análisis primero")
        return
    
    analyzer = st.session_state.analyzer
    cannib = analyzer.results.cannibalization
    
    if cannib.empty:
        st.success("✅ No se detectó canibalización")
        return
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Casos", len(cannib))
    c2.metric("Clics Afectados", f"{cannib['impact_score'].sum():,.0f}")
    c3.metric("Alto Impacto", len(cannib[cannib['impact_score'] > 50]))
    
    st.divider()
    
    display = cannib[['top_query', 'impact_score', 'url', 'suggested_filter']].copy()
    display.columns = ['Query', 'Clics', 'Artículo', 'Filtro Recomendado']
    display['Artículo'] = display['Artículo'].str.replace('https://www.pccomponentes.com/', '/')
    display = display.sort_values('Clics', ascending=False)
    
    st.dataframe(display.head(20), use_container_width=True, hide_index=True)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB: INSIGHTS - "RECOMENDACIÓN" en lugar de "ACCIÓN"
# ═══════════════════════════════════════════════════════════════════════════════

def render_insights_tab():
    st.subheader("💡 Insights")
    
    if not st.session_state.data_loaded:
        st.info("Carga los datos primero")
        return
    
    processor = st.session_state.processor
    analyzer = st.session_state.analyzer
    
    if st.session_state.insights_data is None:
        with st.spinner("Generando..."):
            st.session_state.insights_data = InsightGenerator.generate_all_insights(processor, analyzer)
    
    insights = st.session_state.insights_data.get('insights', [])
    metrics = st.session_state.insights_data.get('metrics', {})
    sources = st.session_state.insights_data.get('data_sources', [])
    
    if sources:
        st.success(" • ".join(sources))
    
    st.divider()
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Interacciones", f"{metrics.get('total_internal_sessions', 0):,}")
    c2.metric("Ratio SEO", f"{metrics.get('seo_ratio', 0):.1f}%")
    c3.metric("Insights", len(insights))
    
    st.divider()
    
    if insights:
        for ins in insights:
            priority = ins.get('priority', 'LOW')
            icon = "🔴" if priority == 'HIGH' else "🟡" if priority == 'MEDIUM' else "🟢"
            
            with st.expander(f"{icon} {ins.get('title')}", expanded=(priority == 'HIGH')):
                st.markdown(ins.get('description', ''))
                if ins.get('action'):
                    st.info(f"💡 **Recomendación:** {ins.get('action')}")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB: RECOMENDACIONES - Texto "Recomendación"
# ═══════════════════════════════════════════════════════════════════════════════

def render_recommendations_tab():
    st.subheader("🚀 Recomendaciones")
    
    if not st.session_state.analysis_complete:
        st.info("Ejecuta el análisis primero")
        return
    
    analyzer = st.session_state.analyzer
    recs = analyzer.results.recommendations
    
    if not recs:
        st.info("No hay recomendaciones")
        return
    
    by_type = {}
    for rec in recs:
        t = rec.get('type', 'OTHER')
        if t not in by_type:
            by_type[t] = []
        by_type[t].append(rec)
    
    labels = {
        'UX_ARCHITECTURE': '🏆 Arquitectura',
        'CANNIBALIZATION': '🔴 Canibalización',
        'DEMAND_GAP': '🟡 Gaps',
        'UX_SEO_GAP': '🔵 Gap Interno/SEO',
        'INDEXATION': '⚪ Indexación'
    }
    
    for rec_type, recs_list in by_type.items():
        st.markdown(f"#### {labels.get(rec_type, rec_type)}")
        
        for rec in recs_list[:5]:
            action = str(rec.get('action', ''))[:80]
            with st.expander(f"{action}..."):
                st.markdown(f"**Recomendación:** {rec.get('action')}")
                st.markdown(f"**Razón:** {rec.get('reason')}")
                st.markdown(f"**Impacto:** {rec.get('impact')}")
        
        st.divider()


# ═══════════════════════════════════════════════════════════════════════════════
# TAB: EXPORTAR
# ═══════════════════════════════════════════════════════════════════════════════
# ESTRATEGIA DE CONTENIDO (Funnel, Drivers, Lead Magnets)
# ═══════════════════════════════════════════════════════════════════════════════

def render_content_strategy_tab():
    """Análisis de estrategia de contenido: funnel, drivers de compra, lead magnets"""
    st.subheader("📝 Estrategia de Contenido")
    
    processor = st.session_state.processor
    analyzer = st.session_state.analyzer
    insights_data = st.session_state.insights_data or {}
    
    if not processor:
        st.info("Carga datos para analizar la estrategia de contenido")
        return
    
    category = processor.category_keyword
    
    # ═══════════════════════════════════════════════════════════════════════════
    # EXPLICACIÓN DEL ANÁLISIS
    # ═══════════════════════════════════════════════════════════════════════════
    with st.expander("ℹ️ Metodología de Análisis", expanded=False):
        st.markdown(f"""
        **Clasificación de URLs por tipo de contenido:**
        - **Transaccional (PLP/Filtros)**: URLs bajo `/{category}/` → Páginas de producto/categoría
        - **Informacional (Blog/Guías)**: URLs que mencionan "{category}" pero NO están bajo `/{category}/`
        
        **Etapas del Funnel:**
        - **TOFU (Awareness)**: "qué es", "tipos de", "cómo funciona" → Educación
        - **MOFU (Consideration)**: "mejores", "comparativa", "vs", "guía" → Evaluación
        - **BOFU (Decision)**: "comprar", "precio", "review" → Compra
        
        **Drivers de Compra:**
        Detectados automáticamente de las facetas más usadas y las queries de búsqueda.
        """)
    
    st.divider()
    
    # ═══════════════════════════════════════════════════════════════════════════
    # ANÁLISIS DE FUNNEL DE CONTENIDO
    # ═══════════════════════════════════════════════════════════════════════════
    st.markdown("### 🔻 Distribución de Contenido en el Funnel")
    
    # Analizar URLs de Top Query o GSC
    top_query_df = processor.data.get('top_query', pd.DataFrame())
    gsc_pages_df = processor.data.get('gsc_pages', pd.DataFrame())
    
    # Usar la fuente disponible
    urls_df = top_query_df if not top_query_df.empty else gsc_pages_df
    
    if not urls_df.empty and 'url' in urls_df.columns:
        # Clasificar cada URL
        url_analysis = []
        for _, row in urls_df.iterrows():
            url = row.get('url', '')
            classification = processor.classify_url(url)
            
            clicks_col = 'clicks' if 'clicks' in row.index else 'url_total_clicks'
            impressions_col = 'impressions' if 'impressions' in row.index else 'url_total_impressions'
            
            url_analysis.append({
                'url': url,
                'content_type': classification.get('content_type', 'OTHER'),
                'funnel_stage': classification.get('funnel_stage', 'OTHER'),
                'url_type': classification.get('type', 'OTHER'),
                'clicks': row.get(clicks_col, 0) if pd.notna(row.get(clicks_col, 0)) else 0,
                'impressions': row.get(impressions_col, 0) if pd.notna(row.get(impressions_col, 0)) else 0
            })
        
        url_analysis_df = pd.DataFrame(url_analysis)
        
        # Métricas por tipo de contenido
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Por Tipo de Contenido")
            content_summary = url_analysis_df.groupby('content_type').agg({
                'url': 'count',
                'clicks': 'sum',
                'impressions': 'sum'
            }).reset_index()
            content_summary.columns = ['Tipo', 'URLs', 'Clics', 'Impresiones']
            content_summary = content_summary.sort_values('Clics', ascending=False)
            
            # Calcular porcentajes
            total_clicks = content_summary['Clics'].sum()
            content_summary['% Clics'] = (content_summary['Clics'] / total_clicks * 100).round(1) if total_clicks > 0 else 0
            
            st.dataframe(content_summary, use_container_width=True, hide_index=True)
            
            # Gráfico de distribución
            fig_content = px.pie(
                content_summary[content_summary['Clics'] > 0],
                values='Clics',
                names='Tipo',
                title='Distribución de Clics por Tipo',
                color_discrete_sequence=['#3b82f6', '#10b981', '#f59e0b']
            )
            fig_content.update_traces(textposition='inside', textinfo='percent+label')
            fig_content.update_layout(height=300, showlegend=False)
            st.plotly_chart(fig_content, use_container_width=True)
        
        with col2:
            st.markdown("#### Por Etapa del Funnel")
            funnel_summary = url_analysis_df.groupby('funnel_stage').agg({
                'url': 'count',
                'clicks': 'sum',
                'impressions': 'sum'
            }).reset_index()
            funnel_summary.columns = ['Etapa', 'URLs', 'Clics', 'Impresiones']
            
            # Ordenar por funnel
            stage_order = {'TOFU': 0, 'MOFU': 1, 'BOFU': 2, 'OTHER': 3}
            funnel_summary['order'] = funnel_summary['Etapa'].map(stage_order)
            funnel_summary = funnel_summary.sort_values('order').drop('order', axis=1)
            
            total_clicks = funnel_summary['Clics'].sum()
            funnel_summary['% Clics'] = (funnel_summary['Clics'] / total_clicks * 100).round(1) if total_clicks > 0 else 0
            
            st.dataframe(funnel_summary, use_container_width=True, hide_index=True)
            
            # Gráfico de funnel
            funnel_display = funnel_summary[funnel_summary['Etapa'] != 'OTHER'].copy()
            if not funnel_display.empty:
                fig_funnel = px.funnel(
                    funnel_display,
                    x='Clics',
                    y='Etapa',
                    title='Funnel de Contenido',
                    color_discrete_sequence=['#22d3ee', '#3b82f6', '#10b981']
                )
                fig_funnel.update_layout(height=300)
                st.plotly_chart(fig_funnel, use_container_width=True)
    else:
        st.warning("Carga datos de Top Query o GSC Páginas para analizar el funnel de contenido")
    
    st.divider()
    
    # ═══════════════════════════════════════════════════════════════════════════
    # DRIVERS DE COMPRA
    # ═══════════════════════════════════════════════════════════════════════════
    st.markdown("### 🎯 Drivers de Compra")
    st.caption("Atributos que más influyen en la decisión de compra, basados en uso de facetas y queries")
    
    # Obtener drivers desde facetas (demanda interna)
    facet_drivers = {}
    filter_all = processor.data.get('filter_usage_all')
    
    if filter_all is not None and not filter_all.empty:
        # Excluir tipos de sistema
        system_types = ['sorting', 'total', 'other', 'search_filters', 'precio', 'price']
        product_facets = filter_all[~filter_all['facet_type'].str.lower().isin(system_types)]
        
        if not product_facets.empty:
            facet_summary = product_facets.groupby('facet_type')['sessions'].sum().reset_index()
            facet_summary = facet_summary.sort_values('sessions', ascending=False)
            total_sessions = facet_summary['sessions'].sum()
            
            for _, row in facet_summary.head(10).iterrows():
                facet_type = row['facet_type']
                sessions = row['sessions']
                pct = sessions / total_sessions * 100 if total_sessions > 0 else 0
                facet_drivers[facet_type] = {
                    'sessions': int(sessions),
                    'pct': round(pct, 1),
                    'source': 'facetas'
                }
    
    # Obtener drivers desde queries (demanda externa)
    query_drivers = {}
    gsc_queries = processor.data.get('gsc_queries', pd.DataFrame())
    keyword_research = processor.data.get('keyword_research', pd.DataFrame())
    
    queries_to_analyze = pd.DataFrame()
    if not gsc_queries.empty and 'query' in gsc_queries.columns:
        queries_to_analyze = gsc_queries
    elif not keyword_research.empty and 'keyword' in keyword_research.columns:
        queries_to_analyze = keyword_research.rename(columns={'keyword': 'query', 'volume': 'impressions'})
    
    if not queries_to_analyze.empty:
        # Analizar drivers en cada query
        driver_counts = {}
        for _, row in queries_to_analyze.iterrows():
            query = row.get('query', '')
            if pd.isna(query):
                continue
            
            funnel_info = processor.classify_query_funnel(query)
            for driver in funnel_info.get('drivers', []):
                if driver not in driver_counts:
                    driver_counts[driver] = {'count': 0, 'impressions': 0}
                driver_counts[driver]['count'] += 1
                driver_counts[driver]['impressions'] += row.get('impressions', 0) if pd.notna(row.get('impressions', 0)) else 0
        
        for driver, data in driver_counts.items():
            query_drivers[driver] = {
                'mentions': data['count'],
                'impressions': int(data['impressions']),
                'source': 'queries'
            }
    
    # Mostrar drivers combinados
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 🏠 Desde Facetas (Demanda Interna)")
        if facet_drivers:
            drivers_df = pd.DataFrame([
                {'Driver': k.replace('_', ' ').title(), 'Sesiones': v['sessions'], '% Uso': f"{v['pct']}%"}
                for k, v in facet_drivers.items()
            ])
            st.dataframe(drivers_df, use_container_width=True, hide_index=True)
            
            # Gráfico
            fig_facet_drivers = px.bar(
                drivers_df.head(8),
                x='Sesiones',
                y='Driver',
                orientation='h',
                title='Top Drivers (Facetas)',
                color='Sesiones',
                color_continuous_scale='Blues'
            )
            fig_facet_drivers.update_layout(height=300, showlegend=False, yaxis={'categoryorder': 'total ascending'})
            st.plotly_chart(fig_facet_drivers, use_container_width=True)
        else:
            st.info("Carga Search Filters para detectar drivers desde facetas")
    
    with col2:
        st.markdown("#### 🌐 Desde Queries (Demanda Externa)")
        if query_drivers:
            query_drivers_df = pd.DataFrame([
                {'Driver': k.replace('_', ' ').title(), 'Menciones': v['mentions'], 'Impresiones': v['impressions']}
                for k, v in sorted(query_drivers.items(), key=lambda x: -x[1]['impressions'])
            ])
            st.dataframe(query_drivers_df, use_container_width=True, hide_index=True)
            
            # Gráfico
            fig_query_drivers = px.bar(
                query_drivers_df.head(8),
                x='Impresiones',
                y='Driver',
                orientation='h',
                title='Top Drivers (Queries)',
                color='Impresiones',
                color_continuous_scale='Greens'
            )
            fig_query_drivers.update_layout(height=300, showlegend=False, yaxis={'categoryorder': 'total ascending'})
            st.plotly_chart(fig_query_drivers, use_container_width=True)
        else:
            st.info("Carga GSC Consultas o Keywords para detectar drivers desde queries")
    
    st.divider()
    
    # ═══════════════════════════════════════════════════════════════════════════
    # OPORTUNIDADES DE LEAD MAGNETS
    # ═══════════════════════════════════════════════════════════════════════════
    st.markdown("### 🧲 Oportunidades de Lead Magnets")
    st.caption("Sugerencias de contenido de valor basadas en los drivers y gaps detectados")
    
    # Generar sugerencias de lead magnets basadas en drivers
    lead_magnet_suggestions = []
    
    # Combinar drivers de ambas fuentes
    all_drivers = set(list(facet_drivers.keys()) + list(query_drivers.keys()))
    
    # Templates de lead magnets por tipo de driver
    lead_magnet_templates = {
        'precio': [
            {'tipo': '📊 Comparador', 'titulo': f'Comparador de precios de {category}', 'funnel': 'MOFU'},
            {'tipo': '📧 Alerta', 'titulo': f'Alerta de ofertas en {category}', 'funnel': 'BOFU'},
        ],
        'marca': [
            {'tipo': '📋 Guía', 'titulo': f'Guía de marcas de {category}: cuál elegir según tu perfil', 'funnel': 'MOFU'},
        ],
        'marcas': [
            {'tipo': '📋 Guía', 'titulo': f'Guía de marcas de {category}: cuál elegir según tu perfil', 'funnel': 'MOFU'},
        ],
        'rendimiento': [
            {'tipo': '🧮 Calculadora', 'titulo': f'Calculadora de rendimiento: qué {category} necesitas', 'funnel': 'MOFU'},
            {'tipo': '📊 Benchmark', 'titulo': f'Benchmark de rendimiento de {category}', 'funnel': 'MOFU'},
        ],
        'tamano': [
            {'tipo': '🧮 Calculadora', 'titulo': f'Calculadora: qué tamaño de {category} necesitas', 'funnel': 'MOFU'},
        ],
        'tamaño': [
            {'tipo': '🧮 Calculadora', 'titulo': f'Calculadora: qué tamaño de {category} necesitas', 'funnel': 'MOFU'},
        ],
        'capacidad': [
            {'tipo': '🧮 Calculadora', 'titulo': f'Calculadora de capacidad/almacenamiento para {category}', 'funnel': 'MOFU'},
        ],
        'almacenamiento': [
            {'tipo': '🧮 Calculadora', 'titulo': f'Calculadora de capacidad/almacenamiento para {category}', 'funnel': 'MOFU'},
        ],
        'bateria': [
            {'tipo': '📊 Comparativa', 'titulo': f'Comparativa de autonomía: {category} con mejor batería', 'funnel': 'MOFU'},
        ],
        'camara': [
            {'tipo': '📷 Test', 'titulo': f'Test de cámaras: comparativa fotográfica de {category}', 'funnel': 'MOFU'},
        ],
        'calidad_imagen': [
            {'tipo': '📊 Comparativa', 'titulo': f'Comparativa de pantallas/calidad de imagen en {category}', 'funnel': 'MOFU'},
        ],
        'conectividad': [
            {'tipo': '📋 Guía', 'titulo': f'Guía de conectividad: 5G, WiFi 6 y más en {category}', 'funnel': 'TOFU'},
        ],
        'diseno': [
            {'tipo': '🎨 Galería', 'titulo': f'Galería de diseños: {category} más elegantes del mercado', 'funnel': 'MOFU'},
        ],
        'durabilidad': [
            {'tipo': '🛡️ Guía', 'titulo': f'Guía de {category} resistentes: IP68, MIL-STD y más', 'funnel': 'MOFU'},
        ],
    }
    
    # Lead magnets genéricos siempre útiles
    generic_lead_magnets = [
        {'tipo': '✅ Checklist', 'titulo': f'Checklist: qué mirar antes de comprar un {category}', 'funnel': 'MOFU', 'driver': 'general'},
        {'tipo': '📚 Ebook', 'titulo': f'Guía definitiva de {category} {datetime.now().year}', 'funnel': 'TOFU', 'driver': 'general'},
        {'tipo': '🎯 Quiz', 'titulo': f'Quiz: encuentra tu {category} ideal en 5 preguntas', 'funnel': 'MOFU', 'driver': 'general'},
        {'tipo': '📧 Newsletter', 'titulo': f'Newsletter: novedades y ofertas en {category}', 'funnel': 'TOFU', 'driver': 'general'},
    ]
    
    # Generar sugerencias basadas en drivers detectados
    for driver in all_drivers:
        driver_lower = driver.lower()
        for template_key, templates in lead_magnet_templates.items():
            if template_key in driver_lower:
                for template in templates:
                    suggestion = template.copy()
                    suggestion['driver'] = driver.replace('_', ' ').title()
                    suggestion['prioridad'] = '🔴 Alta' if driver in facet_drivers and driver in query_drivers else '🟡 Media'
                    lead_magnet_suggestions.append(suggestion)
    
    # Añadir genéricos
    for lm in generic_lead_magnets:
        lm['prioridad'] = '🟢 Base'
        lead_magnet_suggestions.append(lm)
    
    # Eliminar duplicados por título
    seen_titles = set()
    unique_suggestions = []
    for s in lead_magnet_suggestions:
        if s['titulo'] not in seen_titles:
            seen_titles.add(s['titulo'])
            unique_suggestions.append(s)
    
    # Ordenar por prioridad
    priority_order = {'🔴 Alta': 0, '🟡 Media': 1, '🟢 Base': 2}
    unique_suggestions.sort(key=lambda x: priority_order.get(x.get('prioridad', '🟢 Base'), 2))
    
    # Mostrar en tabla
    if unique_suggestions:
        suggestions_df = pd.DataFrame(unique_suggestions)
        display_cols = ['prioridad', 'tipo', 'titulo', 'funnel', 'driver']
        display_cols = [c for c in display_cols if c in suggestions_df.columns]
        
        suggestions_df = suggestions_df[display_cols].rename(columns={
            'prioridad': 'Prioridad',
            'tipo': 'Tipo',
            'titulo': 'Título Sugerido',
            'funnel': 'Etapa',
            'driver': 'Driver'
        })
        
        st.dataframe(suggestions_df, use_container_width=True, hide_index=True)
    
    st.divider()
    
    # ═══════════════════════════════════════════════════════════════════════════
    # GAPS DE CONTENIDO POR ETAPA
    # ═══════════════════════════════════════════════════════════════════════════
    st.markdown("### 🕳️ Gaps de Contenido")
    st.caption("Oportunidades de contenido por etapa del funnel basadas en queries sin cobertura")
    
    if not queries_to_analyze.empty:
        # Clasificar todas las queries por funnel
        query_funnel_analysis = []
        for _, row in queries_to_analyze.iterrows():
            query = row.get('query', '')
            if pd.isna(query):
                continue
            
            funnel_info = processor.classify_query_funnel(query)
            impressions = row.get('impressions', 0) if pd.notna(row.get('impressions', 0)) else 0
            clicks = row.get('clicks', 0) if pd.notna(row.get('clicks', 0)) else 0
            
            query_funnel_analysis.append({
                'query': query,
                'funnel_stage': funnel_info['funnel_stage'],
                'intent': funnel_info['intent'],
                'content_type': funnel_info['content_type'],
                'drivers': ', '.join(funnel_info['drivers']) if funnel_info['drivers'] else '-',
                'impressions': impressions,
                'clicks': clicks,
                'ctr': (clicks / impressions * 100) if impressions > 0 else 0
            })
        
        query_funnel_df = pd.DataFrame(query_funnel_analysis)
        
        # Mostrar queries por etapa con bajo CTR (gaps)
        tabs_funnel = st.tabs(['🔵 TOFU', '🟢 MOFU', '🟠 BOFU'])
        
        for i, (tab, stage) in enumerate(zip(tabs_funnel, ['TOFU', 'MOFU', 'BOFU'])):
            with tab:
                stage_df = query_funnel_df[query_funnel_df['funnel_stage'] == stage].copy()
                
                if stage_df.empty:
                    st.info(f"No hay queries clasificadas como {stage}")
                    continue
                
                # Métricas de la etapa
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.metric("Queries", f"{len(stage_df):,}")
                with c2:
                    st.metric("Impresiones", f"{stage_df['impressions'].sum():,.0f}")
                with c3:
                    avg_ctr = stage_df['ctr'].mean()
                    st.metric("CTR Promedio", f"{avg_ctr:.2f}%")
                
                # Queries con más impresiones pero bajo CTR (oportunidades)
                st.markdown(f"**Oportunidades en {stage}** (alto volumen, bajo CTR)")
                
                opportunities = stage_df[
                    (stage_df['impressions'] > stage_df['impressions'].median()) & 
                    (stage_df['ctr'] < stage_df['ctr'].median())
                ].nlargest(10, 'impressions')
                
                if not opportunities.empty:
                    display_df = opportunities[['query', 'impressions', 'clicks', 'ctr', 'content_type', 'drivers']].copy()
                    display_df.columns = ['Query', 'Impresiones', 'Clics', 'CTR %', 'Tipo Contenido', 'Drivers']
                    display_df['CTR %'] = display_df['CTR %'].round(2)
                    st.dataframe(display_df, use_container_width=True, hide_index=True)
                else:
                    st.success(f"✅ Buena cobertura en {stage}")
    else:
        st.info("Carga GSC Consultas o Keywords para detectar gaps de contenido")


# ═══════════════════════════════════════════════════════════════════════════════
# AUDITORÍA TÉCNICA (Screaming Frog + GSC)
# ═══════════════════════════════════════════════════════════════════════════════

def render_audit_tab():
    """Auditoría técnica SEO basada en datos de Screaming Frog + GSC"""
    st.subheader("🔍 Auditoría Técnica SEO")
    
    processor = st.session_state.processor
    
    if not processor or 'screaming_frog' not in processor.data:
        st.info("📤 Sube el archivo **Screaming Frog - Internal HTML** con integración GSC para habilitar esta auditoría.")
        
        with st.expander("ℹ️ Cómo obtener el archivo"):
            st.markdown("""
            **En Screaming Frog:**
            1. Configurar integración con Google Search Console (Configuration > API Access > GSC)
            2. Seleccionar período: últimos 12 meses
            3. Crawlear el directorio de la categoría
            4. Export > Internal > HTML
            
            **Para análisis de Thin Content real (opcional):**
            1. Configuration > Custom > Extraction
            2. Añadir extracción XPath: `//*[@id="action-bar-total-products"]`
            3. Nombrar como "Productos"
            """)
        return
    
    sf_df = processor.data['screaming_frog']
    category = processor.category_keyword
    
    # ═══════════════════════════════════════════════════════════════════════════
    # FUNNEL DE INDEXACIÓN
    # ═══════════════════════════════════════════════════════════════════════════
    st.markdown("### 🔻 Funnel de Indexación")
    st.caption("Progresión desde URLs rastreadas hasta URLs que generan tráfico real")
    
    total_crawled = len(sf_df)
    indexable = sf_df[sf_df['indexability'] == 'Indexable']
    total_indexable = len(indexable)
    with_impressions = sf_df[(sf_df['impressions'].notna()) & (sf_df['impressions'] > 0)]
    total_with_impressions = len(with_impressions)
    with_clicks = sf_df[(sf_df['clicks'].notna()) & (sf_df['clicks'] > 0)]
    total_with_clicks = len(with_clicks)
    
    # Métricas del funnel
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Rastreadas", f"{total_crawled:,}", help="Total de URLs HTML rastreadas")
        st.caption("100%")
    with c2:
        pct_indexable = total_indexable / total_crawled * 100 if total_crawled > 0 else 0
        st.metric("Indexables", f"{total_indexable:,}", help="URLs con meta robots index")
        st.caption(f"{pct_indexable:.1f}% del total")
    with c3:
        pct_impressions = total_with_impressions / total_crawled * 100 if total_crawled > 0 else 0
        st.metric("Con Impresiones", f"{total_with_impressions:,}", help="URLs que aparecen en SERPs")
        st.caption(f"{pct_impressions:.1f}% del total")
    with c4:
        pct_clicks = total_with_clicks / total_crawled * 100 if total_crawled > 0 else 0
        st.metric("Con Clics", f"{total_with_clicks:,}", help="URLs que generan tráfico orgánico")
        st.caption(f"{pct_clicks:.1f}% del total")
    
    # Gráfico de funnel
    funnel_data = pd.DataFrame({
        'Etapa': ['Rastreadas', 'Indexables', 'Con Impresiones', 'Con Clics'],
        'URLs': [total_crawled, total_indexable, total_with_impressions, total_with_clicks],
        'Porcentaje': [100, pct_indexable, pct_impressions, pct_clicks]
    })
    
    fig_funnel = px.funnel(funnel_data, x='URLs', y='Etapa', 
                           color_discrete_sequence=['#3b82f6', '#22d3ee', '#10b981', '#f59e0b'])
    fig_funnel.update_layout(height=300, margin=dict(t=20, b=20))
    st.plotly_chart(fig_funnel, use_container_width=True)
    
    st.divider()
    
    # ═══════════════════════════════════════════════════════════════════════════
    # JERARQUÍA DE FACETAS
    # ═══════════════════════════════════════════════════════════════════════════
    st.markdown("### 🏛️ Jerarquía de Estructura de Facetas")
    st.caption("Distribución de URLs por nivel de profundidad en el sistema de navegación facetada")
    
    # Agrupar por nivel de faceta
    level_analysis = []
    for level in sorted(sf_df['facet_level'].unique()):
        if level < 0:
            continue
        level_df = sf_df[sf_df['facet_level'] == level]
        level_indexable = level_df[level_df['indexability'] == 'Indexable']
        level_with_clicks = level_df[(level_df['clicks'].notna()) & (level_df['clicks'] > 0)]
        
        total_clicks = level_df['clicks'].sum() if 'clicks' in level_df.columns else 0
        total_impressions = level_df['impressions'].sum() if 'impressions' in level_df.columns else 0
        avg_links = level_df['internal_links'].mean() if 'internal_links' in level_df.columns else 0
        
        efficiency = len(level_with_clicks) / len(level_indexable) * 100 if len(level_indexable) > 0 else 0
        
        level_analysis.append({
            'Nivel': f'N{level}',
            'URLs': len(level_df),
            'Indexables': len(level_indexable),
            'Con Clics': len(level_with_clicks),
            'Eficiencia': efficiency,
            'Total Clics': total_clicks,
            'Total Impresiones': total_impressions,
            'Avg Enlaces Internos': avg_links
        })
    
    level_df_display = pd.DataFrame(level_analysis)
    
    # Mostrar tabla
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.dataframe(
            level_df_display.style.format({
                'URLs': '{:,.0f}',
                'Indexables': '{:,.0f}',
                'Con Clics': '{:,.0f}',
                'Eficiencia': '{:.1f}%',
                'Total Clics': '{:,.0f}',
                'Total Impresiones': '{:,.0f}',
                'Avg Enlaces Internos': '{:.0f}'
            }).background_gradient(subset=['Eficiencia'], cmap='RdYlGn'),
            use_container_width=True,
            hide_index=True
        )
    
    with col2:
        # Gráfico de distribución de clics por nivel
        fig_clicks = px.pie(
            level_df_display[level_df_display['Total Clics'] > 0],
            values='Total Clics',
            names='Nivel',
            title='Distribución de Clics por Nivel',
            color_discrete_sequence=px.colors.qualitative.Set2
        )
        fig_clicks.update_traces(textposition='inside', textinfo='percent+label')
        fig_clicks.update_layout(height=300, showlegend=False, margin=dict(t=40, b=20))
        st.plotly_chart(fig_clicks, use_container_width=True)
    
    # Alertas por nivel
    st.markdown("#### ⚠️ Alertas de Arquitectura")
    
    alerts = []
    for row in level_analysis:
        level = row['Nivel']
        indexables = row['Indexables']
        with_clicks = row['Con Clics']
        efficiency = row['Eficiencia']
        
        if level in ['N3', 'N4', 'N5'] and indexables > 0:
            alerts.append({
                'Nivel': level,
                'Problema': f'{indexables:,} URLs indexables en nivel profundo',
                'Impacto': f'Solo {efficiency:.1f}% reciben clics',
                'Acción': 'Aplicar NOINDEX + canonical al ancestro N1/N2',
                'Prioridad': '🔴 Alta' if indexables > 1000 else '🟡 Media'
            })
        
        if level == 'N1' and efficiency < 50 and indexables > 0:
            alerts.append({
                'Nivel': level,
                'Problema': f'Baja eficiencia en N1 ({efficiency:.1f}%)',
                'Impacto': f'{indexables - with_clicks:,} URLs indexables sin tráfico',
                'Acción': 'Revisar contenido y enlaces internos',
                'Prioridad': '🟡 Media'
            })
    
    if alerts:
        st.dataframe(pd.DataFrame(alerts), use_container_width=True, hide_index=True)
    else:
        st.success("✅ No se detectaron problemas críticos de arquitectura")
    
    st.divider()
    
    # ═══════════════════════════════════════════════════════════════════════════
    # LINK JUICE & CRAWL BUDGET
    # ═══════════════════════════════════════════════════════════════════════════
    st.markdown("### 🔗 Distribución de Link Juice")
    st.caption("Análisis de enlaces internos y su correlación con rendimiento SEO")
    
    if 'internal_links' in sf_df.columns:
        col1, col2 = st.columns(2)
        
        with col1:
            # Distribución de enlaces por nivel
            link_by_level = []
            for level in sorted(sf_df['facet_level'].unique()):
                if level < 0:
                    continue
                level_df = sf_df[sf_df['facet_level'] == level]
                link_by_level.append({
                    'Nivel': f'N{level}',
                    'Promedio Enlaces': level_df['internal_links'].mean(),
                    'Máximo Enlaces': level_df['internal_links'].max(),
                    'Mínimo Enlaces': level_df['internal_links'].min()
                })
            
            link_df = pd.DataFrame(link_by_level)
            
            fig_links = px.bar(
                link_df,
                x='Nivel',
                y='Promedio Enlaces',
                title='Promedio de Enlaces Internos por Nivel',
                color='Promedio Enlaces',
                color_continuous_scale='Blues'
            )
            fig_links.update_layout(height=350, margin=dict(t=40, b=20))
            st.plotly_chart(fig_links, use_container_width=True)
        
        with col2:
            # Correlación enlaces vs clics
            corr_df = sf_df[(sf_df['internal_links'] > 0) & (sf_df['clicks'].notna())].copy()
            
            if len(corr_df) > 10:
                fig_corr = px.scatter(
                    corr_df.head(500),
                    x='internal_links',
                    y='clicks',
                    color='facet_level',
                    title='Enlaces Internos vs Clics',
                    labels={'internal_links': 'Enlaces Internos', 'clicks': 'Clics', 'facet_level': 'Nivel'},
                    color_continuous_scale='Viridis'
                )
                fig_corr.update_layout(height=350, margin=dict(t=40, b=20))
                st.plotly_chart(fig_corr, use_container_width=True)
            else:
                st.info("Datos insuficientes para correlación")
        
        # Métricas de crawl budget
        st.markdown("#### 📊 Métricas de Crawl Budget")
        
        total_links = sf_df['internal_links'].sum()
        avg_links_indexable = indexable['internal_links'].mean() if len(indexable) > 0 else 0
        avg_links_noindex = sf_df[sf_df['indexability'] != 'Indexable']['internal_links'].mean()
        
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Total Enlaces Internos", f"{total_links:,.0f}")
            st.caption("Suma de todos los enlaces entrantes")
        with c2:
            st.metric("Promedio (Indexables)", f"{avg_links_indexable:.0f}")
            st.caption("Enlaces hacia URLs indexables")
        with c3:
            waste_pct = avg_links_noindex / avg_links_indexable * 100 if avg_links_indexable > 0 else 0
            st.metric("Promedio (No Indexables)", f"{avg_links_noindex:.0f}")
            st.caption(f"Potencial desperdicio de crawl budget")
    
    st.divider()
    
    # ═══════════════════════════════════════════════════════════════════════════
    # THIN CONTENT
    # ═══════════════════════════════════════════════════════════════════════════
    st.markdown("### 📄 Análisis de Thin Content")
    
    # Detectar si hay columna de productos
    has_products = 'product_count' in sf_df.columns and sf_df['product_count'].sum() > 0
    
    if has_products:
        st.success("✅ Datos de productos detectados (extracción personalizada)")
        content_metric = 'product_count'
        metric_name = 'Productos'
        thin_threshold_low = 5
        thin_threshold_medium = 20
    else:
        st.warning("⚠️ Sin datos de productos. Usando 'Recuento de palabras' como proxy.")
        st.caption("Para análisis preciso, configura extracción XPath: `//*[@id=\"action-bar-total-products\"]`")
        content_metric = 'word_count'
        metric_name = 'Palabras'
        thin_threshold_low = 100
        thin_threshold_medium = 300
    
    if content_metric in sf_df.columns:
        # Solo analizar indexables
        indexable_content = indexable.copy()
        
        thin_critical = indexable_content[indexable_content[content_metric] < thin_threshold_low]
        thin_warning = indexable_content[(indexable_content[content_metric] >= thin_threshold_low) & 
                                          (indexable_content[content_metric] < thin_threshold_medium)]
        healthy = indexable_content[indexable_content[content_metric] >= thin_threshold_medium]
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(
                f"🔴 Crítico (<{thin_threshold_low} {metric_name})", 
                f"{len(thin_critical):,}",
                help="URLs indexables con contenido muy bajo"
            )
        with col2:
            st.metric(
                f"🟡 Bajo ({thin_threshold_low}-{thin_threshold_medium} {metric_name})", 
                f"{len(thin_warning):,}",
                help="URLs indexables con contenido limitado"
            )
        with col3:
            st.metric(
                f"✅ Saludable (>{thin_threshold_medium} {metric_name})", 
                f"{len(healthy):,}",
                help="URLs con contenido suficiente"
            )
        
        # Tabla de thin content con más impresiones (oportunidades)
        st.markdown("#### 🎯 Thin Content con Mayor Potencial")
        st.caption("URLs indexables con poco contenido pero que ya tienen impresiones (oportunidad de mejora)")
        
        thin_with_impressions = thin_critical[
            (thin_critical['impressions'].notna()) & 
            (thin_critical['impressions'] > 0)
        ].nlargest(20, 'impressions')
        
        if len(thin_with_impressions) > 0:
            display_cols = ['url', content_metric, 'impressions', 'clicks', 'position', 'facet_level']
            display_cols = [c for c in display_cols if c in thin_with_impressions.columns]
            
            display_df = thin_with_impressions[display_cols].copy()
            display_df['url'] = display_df['url'].str.replace('https://www.pccomponentes.com', '', regex=False)
            
            col_names = {
                'url': 'URL',
                content_metric: metric_name,
                'impressions': 'Impresiones',
                'clicks': 'Clics',
                'position': 'Posición',
                'facet_level': 'Nivel'
            }
            display_df = display_df.rename(columns=col_names)
            
            st.dataframe(display_df, use_container_width=True, hide_index=True)
        else:
            st.info("No hay thin content crítico con impresiones")
        
        # Distribución de contenido
        st.markdown("#### 📊 Distribución de Contenido")
        
        fig_content = px.histogram(
            indexable_content[indexable_content[content_metric] < 1000],
            x=content_metric,
            nbins=50,
            title=f'Distribución de {metric_name} en URLs Indexables',
            labels={content_metric: metric_name},
            color_discrete_sequence=['#3b82f6']
        )
        fig_content.add_vline(x=thin_threshold_low, line_dash="dash", line_color="red", 
                              annotation_text="Crítico")
        fig_content.add_vline(x=thin_threshold_medium, line_dash="dash", line_color="orange",
                              annotation_text="Mínimo recomendado")
        fig_content.update_layout(height=350, margin=dict(t=40, b=20))
        st.plotly_chart(fig_content, use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTAR
# ═══════════════════════════════════════════════════════════════════════════════

def render_export_tab():
    st.subheader("📥 Exportar")
    
    if not st.session_state.analysis_complete:
        st.info("Ejecuta el análisis primero")
        return
    
    analyzer = st.session_state.analyzer
    category = st.session_state.category
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### CSV")
        if analyzer and not analyzer.results.cannibalization.empty:
            st.download_button("📥 Canibalización", analyzer.results.cannibalization.to_csv(index=False), "canibalizacion.csv")
        if analyzer and not analyzer.results.gaps.empty:
            st.download_button("📥 Gaps", analyzer.results.gaps.to_csv(index=False), "gaps.csv")
        if analyzer and not analyzer.results.facet_usage.empty:
            st.download_button("📥 Facetas", analyzer.results.facet_usage.to_csv(index=False), "facetas.csv")
    
    with col2:
        st.markdown("#### HTML")
        if st.session_state.insights_data:
            report = ReportGenerator(category, st.session_state.insights_data)
            st.download_button("📋 Resumen", report.generate_executive_summary(), f"resumen-{category}.html")
            st.download_button("🏗️ Arquitectura", report.generate_architecture_report(), f"arquitectura-{category}.html")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    init_session_state()
    
    st.title("🏗️ Facet Architecture Analyzer")
    st.caption("Demanda Interna + Demanda de Mercado | Validación Dual IA (2 Fases)")
    
    render_sidebar()
    
    tabs = st.tabs([
        "📊 Resumen",
        "🏗️ Arquitectura", 
        "🧭 Navegación",
        "📈 Demanda",
        "🔴 Canibalización",
        "📝 Estrategia",
        "🔍 Auditoría Técnica",
        "💡 Insights",
        "🚀 Recomendaciones",
        "📥 Exportar"
    ])
    
    with tabs[0]: render_overview_tab()
    with tabs[1]: render_architecture_tab()
    with tabs[2]: render_navigation_tab()
    with tabs[3]: render_demand_tab()
    with tabs[4]: render_cannibalization_tab()
    with tabs[5]: render_content_strategy_tab()
    with tabs[6]: render_audit_tab()
    with tabs[7]: render_insights_tab()
    with tabs[8]: render_recommendations_tab()
    with tabs[9]: render_export_tab()


if __name__ == "__main__":
    main()
