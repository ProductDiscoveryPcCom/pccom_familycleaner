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
        
        category = st.text_input("Categoría", value=st.session_state.get('category', 'televisores'))
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
                filter_url_seo=filter_url_seo
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
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PÁRRAFO EXPLICATIVO DE MÉTRICAS
    # ═══════════════════════════════════════════════════════════════════════════
    st.markdown("""
    Este resumen muestra las métricas principales del análisis de navegación facetada. 
    **URLs** y **Filtros** provienen de los datos de rendimiento SEO (Top Query/GSC). 
    **Canibalización** indica el porcentaje de clics en artículos que deberían ir a filtros de categoría.
    Los datos de uso de facetas provienen de Adobe Analytics (Search Filters).
    """)
    
    st.divider()
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("URLs", f"{summary.get('total_urls', 0):,}")
    c2.metric("Filtros", f"{summary.get('filters_count', 0):,}")
    c3.metric("Artículos", f"{summary.get('articles_count', 0):,}")
    c4.metric("Canibalización", f"{summary.get('cannibalization_rate', 0):.1f}%")
    
    st.divider()
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PRIORIDAD DE FACETAS - CON EXPLICACIÓN Y EJEMPLO
    # ═══════════════════════════════════════════════════════════════════════════
    if summary.get('facet_order'):
        st.markdown("#### 🎯 Prioridad de Facetas")
        
        # Obtener datos de uso para el ejemplo
        filter_all = processor.data.get('filter_usage_all')
        top_example_url = ""
        top_facet_value = ""
        
        if filter_all is not None and not filter_all.empty:
            top_facet = summary['facet_order'][0] if summary['facet_order'] else None
            if top_facet:
                facet_data = filter_all[filter_all['facet_type'] == top_facet]
                if not facet_data.empty:
                    top_row = facet_data.nlargest(1, 'sessions').iloc[0]
                    top_facet_value = top_row.get('facet_value', '')
                    # Construir URL ejemplo
                    category = st.session_state.category
                    if top_facet == 'size':
                        top_example_url = f"/{category}/{top_facet_value}-pulgadas"
                    elif top_facet == 'brand':
                        top_example_url = f"/{category}/{top_facet_value}"
                    else:
                        top_example_url = f"/{category}/{top_facet_value}"
        
        # Explicación de la priorización
        st.markdown(f"""
        La priorización se basa en el **uso real de filtros por usuarios** (demanda interna desde Adobe Analytics).
        Las facetas con más interacciones deben aparecer primero en la navegación del sitio.
        
        > **Ejemplo:** La faceta más usada es **{summary['facet_order'][0].upper()}** con el valor más popular 
        > **"{top_facet_value}"**, que genera la URL: `{top_example_url}`
        """)
        
        # Mostrar ranking con número grande y nombre pequeño
        cols = st.columns(min(5, len(summary['facet_order'])))
        icons = {'size': '📐', 'brand': '🏷️', 'technology': '⚡', 'price': '💰', 'connectivity': '📡', 'refresh_rate': '🔄', 'resolution': '🖥️', 'condition': '♻️'}
        
        for i, facet in enumerate(summary['facet_order'][:5]):
            with cols[i]:
                st.markdown(f"""
                <div style="text-align: center; padding: 10px; background: #1e293b; border-radius: 10px; border: 1px solid #334155;">
                    <div style="font-size: 2.5rem; font-weight: 700; color: #22d3ee;">#{i+1}</div>
                    <div style="font-size: 0.85rem; color: #94a3b8; margin-top: 5px;">{icons.get(facet, '📦')} {facet.title()}</div>
                </div>
                """, unsafe_allow_html=True)
    
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
        st.markdown("#### 📈 Distribución URLs")
        st.caption("Clics SEO agrupados por tipo de URL (Top Query/GSC)")
        
        url_df = analyzer.results.url_classification
        if not url_df.empty:
            clicks_col = 'clicks' if 'clicks' in url_df.columns else 'url_total_clicks'
            if clicks_col in url_df.columns:
                dist = url_df.groupby('url_type')[clicks_col].sum().reset_index()
                dist.columns = ['Tipo', 'Clics']
                fig = px.pie(dist, values='Clics', names='Tipo')
                # Leyenda más cerca del gráfico
                fig.update_layout(
                    height=280, 
                    margin=dict(t=10, b=10, l=10, r=10),
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=-0.15,
                        xanchor="center",
                        x=0.5
                    )
                )
                st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown("#### 🔄 Uso de Facetas")
        st.caption("Porcentaje de interacciones por tipo de filtro (Adobe Analytics: Search Filters). Cada barra representa una faceta (ej: 'size', 'brand'). Los valores individuales de cada faceta (ej: '55', 'Samsung') se analizan en detalle en la pestaña Navegación.")
        
        usage_df = analyzer.results.facet_usage
        if not usage_df.empty:
            fig = px.bar(usage_df.head(6), x='facet_type', y='pct_usage',
                        labels={'facet_type': 'Faceta', 'pct_usage': '% Uso'})
            fig.update_layout(height=280, showlegend=False)
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
        "💡 Insights",
        "🚀 Recomendaciones",
        "📥 Exportar"
    ])
    
    with tabs[0]: render_overview_tab()
    with tabs[1]: render_architecture_tab()
    with tabs[2]: render_navigation_tab()
    with tabs[3]: render_demand_tab()
    with tabs[4]: render_cannibalization_tab()
    with tabs[5]: render_insights_tab()
    with tabs[6]: render_recommendations_tab()
    with tabs[7]: render_export_tab()


if __name__ == "__main__":
    main()
